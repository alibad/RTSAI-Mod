#region Copyright & License Information
/*
 * Copyright (c) The OpenRA Developers and Contributors
 * This file is part of OpenRA, which is free software. It is made
 * available to you under the terms of the GNU General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version. For more
 * information, see COPYING.
 */
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Pathfinder;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;
using RLProto = OpenRA.Mods.RTSAI.RL;

namespace OpenRA.Mods.RTSAI.Traits
{
	/// <summary>
	/// Serializes the current game state visible to a player into a protobuf GameObservation.
	/// </summary>
	public sealed class ObservationSerializer
	{
		const int SpatialChannelCount = 12;

		readonly World world;
		readonly Player player;
		readonly string episodeId;
		readonly ObservationWeaponTargets weaponTargets;

		// Cached trait references for spatial map (resolved lazily)
		IResourceLayer resourceLayer;
		BuildingInfluence buildingInfluence;
		Locomotor locomotor;
		bool traitsCached;
		readonly Dictionary<uint, int> enemyLastSeenTicks = [];

		public ObservationSerializer(World world, Player player, string episodeId)
		{
			this.world = world;
			this.player = player;
			this.episodeId = episodeId;
			weaponTargets = new ObservationWeaponTargets(world.Map.Rules.Actors.Values
				.Where(info => !info.Name.StartsWith('^'))
				.SelectMany(info => info.TraitInfos<ITargetableInfo>()).Select(info => info.GetTargetTypes()));
		}

		void EnsureTraitsCached()
		{
			if (traitsCached)
				return;

			traitsCached = true;
			resourceLayer = world.WorldActor.TraitOrDefault<IResourceLayer>();
			buildingInfluence = world.WorldActor.TraitOrDefault<BuildingInfluence>();

			// Use first available locomotor for passability checks
			locomotor = world.WorldActor.TraitsImplementing<Locomotor>().FirstOrDefault();
		}

		public RLProto.GameObservation Serialize(int tick)
		{
			var obs = new RLProto.GameObservation
			{
				Tick = tick,
				EpisodeId = episodeId,
				// The two standalone render profiles share the same actor and technology contract.
				ModId = Game.ModData.Manifest.Id == "rtsai-topdown" ? "rtsai" : Game.ModData.Manifest.Id,
				Economy = SerializeEconomy(),
				Military = SerializeMilitary(),
				MapInfo = SerializeMapInfo(),
				Done = world.IsGameOver,
			};

			if (world.IsGameOver)
			{
				obs.Result = player.WinState == WinState.Won ? "win"
					: player.WinState == WinState.Lost ? "lose"
					: "draw";
			}

			SerializeOwnedActors(obs);
			SerializeVisibleEnemies(obs);
			SerializeRememberedEnemyBuildings(obs);
			SerializeProduction(obs);
			SerializeMissionContext(obs);
			SerializeSupportPowers(obs);
			SerializeSpatialMap(obs);
			var knownTypes = obs.Units.Select(a => a.Type).Concat(obs.Buildings.Select(a => a.Type))
				.Concat(obs.VisibleEnemies.Select(a => a.Type)).Concat(obs.VisibleEnemyBuildings.Select(a => a.Type))
				.Concat(obs.RememberedEnemyBuildings.Select(a => a.Type)).Concat(obs.AvailableProduction)
				.Concat(obs.Production.Select(a => a.Item)).Distinct();
			foreach (var type in knownTypes)
				if (world.Map.Rules.Actors.TryGetValue(type, out var info))
				{
					var name = info.TraitInfos<TooltipInfo>().FirstOrDefault()?.Name;
					obs.ActorNames[type] = string.IsNullOrEmpty(name) ? type : FluentProvider.GetMessage(name);
				}

			return obs;
		}

		void SerializeSupportPowers(RLProto.GameObservation obs)
		{
			var manager = player.PlayerActor.TraitOrDefault<SupportPowerManager>();
			if (manager == null)
				return;

			foreach (var power in manager.Powers.Values.OrderBy(power => power.Key))
			{
				obs.SupportPowers.Add(new RLProto.RlSupportPowerInfo
				{
					Key = power.Key,
					Name = power.Name ?? "",
					Description = power.Description ?? "",
					Active = power.Active,
					Ready = power.Ready,
					RemainingTicks = power.RemainingTicks,
					TotalTicks = power.TotalTicks,
				});
			}
		}

		void SerializeMissionContext(RLProto.GameObservation obs)
		{
			var missionData = world.WorldActor.Info.TraitInfoOrDefault<MissionDataInfo>();
			obs.MissionMode = missionData != null;
			if (missionData != null && !string.IsNullOrEmpty(missionData.Briefing))
				obs.MissionBriefing = FluentProvider.TryGetMessage(missionData.Briefing, out var briefing)
					? briefing
					: missionData.Briefing;

			var missionObjectives = player.PlayerActor.TraitOrDefault<MissionObjectives>();
			if (missionObjectives == null)
				return;

			for (var id = 0; id < missionObjectives.Objectives.Count; id++)
			{
				var objective = missionObjectives.Objectives[id];
				obs.Objectives.Add(new RLProto.RlObjective
				{
					Id = id,
					Description = objective.Description ?? "",
					Type = objective.Type ?? "",
					Required = objective.Required,
					State = objective.State.ToString().ToLowerInvariant(),
				});
			}
		}

		void SerializeRememberedEnemyBuildings(RLProto.GameObservation obs)
		{
			var frozenLayer = player.FrozenActorLayer;
			if (frozenLayer == null)
				return;

			foreach (var frozen in frozenLayer.FrozenActorsInRegion(world.Map.AllCells))
			{
				if (player.RelationshipWith(frozen.Owner) != PlayerRelationship.Enemy ||
					!frozen.Info.HasTraitInfo<BuildingInfo>())
					continue;

				var cell = world.Map.CellContaining(frozen.CenterPosition).ToMPos(world.Map);
				var healthInfo = frozen.Info.TraitInfoOrDefault<HealthInfo>();
				var hpPercent = healthInfo != null && healthInfo.HP > 0
					? (float)frozen.HP / healthInfo.HP
					: 1f;

				obs.RememberedEnemyBuildings.Add(new RLProto.RlBuildingInfo
				{
					ActorId = frozen.ID,
					Type = frozen.Info.Name,
					PosX = frozen.CenterPosition.X,
					PosY = frozen.CenterPosition.Y,
					CellX = cell.U,
					CellY = cell.V,
					HpPercent = hpPercent,
					Owner = frozen.Owner.InternalName,
					LastSeenTick = enemyLastSeenTicks.TryGetValue(frozen.ID, out var lastSeenTick) ? lastSeenTick : 0,
				});
			}
		}

		RLProto.RlEconomy SerializeEconomy()
		{
			var economy = new RLProto.RlEconomy();

			var resources = player.PlayerActor.TraitOrDefault<PlayerResources>();
			if (resources != null)
			{
				economy.Cash = resources.Cash;
				economy.Ore = resources.Resources;
				economy.ResourceCapacity = resources.ResourceCapacity;
			}

			var power = player.PlayerActor.TraitOrDefault<PowerManager>();
			if (power != null)
			{
				economy.PowerProvided = power.PowerProvided;
				economy.PowerDrained = power.PowerDrained;
			}

			// Count harvesters
			economy.HarvesterCount = world.ActorsHavingTrait<Harvester>()
				.Count(a => a.Owner == player && !a.IsDead && a.IsInWorld);

			return economy;
		}

		RLProto.RlMilitary SerializeMilitary()
		{
			var military = new RLProto.RlMilitary();

			var stats = player.PlayerActor.TraitOrDefault<PlayerStatistics>();
			if (stats != null)
			{
				military.UnitsKilled = stats.UnitsKilled;
				military.UnitsLost = stats.UnitsDead;
				military.BuildingsKilled = stats.BuildingsKilled;
				military.BuildingsLost = stats.BuildingsDead;
				military.KillsCost = stats.KillsCost;
				military.DeathsCost = stats.DeathsCost;
				military.AssetsValue = stats.AssetsValue;
				military.Experience = stats.Experience;
				military.OrderCount = stats.OrderCount;
			}

			// Calculate army value and active unit count
			var ownedActors = world.ActorsHavingTrait<Health>()
				.Where(a => a.Owner == player && !a.IsDead && a.IsInWorld);

			var armyValue = 0;
			var unitCount = 0;
			foreach (var actor in ownedActors)
			{
				if (actor.Info.HasTraitInfo<BuildingInfo>())
					continue;

				unitCount++;

				var valued = actor.Info.TraitInfoOrDefault<ValuedInfo>();
				if (valued != null)
					armyValue += valued.Cost;
			}

			military.ArmyValue = armyValue;
			military.ActiveUnitCount = unitCount;

			return military;
		}

		void SerializeOwnedActors(RLProto.GameObservation obs)
		{
			foreach (var actor in world.Actors)
			{
				if (actor.Owner != player || actor.IsDead || !actor.IsInWorld)
					continue;

				// Skip world/player actors
				if (actor == world.WorldActor || actor == player.PlayerActor)
					continue;

				Health health;
				float hpPercent;
				try
				{
					health = actor.TraitOrDefault<Health>();
					hpPercent = health != null ? (float)health.HP / health.MaxHP : 1f;

					// Test position access early to catch transitional actors
					_ = actor.CenterPosition;
				}
				catch (NullReferenceException)
				{
					continue;
				}

				if (actor.Info.HasTraitInfo<BuildingInfo>())
				{
					var bldg = SerializeBuilding(actor, hpPercent, player.InternalName);
					obs.Buildings.Add(bldg);
				}
				else
				{
					var unit = SerializeUnit(actor, hpPercent, player.InternalName);
					obs.Units.Add(unit);
				}
			}
		}

		void SerializeVisibleEnemies(RLProto.GameObservation obs)
		{
			var enemyCount = 0;
			var buildingCount = 0;
			foreach (var actor in world.Actors)
			{
				if (actor.IsDead || !actor.IsInWorld ||
					player.RelationshipWith(actor.Owner) != PlayerRelationship.Enemy)
					continue;

				if (actor == world.WorldActor)
					continue;

				enemyCount++;
				try
				{
					var isBuilding = actor.Info.HasTraitInfo<BuildingInfo>();
					if (isBuilding) buildingCount++;
					// Check if visible through shroud/fog
					if (player.Shroud.IsVisible(actor.CenterPosition))
					{
						enemyLastSeenTicks[actor.ActorID] = obs.Tick;
						var health = actor.TraitOrDefault<Health>();
						var hpPercent = health != null ? (float)health.HP / health.MaxHP : 1f;

						if (actor.Info.HasTraitInfo<BuildingInfo>())
						{
							var bldg = SerializeBuilding(actor, hpPercent, actor.Owner.InternalName);
							obs.VisibleEnemyBuildings.Add(bldg);
						}
						else
						{
							var unit = SerializeUnit(actor, hpPercent, actor.Owner.InternalName);
							obs.VisibleEnemies.Add(unit);
						}
					}
				}
				catch (NullReferenceException)
				{
					// Actor may be in a transitional state — skip it
				}
			}
			if (obs.Tick % 500 == 0 || obs.Tick < 10)
				Log.Write(CompanionLog.Channel, $"Tick {obs.Tick}: {enemyCount} enemy actors, {buildingCount} buildings, {obs.VisibleEnemyBuildings.Count} visible bldgs");
		}

		RLProto.RlBuildingInfo SerializeBuilding(Actor actor, float hpPercent, string owner)
		{
			var bldg = new RLProto.RlBuildingInfo
			{
				ActorId = actor.ActorID,
				Type = actor.Info.Name,
				PosX = actor.CenterPosition.X,
				PosY = actor.CenterPosition.Y,
				HpPercent = hpPercent,
				Owner = owner,
				LastSeenTick = world.WorldTick,
			};

			var armor = actor.Info.TraitInfos<ArmorInfo>().FirstOrDefault();
			if (armor != null)
				bldg.ArmorType = armor.Type ?? "";
			bldg.TargetTypes.Add(actor.GetEnabledTargetTypes());
			var actorValue = actor.Info.TraitInfoOrDefault<ValuedInfo>();
			if (actorValue != null)
				bldg.Cost = actorValue.Cost;
			SerializeBuildingWeapon(actor, bldg);

			// Cell position
			var bldgCell = world.Map.CellContaining(actor.CenterPosition).ToMPos(world.Map);
			bldg.CellX = bldgCell.U;
			bldg.CellY = bldgCell.V;

			// Power
			var powerTrait = actor.TraitOrDefault<Power>();
			bldg.IsPowered = powerTrait == null || !powerTrait.IsTraitDisabled;
			if (powerTrait != null)
				bldg.PowerAmount = powerTrait.GetEnabledPower();

			// Repair status
			var repair = actor.TraitOrDefault<RepairableBuilding>();
			bldg.IsRepairing = repair != null && repair.RepairActive;

			// Sell value
			var valued = actor.Info.TraitInfoOrDefault<ValuedInfo>();
			var sellable = actor.Info.TraitInfoOrDefault<SellableInfo>();
			if (valued != null && sellable != null)
				bldg.SellValue = valued.Cost * sellable.RefundPercent / 100;

			// Rally point
			var rally = actor.TraitOrDefault<RallyPoint>();
			if (rally != null && rally.Path.Count > 0)
			{
				var rallyCell = rally.Path[0].ToMPos(world.Map);
				bldg.RallyX = rallyCell.U;
				bldg.RallyY = rallyCell.V;
			}
			else
			{
				bldg.RallyX = -1;
				bldg.RallyY = -1;
			}

			// Production status and capabilities
			var queues = actor.TraitsImplementing<ProductionQueue>();
			foreach (var queue in queues)
			{
				var current = queue.CurrentItem();
				if (current != null && !bldg.IsProducing)
				{
					bldg.IsProducing = true;
					bldg.ProducingItem = current.Item;
					bldg.ProductionProgress = current.TotalTime > 0
						? 1f - (float)current.RemainingTime / current.TotalTime
						: 0f;
				}

				foreach (var buildable in queue.BuildableItems())
					bldg.CanProduce.Add(buildable.Name);
			}

			return bldg;
		}

		RLProto.RlUnitInfo SerializeUnit(Actor actor, float hpPercent, string owner)
		{
			var unit = new RLProto.RlUnitInfo
			{
				ActorId = actor.ActorID,
				Type = actor.Info.Name,
				PosX = actor.CenterPosition.X,
				PosY = actor.CenterPosition.Y,
				HpPercent = hpPercent,
				IsIdle = actor.IsIdle,
				Owner = owner,
				Ammo = -1,
				PassengerCount = -1,
				MoveTargetX = -1,
				MoveTargetY = -1,
				LastSeenTick = world.WorldTick,
			};

			var armor = actor.Info.TraitInfos<ArmorInfo>().FirstOrDefault();
			if (armor != null)
				unit.ArmorType = armor.Type ?? "";
			unit.TargetTypes.Add(actor.GetEnabledTargetTypes());
			var actorValue = actor.Info.TraitInfoOrDefault<ValuedInfo>();
			if (actorValue != null)
				unit.Cost = actorValue.Cost;

			// Cell position
			var cell = world.Map.CellContaining(actor.CenterPosition).ToMPos(world.Map);
			unit.CellX = cell.U;
			unit.CellY = cell.V;

			// Current activity
			var activity = actor.CurrentActivity;
			if (activity != null)
				unit.CurrentActivity = activity.GetType().Name;

			// Attack capability and range
			var armaments = GetActiveArmaments(actor).ToArray();
			unit.CanAttack = armaments.Length > 0;
			var ranges = GetAttackRanges(actor);
			unit.AttackRange = ranges.Maximum;
			unit.MinimumAttackRange = ranges.Minimum;
			var targets = weaponTargets.Summarize(armaments.Select(armament => armament.Weapon));
			unit.CanTargetAir = targets.Air;
			unit.CanTargetGround = targets.Ground;
			var armament = armaments.FirstOrDefault();
			if (armament != null)
			{
				unit.ReloadRemainingTicks = armament.FireDelay;
				unit.ReloadTotalTicks = armament.Weapon.ReloadDelay;
				unit.Weapon = armament.Info.Weapon ?? "";
				unit.Burst = armament.Weapon.Burst;
			}

			var attackFollow = actor.TraitsImplementing<AttackFollow>()
				.FirstOrDefault(attack => !attack.IsTraitDisabled && attack.RequestedTarget.Type == TargetType.Actor);
			if (attackFollow != null)
				unit.CurrentTargetActorId = attackFollow.RequestedTarget.Actor.ActorID;

			// Ammo
			var ammoPools = actor.TraitsImplementing<AmmoPool>().ToArray();
			if (ammoPools.Length > 0)
				unit.Ammo = ammoPools.Sum(pool => pool.CurrentAmmoCount);

			// Facing
			var facing = actor.TraitOrDefault<IFacing>();
			if (facing != null)
				unit.Facing = facing.Facing.Angle;

			// Veterancy
			var exp = actor.TraitOrDefault<GainsExperience>();
			if (exp != null)
				unit.ExperienceLevel = exp.Level;

			// Stance
			var autoTarget = actor.TraitOrDefault<AutoTarget>();
			if (autoTarget != null)
				unit.Stance = (int)autoTarget.Stance;

			// Speed (base speed from trait info)
			var mobileInfo = actor.Info.TraitInfoOrDefault<MobileInfo>();
			if (mobileInfo != null)
				unit.Speed = mobileInfo.Speed;
			var mobile = actor.TraitOrDefault<Mobile>();
			if (mobile != null)
			{
				var destination = mobile.ToCell.ToMPos(world.Map);
				unit.MoveTargetX = destination.U;
				unit.MoveTargetY = destination.V;
			}

			// Cargo
			var cargo = actor.TraitOrDefault<Cargo>();
			if (cargo != null)
				unit.PassengerCount = cargo.PassengerCount;

			// Building flag (for distinguishing in mixed lists)
			unit.IsBuilding = actor.Info.HasTraitInfo<BuildingInfo>();

			unit.IsDisguised = actor.EffectiveOwner?.Disguised == true;
			unit.DisguiseOwner = unit.IsDisguised ? actor.EffectiveOwner.Owner?.InternalName ?? "" : "";
			// IgnoresDisguiseInfo is internal to OpenRA.Mods.Common; match it by type name from the mod assembly.
			unit.DetectsDisguise = actor.Info.TraitInfos<TraitInfo>().Any(t => t.GetType().Name == "IgnoresDisguiseInfo");

			if (actor.Owner == player)
				SerializeSpecialOrders(actor, unit);

			return unit;
		}

		static (int Minimum, int Maximum) GetAttackRanges(Actor actor)
		{
			var minimum = int.MaxValue;
			var maximum = 0;
			foreach (var attack in actor.TraitsImplementing<AttackBase>())
			{
				if (attack.IsTraitDisabled || attack.IsTraitPaused)
					continue;

				var range = attack.GetMaximumRange().Length;
				if (range <= 0)
					continue;

				maximum = Math.Max(maximum, range);
				minimum = Math.Min(minimum, attack.GetMinimumRange().Length);
			}

			return (minimum == int.MaxValue ? 0 : minimum, maximum);
		}

		static IEnumerable<Armament> GetActiveArmaments(Actor actor)
		{
			// Attack modes may select different armaments even when the armament itself
			// has no condition (e.g. deployed infantry). Include secondary weapons and
			// passenger weapons only when their owning attack mode can use them.
			return actor.TraitsImplementing<AttackBase>()
				.Where(attack => !attack.IsTraitDisabled && !attack.IsTraitPaused)
				.SelectMany(attack => attack.Armaments)
				.Where(armament => !armament.IsTraitDisabled && !armament.IsTraitPaused)
				.Distinct();
		}

		void SerializeBuildingWeapon(Actor actor, RLProto.RlBuildingInfo building)
		{
			var ranges = GetAttackRanges(actor);
			building.AttackRange = ranges.Maximum;
			building.MinimumAttackRange = ranges.Minimum;

			var armaments = GetActiveArmaments(actor).ToArray();
			var targets = weaponTargets.Summarize(armaments.Select(armament => armament.Weapon));
			building.CanTargetAir = targets.Air;
			building.CanTargetGround = targets.Ground;
			var armament = armaments.FirstOrDefault();
			if (armament == null)
				return;
			building.ReloadRemainingTicks = armament.FireDelay;
			building.ReloadTotalTicks = armament.Weapon.ReloadDelay;
			building.Weapon = armament.Info.Weapon ?? "";
			building.Burst = armament.Weapon.Burst;
			var attackFollow = actor.TraitsImplementing<AttackFollow>()
				.FirstOrDefault(attack => !attack.IsTraitDisabled && attack.RequestedTarget.Type == TargetType.Actor);
			if (attackFollow != null)
				building.CurrentTargetActorId = attackFollow.RequestedTarget.Actor.ActorID;
		}

		void SerializeSpecialOrders(Actor actor, RLProto.RlUnitInfo unit)
		{
			var targeters = actor.TraitsImplementing<IIssueOrder>()
				.SelectMany(issuer => issuer.Orders)
				.Where(targeter => targeter.OrderID is "Disguise" or "Infiltrate" or "C4" or "CaptureActor")
				.ToArray();
			unit.CanDisguise = targeters.Any(targeter => targeter.OrderID == "Disguise");
			unit.CanInfiltrate = targeters.Any(targeter => targeter.OrderID == "Infiltrate");
			unit.CanDemolish = targeters.Any(targeter => targeter.OrderID == "C4");
			unit.CanCapture = targeters.Any(targeter => targeter.OrderID == "CaptureActor");
			if (targeters.Length == 0)
				return;

			foreach (var target in world.Actors)
			{
				if (target == actor || target.IsDead || !target.IsInWorld || target == world.WorldActor)
					continue;

				WPos centerPosition;
				try
				{
					centerPosition = target.CenterPosition;
				}
				catch (NullReferenceException)
				{
					continue;
				}

				if (target.Owner != player && !player.Shroud.IsVisible(centerPosition))
					continue;

				foreach (var targeter in targeters)
				{
					var modifiers = TargetModifiers.None;
					var cursor = "";
					if (!targeter.CanTarget(actor, Target.FromActor(target), ref modifiers, ref cursor))
						continue;

					switch (targeter.OrderID)
					{
						case "Disguise":
							unit.ValidDisguiseTargets.Add(target.ActorID);
							break;
						case "Infiltrate":
							unit.ValidInfiltrationTargets.Add(target.ActorID);
							break;
						case "C4":
							unit.ValidDemolitionTargets.Add(target.ActorID);
							break;
						case "CaptureActor":
							unit.ValidCaptureTargets.Add(target.ActorID);
							break;
					}
				}
			}
		}

		void SerializeProduction(RLProto.GameObservation obs)
		{
			// Collect production from all owned production structures
			foreach (var actor in world.ActorsHavingTrait<ProductionQueue>())
			{
				if (actor.Owner != player || actor.IsDead || !actor.IsInWorld)
					continue;

				foreach (var queue in actor.TraitsImplementing<ProductionQueue>())
				{
					foreach (var item in queue.AllQueued())
					{
						obs.Production.Add(new RLProto.RlProductionInfo
						{
							QueueType = queue.Info.Type,
							Item = item.Item,
							Progress = item.TotalTime > 0
								? 1f - (float)item.RemainingTime / item.TotalTime
								: 0f,
							RemainingTicks = item.RemainingTime,
							RemainingCost = item.RemainingCost,
							Paused = item.Paused,
						});
					}

					// Available production items
					foreach (var buildable in queue.BuildableItems())
						obs.AvailableProduction.Add(buildable.Name);
				}
			}
		}

		RLProto.RlMapInfo SerializeMapInfo()
		{
			var bounds = world.Map.Bounds;
			return new RLProto.RlMapInfo
			{
				Width = world.Map.MapSize.Width,
				Height = world.Map.MapSize.Height,
				MapName = world.Map.Title ?? "",
				BoundsX = bounds.X,
				BoundsY = bounds.Y,
				BoundsWidth = bounds.Width,
				BoundsHeight = bounds.Height,
			};
		}

		void SerializeSpatialMap(RLProto.GameObservation obs)
		{
			EnsureTraitsCached();

			var map = world.Map;
			var width = map.MapSize.Width;
			var height = map.MapSize.Height;
			var shroud = player.Shroud;

			// Allocate spatial tensor: H × W × channels, row-major channels-last
			var data = new float[height * width * SpatialChannelCount];

			// Pre-compute actor cell positions for unit/building density layers
			var ownBuildingCells = new bool[height * width];
			var ownUnitDensity = new int[height * width];
			var enemyBuildingCells = new bool[height * width];
			var enemyUnitDensity = new int[height * width];
			var enemyThreat = new float[height * width];
			var friendlyCoverage = new float[height * width];
			var exploredCells = 0;
			var totalCells = 0;

			foreach (var actor in world.Actors)
			{
				if (actor.IsDead || !actor.IsInWorld || actor == world.WorldActor)
					continue;

				if (actor.Owner.NonCombatant)
					continue;

				MPos actorCell;
				try
				{
					actorCell = map.CellContaining(actor.CenterPosition).ToMPos(map);
				}
				catch (NullReferenceException)
				{
					continue;
				}

				if (actorCell.U < 0 || actorCell.U >= width || actorCell.V < 0 || actorCell.V >= height)
					continue;

				var idx = actorCell.V * width + actorCell.U;

				if (actor.Owner == player)
				{
					if (actor.Info.HasTraitInfo<BuildingInfo>())
						ownBuildingCells[idx] = true;
					else if (actor != player.PlayerActor)
						ownUnitDensity[idx]++;
				}
				else if (player.RelationshipWith(actor.Owner) == PlayerRelationship.Enemy && shroud.IsVisible(actor.CenterPosition))
				{
					if (actor.Info.HasTraitInfo<BuildingInfo>())
						enemyBuildingCells[idx] = true;
					else
						enemyUnitDensity[idx]++;
				}

				if (actor.Owner != player &&
					(player.RelationshipWith(actor.Owner) != PlayerRelationship.Enemy || !shroud.IsVisible(actor.CenterPosition)))
					continue;
				var maximumRange = GetAttackRanges(actor).Maximum;
				if (maximumRange <= 0)
					continue;
				var range = (maximumRange + 1023) / 1024;
				var coverage = actor.Owner == player ? friendlyCoverage : enemyThreat;
				for (var cy = Math.Max(0, actorCell.V - range * 2); cy <= Math.Min(height - 1, actorCell.V + range * 2); cy++)
				{
					for (var cx = Math.Max(0, actorCell.U - range * 2); cx <= Math.Min(width - 1, actorCell.U + range * 2); cx++)
					{
						var offset = new MPos(cx, cy).ToCPos(map) - actorCell.ToCPos(map);
						if (offset.LengthSquared <= range * range)
							coverage[cy * width + cx] += 1f;
					}
				}
			}

			// Fill per-cell data
			foreach (var cell in map.AllCells)
			{
				var mapCell = cell.ToMPos(map);
				var x = mapCell.U;
				var y = mapCell.V;
				if (x < 0 || x >= width || y < 0 || y >= height)
					continue;

				var baseIdx = (y * width + x) * SpatialChannelCount;
				var cellIdx = y * width + x;
				totalCells++;
				var explored = shroud.IsExplored(cell);

				// Ch 0: Terrain type index
				data[baseIdx + 0] = map.GetTerrainIndex(cell);

				// Ch 1: Height
				data[baseIdx + 1] = map.Height[cell];

				// Ch 2: Resource density
				if (resourceLayer != null && explored)
				{
					var resource = resourceLayer.GetResource(cell);
					data[baseIdx + 2] = resource.Density;
				}

				// Ch 3: Passability (1=passable, 0=impassable)
				if (locomotor != null)
				{
					var cost = locomotor.MovementCostForCell(cell);
					data[baseIdx + 3] = cost >= PathGraph.MovementCostForUnreachableCell ? 0f : 1f;
					data[baseIdx + 11] = cost >= PathGraph.MovementCostForUnreachableCell ? 1f : Math.Min(1f, cost / 10000f);
				}

				// Ch 4: Fog of war (0=hidden, 0.5=explored, 1=visible)
				if (explored)
					exploredCells++;

				if (shroud.IsVisible(cell))
					data[baseIdx + 4] = 1f;
				else if (explored)
					data[baseIdx + 4] = 0.5f;

				// Ch 5-8: Actor density (pre-computed above)
				data[baseIdx + 5] = ownBuildingCells[cellIdx] ? 1f : 0f;
				data[baseIdx + 6] = ownUnitDensity[cellIdx];
				data[baseIdx + 7] = enemyBuildingCells[cellIdx] ? 1f : 0f;
				data[baseIdx + 8] = enemyUnitDensity[cellIdx];
				data[baseIdx + 9] = enemyThreat[cellIdx];
				data[baseIdx + 10] = friendlyCoverage[cellIdx];
			}

			// Convert float[] to byte[] for protobuf
			var bytes = new byte[data.Length * sizeof(float)];
			Buffer.BlockCopy(data, 0, bytes, 0, bytes.Length);

			obs.SpatialMap = Google.Protobuf.ByteString.CopyFrom(bytes);
			obs.SpatialChannels = SpatialChannelCount;
			obs.ExploredPercent = totalCells > 0 ? (float)exploredCells / totalCells * 100f : 0f;
		}
	}
}
