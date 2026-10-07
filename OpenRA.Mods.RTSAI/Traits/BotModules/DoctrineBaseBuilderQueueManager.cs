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
using System.Collections.Frozen;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	// Upstream BaseBuilderQueueManager for DoctrineBaseBuilderBotModule: adds the fork's opening
	// build order and does not let a queue without power plants deepen a power outage.
	sealed class DoctrineBaseBuilderQueueManager
	{
		public readonly string Category;
		public int WaitTicks;

		readonly DoctrineBaseBuilderBotModule baseBuilder;
		readonly World world;
		readonly Player player;
		readonly PowerManager playerPower;
		readonly PlayerResources playerResources;
		readonly IResourceLayer resourceLayer;

		Actor[] playerBuildings;
		int failCount;
		int failRetryTicks;
		string lastFailedBuilding;
		int checkForBasesTicks;
		int cachedBases;
		int cachedBuildings;
		int minimumExcessPower;
		CPos? baseCenterKeepsFailing = null;

		bool itemQueuedThisTick = false;

		WaterCheck waterState = WaterCheck.NotChecked;

		public DoctrineBaseBuilderQueueManager(DoctrineBaseBuilderBotModule baseBuilder, string category, Player p, PowerManager pm,
			PlayerResources pr, IResourceLayer rl)
		{
			this.baseBuilder = baseBuilder;
			world = p.World;
			player = p;
			playerPower = pm;
			playerResources = pr;
			resourceLayer = rl;
			Category = category;
			minimumExcessPower = baseBuilder.Info.MinimumExcessPower;
			if (baseBuilder.Info.NavalProductionTypes.Count == 0)
				waterState = WaterCheck.DontCheck;
		}

		public void Tick(IBot bot, ILookup<string, ProductionQueue> queuesByCategory)
		{
			// If we can't place any structures, give a nudge to BaseExpansionModules and hope it gets fixed.
			if (failCount >= baseBuilder.Info.MaximumFailedPlacementAttempts)
			{
				if (baseBuilder.BaseExpansionModules != null && baseCenterKeepsFailing != null)
				{
					// we should not give a nudge for defence
					if (!baseBuilder.Info.DefenseTypes.Contains(lastFailedBuilding))
					{
						var stuckConyard = baseBuilder.ConstructionYardBuildings.Actors
							.Where(a => (a.Location - baseCenterKeepsFailing.Value).LengthSquared <= baseBuilder.Info.MaxBaseRadius * baseBuilder.Info.MaxBaseRadius)
							.MinByOrDefault(a => (a.Location - baseCenterKeepsFailing.Value).LengthSquared);

						if (stuckConyard != null)
						{
							foreach (var be in baseBuilder.BaseExpansionModules)
								be.UpdateExpansionParams(bot, false, true, stuckConyard);
						}
					}

					failCount = 0;
				}

				// No BaseExpansionModules exist. Only bother resetting failCount when either
				// a) the number of buildings has decreased since last failure M ticks ago,
				// or b) number of BaseProviders (construction yard or similar) has increased since then.
				// Otherwise reset failRetryTicks instead to wait again.
				else if (baseBuilder.BaseExpansionModules == null && --failRetryTicks <= 0)
				{
					var currentBuildings = world.ActorsHavingTrait<Building>().Count(a => a.Owner == player);
					var baseProviders = world.ActorsHavingTrait<BaseProvider>().Count(a => a.Owner == player);

					if (currentBuildings < cachedBuildings || baseProviders > cachedBases)
						failCount = 0;
					else
						failRetryTicks = baseBuilder.Info.StructureProductionResumeDelay;
				}

				if (failCount >= baseBuilder.Info.MaximumFailedPlacementAttempts)
					return;
			}

			if (waterState == WaterCheck.NotChecked)
			{
				if (AIUtils.IsAreaAvailable<BaseProvider>(world, player, world.Map, baseBuilder.Info.MaxBaseRadius, baseBuilder.Info.WaterTerrainTypes)
					&& NavalTargetReachable())
					waterState = WaterCheck.EnoughWater;
				else
				{
					waterState = WaterCheck.NotEnoughWater;
					checkForBasesTicks = baseBuilder.Info.CheckForNewBasesDelay;
				}
			}

			if (waterState == WaterCheck.NotEnoughWater && --checkForBasesTicks <= 0)
			{
				var currentBases = world.ActorsHavingTrait<BaseProvider>().Count(a => a.Owner == player);

				if (currentBases > cachedBases)
				{
					cachedBases = currentBases;
					waterState = WaterCheck.NotChecked;
				}
			}

			// Only update once per second or so
			if (WaitTicks > 0)
				return;

			playerBuildings = world.ActorsHavingTrait<Building>().Where(a => a.Owner == player).ToArray();
			var excessPowerBonus =
				baseBuilder.Info.ExcessPowerIncrement *
				(playerBuildings.Length / baseBuilder.Info.ExcessPowerIncreaseThreshold.Clamp(1, int.MaxValue));
			minimumExcessPower =
				(baseBuilder.Info.MinimumExcessPower + excessPowerBonus)
					.Clamp(baseBuilder.Info.MinimumExcessPower, baseBuilder.Info.MaximumExcessPower);

			// PERF: Queue only one actor at a time per category
			itemQueuedThisTick = false;
			var active = false;
			foreach (var queue in queuesByCategory[Category])
			{
				if (TickQueue(bot, queue))
					active = true;
			}

			// Add a random factor so not every AI produces at the same tick early in the game.
			// Minimum should not be negative as delays in HackyAI could be zero.
			var randomFactor = world.LocalRandom.Next(0, baseBuilder.Info.StructureProductionRandomBonusDelay);

			WaitTicks = active ? baseBuilder.Info.StructureProductionActiveDelay + randomFactor
				: baseBuilder.Info.StructureProductionInactiveDelay + randomFactor;
		}

		bool TickQueue(IBot bot, ProductionQueue queue)
		{
			var currentBuilding = queue.AllQueued().FirstOrDefault();

			// Waiting to build something
			if (currentBuilding == null && failCount < baseBuilder.Info.MaximumFailedPlacementAttempts)
			{
				// PERF: We shouldn't be queueing new units when we're low on cash
				if (playerResources.GetCashAndResources() < baseBuilder.Info.ProductionMinCashRequirement || itemQueuedThisTick)
					return false;

				var item = ChooseBuildingToBuild(queue);
				if (item == null)
					return false;

				bot.QueueOrder(Order.StartProduction(queue.Actor, item.Name, 1));
				itemQueuedThisTick = true;
				DoctrineLog.Write(player, $"building {queue.Info.Type} {item.Name}");
			}
			else if (currentBuilding != null && currentBuilding.Done)
			{
				// Production is complete
				// Choose the placement logic
				// HACK: HACK HACK HACK
				// TODO: Derive this from BuildingCommonNames instead
				var type = BuildingType.Building;
				CPos? location = null;
				var actorVariant = 0;
				var orderString = "PlaceBuilding";

				// Check if Building is a plug for other Building
				var actorInfo = world.Map.Rules.Actors[currentBuilding.Item];
				var plugInfo = actorInfo.TraitInfoOrDefault<PlugInfo>();

				if (plugInfo != null)
				{
					var possibleBuilding = world.ActorsWithTrait<Pluggable>().FirstOrDefault(a =>
						a.Actor.Owner == player && a.Trait.AcceptsPlug(plugInfo.Type));

					if (possibleBuilding.Actor != null)
					{
						orderString = "PlacePlug";
						location = possibleBuilding.Actor.Location + possibleBuilding.Trait.Info.Offset;
						DoctrineLog.Write(player, $"plug {currentBuilding.Item} onto {possibleBuilding.Actor.Info.Name} at {location}");
					}
				}
				else
				{
					// Check if Building is a defense and if we should place it towards the enemy or not.
					if (baseBuilder.Info.DefenseTypes.Contains(actorInfo.Name) && world.LocalRandom.Next(100) < baseBuilder.Info.PlaceDefenseTowardsEnemyChance)
						type = BuildingType.Defense;
					else if (baseBuilder.Info.RefineryTypes.Contains(actorInfo.Name))
						type = BuildingType.Refinery;

					(location, baseCenterKeepsFailing, actorVariant) = ChooseBuildLocation(currentBuilding.Item, true, type);
				}

				if (location == null)
				{
					// If we just reached the maximum fail count, cache the number of current structures
					if (++failCount >= baseBuilder.Info.MaximumFailedPlacementAttempts)
					{
						AIUtils.BotDebug($"{player} has nowhere to place {currentBuilding.Item}");
						bot.QueueOrder(Order.CancelProduction(queue.Actor, currentBuilding.Item, 1));
						lastFailedBuilding = currentBuilding.Item;
						if (baseBuilder.BaseExpansionModules == null)
						{
							cachedBuildings = world.ActorsHavingTrait<Building>().Count(a => a.Owner == player);
							cachedBases = world.ActorsHavingTrait<BaseProvider>().Count(a => a.Owner == player);
						}
					}
				}
				else
				{
					failCount = 0;

					bot.QueueOrder(new Order(orderString, player.PlayerActor, Target.FromCell(world, location.Value), false)
					{
						// Building to place
						TargetString = currentBuilding.Item,

						// Actor variant will always be small enough to safely pack in a CPos
						ExtraLocation = new CPos(actorVariant, 0),

						// Actor ID to associate the placement with
						ExtraData = queue.Actor.ActorID,
						SuppressVisualFeedback = true
					});

					// After succesfuly placing a building, nudge BaseExpansionModules to expand.
					// We want to avoid expanding too often, so we make a judgement by counting buildings.
					if (baseBuilder.Info.ProductionTypes.Contains(currentBuilding.Item)
						|| baseBuilder.Info.TechTypes.Contains(currentBuilding.Item) || baseBuilder.Info.RefineryTypes.Contains(currentBuilding.Item))
					{
						var numRef = baseBuilder.RefineryBuildings.Actors.Count(a => !a.IsDead) + (baseBuilder.Info.RefineryTypes.Contains(currentBuilding.Item) ? 1 : 0);

						var numProd = baseBuilder.ProductionBuildings.Actors.Count(a => !a.IsDead) + (baseBuilder.Info.ProductionTypes.Contains(currentBuilding.Item) ? 1 : 0);

						var numTech = playerBuildings.Count(a => baseBuilder.Info.TechTypes.Contains(a.Info.Name))
							+ (baseBuilder.Info.TechTypes.Contains(currentBuilding.Item) ? 1 : 0);

						var tolerateOnCash = playerResources.GetCashAndResources() / Math.Max(baseBuilder.Info.PerExpansionTolerateOnCash, 1);

						if (numRef >= baseBuilder.Info.InititalMinimumRefineryCount + baseBuilder.Info.AdditionalMinimumRefineryCount
							&& numProd > 0 && numProd + numTech - baseBuilder.Info.ExpansionTolerate.Random(world.LocalRandom) - tolerateOnCash >= numRef)
						{
							var undeployEvenNoBase = numProd + numTech - baseBuilder.Info.ForceExpansionTolerate.Random(world.LocalRandom) - tolerateOnCash >= numRef;

							foreach (var be in baseBuilder.BaseExpansionModules)
								be.UpdateExpansionParams(bot, true, undeployEvenNoBase, null);
						}
					}

					return true;
				}
			}

			return true;
		}

		// RTS AI: the upstream water check accepts any 3x3 water near the base, so bots built shipyards and
		// ships on rivers and ponds that never reach the enemy (7-13% of their spending on the land maps of
		// docs/balance.md, round 4). Naval production now also needs a naval path from that water to water
		// within NavalTargetRadius cells of an enemy start location.
		bool NavalTargetReachable()
		{
			var info = baseBuilder.Info;
			if (info.NavalTargetRadius <= 0)
				return true;

			var map = world.Map;
			var locomotor = world.WorldActor.TraitsImplementing<Locomotor>().FirstOrDefault(l => l.Info.Name == info.NavalLocomotor);
			var pathFinder = world.WorldActor.TraitOrDefault<IPathFinder>();
			if (locomotor == null || pathFinder == null)
				return true;

			bool IsWater(CPos c) => map.Contains(c) && info.WaterTerrainTypes.Contains(map.GetTerrainInfo(c).Type);

			// Launch water: the 3x3 water areas the upstream check accepts, one representative per water body.
			var launch = new List<CPos>();
			foreach (var cell in world.ActorsHavingTrait<BaseProvider>().Where(a => a.Owner == player)
				.SelectMany(a => map.FindTilesInCircle(a.Location, info.MaxBaseRadius)))
			{
				if (!IsWater(cell) || !Util.AdjacentCells(world, Target.FromCell(world, cell)).All(IsWater))
					continue;

				if (!launch.Any(l => l == cell || pathFinder.PathExistsForLocomotor(locomotor, l, cell)))
					launch.Add(cell);
			}

			var reachable = launch.Count > 0 && world.Players
				.Where(p => p.Playable && !p.NonCombatant && p.RelationshipWith(player) == PlayerRelationship.Enemy)
				.SelectMany(p => map.FindTilesInCircle(p.HomeLocation, info.NavalTargetRadius))
				.Where(IsWater)
				.Any(target => launch.Any(l => pathFinder.PathExistsForLocomotor(locomotor, l, target)));

			DoctrineLog.Write(player, $"naval: {launch.Count} water bodies near the base; " +
				$"{(reachable ? "one reaches" : "none reaches")} within {info.NavalTargetRadius} cells of an enemy start");
			return reachable;
		}

		ActorInfo GetProducibleBuilding(FrozenSet<string> actors, IEnumerable<ActorInfo> buildables, Func<ActorInfo, int> orderBy = null)
		{
			var available = buildables.Where(actor =>
			{
				// Are we able to build this?
				if (!actors.Contains(actor.Name))
					return false;

				if (!baseBuilder.Info.BuildingLimits.TryGetValue(actor.Name, out var limit))
					return true;

				return playerBuildings.Count(a => a.Info.Name == actor.Name) < limit;
			});

			if (orderBy != null)
				return available.MaxByOrDefault(orderBy);

			return available.RandomOrDefault(world.LocalRandom);
		}

		bool HasSufficientPowerForActor(ActorInfo actorInfo)
		{
			return playerPower == null || actorInfo.TraitInfos<PowerInfo>().Where(i => i.EnabledByDefault)
				.Sum(p => p.Amount) + playerPower.ExcessPower >= baseBuilder.Info.MinimumExcessPower;
		}

		ActorInfo ChooseBuildingToBuild(ProductionQueue queue)
		{
			var buildableThings = queue.BuildableItems().ToList();

			// This gets used quite a bit, so let's cache it here
			var power = GetProducibleBuilding(baseBuilder.Info.PowerTypes, buildableThings,
				a => a.TraitInfos<PowerInfo>().Where(i => i.EnabledByDefault).Sum(p => p.Amount));

			// First priority is to get out of a low power situation
			if (playerPower != null && playerPower.ExcessPower < minimumExcessPower &&
				power != null && power.TraitInfos<PowerInfo>().Where(i => i.EnabledByDefault).Sum(p => p.Amount) > 0)
			{
				AIUtils.BotDebug("{0} decided to build {1}: Priority override (low power)", queue.Actor.Owner, power.Name);
				return power;
			}

			// An opt-in opening prevents random discretionary choices from starving
			// the first production facility. Low-power recovery still takes priority.
			var initial = DoctrineBaseBuilderBotModule.NextInitialBuilding(baseBuilder.InitialBuildOrder,
				buildableThings.Where(a => baseBuilder.Info.BuildingLimits == null ||
					!baseBuilder.Info.BuildingLimits.TryGetValue(a.Name, out var limit) || limit > 0).Select(a => a.Name),
				playerBuildings.Select(a => a.Info.Name).Concat(baseBuilder.BuildingsBeingProduced.Where(p => p.Value > 0).Select(p => p.Key)));
			if (initial != null)
			{
				var actor = world.Map.Rules.Actors[initial];
				if (HasSufficientPowerForActor(actor))
				{
					AIUtils.BotDebug("{0} decided to build {1}: Opening build order", queue.Actor.Owner, actor.Name);
					return actor;
				}

				if (power != null)
					return power;
			}

			// Next is to build up a strong economy
			if (baseBuilder.RequestedRefineries.Count > 0 || !baseBuilder.HasAdequateRefineryCount())
			{
				var refinery = GetProducibleBuilding(baseBuilder.Info.RefineryTypes, buildableThings);
				if (refinery != null && HasSufficientPowerForActor(refinery))
				{
					AIUtils.BotDebug("{0} decided to build {1}: Priority override (refinery)", queue.Actor.Owner, refinery.Name);
					return refinery;
				}

				if (power != null && refinery != null && !HasSufficientPowerForActor(refinery))
				{
					AIUtils.BotDebug("{0} decided to build {1}: Priority override (would be low power)", queue.Actor.Owner, power.Name);
					return power;
				}
			}

			// Make sure that we can spend as fast as we are earning
			if (baseBuilder.Info.NewProductionCashThreshold > 0 && playerResources.GetCashAndResources() > baseBuilder.Info.NewProductionCashThreshold
				&& world.LocalRandom.Next(100) < baseBuilder.Info.NewProductionChance)
			{
				var production = GetProducibleBuilding(baseBuilder.Info.ProductionTypes, buildableThings);
				if (production != null && HasSufficientPowerForActor(production))
				{
					AIUtils.BotDebug("{0} decided to build {1}: Priority override (production)", queue.Actor.Owner, production.Name);
					return production;
				}

				if (power != null && production != null && !HasSufficientPowerForActor(production))
				{
					AIUtils.BotDebug("{0} decided to build {1}: Priority override (would be low power)", queue.Actor.Owner, power.Name);
					return power;
				}
			}

			// Only consider building this if there is enough water inside the base perimeter and there are close enough adjacent buildings
			if (waterState == WaterCheck.EnoughWater && baseBuilder.Info.NewProductionCashThreshold > 0
				&& playerResources.GetCashAndResources() > baseBuilder.Info.NewProductionCashThreshold
				&& AIUtils.IsAreaAvailable<GivesBuildableArea>(world, player, world.Map, baseBuilder.Info.CheckForWaterRadius, baseBuilder.Info.WaterTerrainTypes))
			{
				var navalproduction = GetProducibleBuilding(baseBuilder.Info.NavalProductionTypes, buildableThings);
				if (navalproduction != null && HasSufficientPowerForActor(navalproduction))
				{
					AIUtils.BotDebug("{0} decided to build {1}: Priority override (navalproduction)", queue.Actor.Owner, navalproduction.Name);
					return navalproduction;
				}

				if (power != null && navalproduction != null && !HasSufficientPowerForActor(navalproduction))
				{
					AIUtils.BotDebug("{0} decided to build {1}: Priority override (would be low power)", queue.Actor.Owner, power.Name);
					return power;
				}
			}

			// Create some head room for resource storage if we really need it
			if (playerResources.Resources > 0.8 * playerResources.ResourceCapacity)
			{
				var silo = GetProducibleBuilding(baseBuilder.Info.SiloTypes, buildableThings);
				if (silo != null && HasSufficientPowerForActor(silo))
				{
					AIUtils.BotDebug("{0} decided to build {1}: Priority override (silo)", queue.Actor.Owner, silo.Name);
					return silo;
				}

				if (power != null && silo != null && !HasSufficientPowerForActor(silo))
				{
					AIUtils.BotDebug("{0} decided to build {1}: Priority override (would be low power)", queue.Actor.Owner, power.Name);
					return power;
				}
			}

			// Build everything else
			foreach (var frac in baseBuilder.Info.BuildingFractions.Shuffle(world.LocalRandom))
			{
				var name = frac.Key;

				// Does this building have initial delay, if so have we passed it?
				if (baseBuilder.Info.BuildingDelays != null &&
					baseBuilder.Info.BuildingDelays.TryGetValue(name, out var delay) &&
					delay > world.WorldTick)
					continue;

				// Can we build this structure?
				if (!buildableThings.Any(b => b.Name == name))
					continue;

				// Check the number of this structure and its variants
				var actorInfo = world.Map.Rules.Actors[name];

				// A plug (an upgrade placed onto an own building) is never counted as a building: build one
				// only while some own host still accepts it, so a finished plug always has somewhere to go.
				var plug = actorInfo.TraitInfoOrDefault<PlugInfo>();
				if (plug != null && !world.ActorsWithTrait<Pluggable>().Any(p => p.Actor.Owner == player && p.Trait.AcceptsPlug(plug.Type)))
					continue;

				var buildingVariantInfo = actorInfo.TraitInfoOrDefault<PlaceBuildingVariantsInfo>();
				var variants = buildingVariantInfo?.Actors ?? [];

				var count = playerBuildings.Count(a =>
					a.Info.Name == name || variants.Contains(a.Info.Name)) +
					(baseBuilder.BuildingsBeingProduced.TryGetValue(name, out var num) ? num : 0);

				// Do we want to build this structure?
				if (count * 100 > frac.Value * playerBuildings.Length)
					continue;

				if (baseBuilder.Info.BuildingLimits.TryGetValue(name, out var limit) && limit <= count)
					continue;

				// If we're considering to build a naval structure, check whether there is enough water inside the base perimeter
				// and any structure providing buildable area close enough to that water.
				// TODO: Extend this check to cover any naval structure, not just production.
				if (baseBuilder.Info.NavalProductionTypes.Contains(name)
					&& (waterState == WaterCheck.NotEnoughWater
						|| !AIUtils.IsAreaAvailable<GivesBuildableArea>(world, player, world.Map, baseBuilder.Info.CheckForWaterRadius, baseBuilder.Info.WaterTerrainTypes)))
					continue;

				// Will this put us into low power?
				var actor = world.Map.Rules.Actors[name];
				if (playerPower != null && (playerPower.ExcessPower < minimumExcessPower || !HasSufficientPowerForActor(actor)))
				{
					// Try building a power plant instead
					if (power != null && power.TraitInfos<PowerInfo>().Where(i => i.EnabledByDefault).Sum(pi => pi.Amount) > 0)
					{
						if (playerPower.PowerOutageRemainingTicks > 0)
							AIUtils.BotDebug("{0} decided to build {1}: Priority override (is low power)", queue.Actor.Owner, power.Name);
						else
							AIUtils.BotDebug("{0} decided to build {1}: Priority override (would be low power)", queue.Actor.Owner, power.Name);

						return power;
					}

					// This queue may not be able to produce a power plant (the
					// Defense queue is the important example). Do not let it make
					// the outage worse while the Building queue is recovering power.
					AIUtils.BotDebug("{0} skipped {1}: no power plant is available in queue {2}",
						queue.Actor.Owner, name, queue.Info.Type);
					return null;
				}

				// Lets build this
				AIUtils.BotDebug("{0} decided to build {1}: Desired is {2} ({3} / {4}); current is {5} / {4}",
					queue.Actor.Owner, name, frac.Value, frac.Value * playerBuildings.Length, playerBuildings.Length, count);
				return actor;
			}

			// Too spammy to keep enabled all the time, but very useful when debugging specific issues.
			// AIUtils.BotDebug("{0} couldn't decide what to build for queue {1}.", queue.Actor.Owner, queue.Info.Group);
			return null;
		}

		(CPos? Location, CPos? BaseCenter, int Variant) ChooseBuildLocation(string actorType, bool distanceToBaseIsImportant, BuildingType type)
		{
			var actorInfo = world.Map.Rules.Actors[actorType];
			var bi = actorInfo.TraitInfoOrDefault<BuildingInfo>();

			if (bi == null)
				return (null, null, 0);

			// Find the buildable cell that is closest to pos and centered around center
			(CPos? Location, CPos Center, int Variant) FindPos(CPos center, CPos target, int minRange, int maxRange, int? tryMaintainRange = null)
			{
				var actorVariant = 0;
				var buildingVariantInfo = actorInfo.TraitInfoOrDefault<PlaceBuildingVariantsInfo>();
				var variantActorInfo = actorInfo;
				var vbi = bi;

				var cells = world.Map.FindTilesInAnnulus(center, minRange, maxRange);

				// Sort by distance to target if we have one
				if (center != target)
				{
					if (tryMaintainRange == null)
						cells = cells.OrderBy(c => (c - target).LengthSquared);
					else
					{
						var theta = tryMaintainRange;
						var deta = (target - center).Length - tryMaintainRange;
						cells = cells.OrderBy(c => deta * (c - target).LengthSquared + theta * (c - center).LengthSquared);
					}

					// Rotate building if we have a Facings in buildingVariantInfo.
					// If we don't have Facings in buildingVariantInfo, use a random variant
					if (buildingVariantInfo?.Actors != null)
					{
						if (buildingVariantInfo.Facings != null)
						{
							var vector = world.Map.CenterOfCell(target) - world.Map.CenterOfCell(center);

							// The rotation Y point to upside vertically, so -Y = Y(rotation)
							var desireFacing = new WAngle(WAngle.ArcSin((int)((long)Math.Abs(vector.X) * 1024 / vector.Length)).Angle);
							if (vector.X > 0 && vector.Y >= 0)
								desireFacing = new WAngle(512) - desireFacing;
							else if (vector.X < 0 && vector.Y >= 0)
								desireFacing = new WAngle(512) + desireFacing;
							else if (vector.X < 0 && vector.Y < 0)
								desireFacing = -desireFacing;

							for (int i = 0, e = 1024; i < buildingVariantInfo.Facings.Length; i++)
							{
								var minDelta = Math.Min((desireFacing - buildingVariantInfo.Facings[i]).Angle, (buildingVariantInfo.Facings[i] - desireFacing).Angle);
								if (e > minDelta)
								{
									e = minDelta;
									actorVariant = i;
								}
							}
						}
						else
							actorVariant = world.LocalRandom.Next(buildingVariantInfo.Actors.Length + 1);
					}
				}
				else
				{
					cells = cells.Shuffle(world.LocalRandom);

					if (buildingVariantInfo?.Actors != null)
						actorVariant = world.LocalRandom.Next(buildingVariantInfo.Actors.Length + 1);
				}

				if (actorVariant != 0)
				{
					variantActorInfo = world.Map.Rules.Actors[buildingVariantInfo.Actors[actorVariant - 1]];
					vbi = variantActorInfo.TraitInfoOrDefault<BuildingInfo>();
				}

				foreach (var cell in cells)
				{
					if (!world.CanPlaceBuilding(cell, variantActorInfo, vbi, null))
						continue;

					if (distanceToBaseIsImportant && !vbi.IsCloseEnoughToBase(world, player, variantActorInfo, cell))
						continue;

					return (cell, center, actorVariant);
				}

				return (null, center, 0);
			}

			var baseCenter = type == BuildingType.Defense ? baseBuilder.GetDefenseBaseCenter() : baseBuilder.GetRandomBaseCenter();

			switch (type)
			{
				case BuildingType.Defense:

					// Build near the closest enemy
					var closestEnemy = world.ActorsHavingTrait<Targetable>()
						.Where(a => !a.Disposed && a.IsInWorld && player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy)
						.ClosestToIgnoringPath(world.Map.CenterOfCell(baseCenter));

					var targetCell = closestEnemy != null ? closestEnemy.Location : baseCenter;

					return FindPos(baseCenter, targetCell, baseBuilder.Info.MinBaseRadius, baseBuilder.Info.MaxBaseRadius, baseBuilder.Info.TryMaintainDefenseRange);

				case BuildingType.Refinery:

					var requestRef = baseBuilder.RequestedRefineries.Count > 0 ? baseBuilder.RequestedRefineries.Keys.First() : null;

					// Try and place the refinery near a resource field
					if (resourceLayer != null)
					{
						// If we have failed to place to the requested refinery point, try and place it near the base center
						var resourceBaseCenter = failCount > 0 ? baseCenter :
							(requestRef != null ? baseBuilder.RequestedRefineries[requestRef].ConyardLoc : (baseBuilder.ResourceConyardCenter ?? baseCenter));

						// If we have a ResourceMapModule, only consider the resource types it considers valuable
						// Otherwise consider any resource type
						var nearbyResources = world.Map
							.FindTilesInAnnulus(resourceBaseCenter, baseBuilder.Info.MinBaseRadius, baseBuilder.Info.MaxBaseRadius)
							.Where(c => baseBuilder.ResourceMapModule != null ?
							baseBuilder.ResourceMapModule.Info.ValuableResourceTypes.Contains(resourceLayer.GetResource(c).Type)
							: resourceLayer.GetResource(c).Type != null);

						// Find the closest refinery we have if we have any when not failing to place for the first time
						var closestRefinery = failCount <= 0
							? baseBuilder.RefineryBuildings.Actors.Where(a => !a.IsDead)?.ClosestToIgnoringPath(world.Map.CenterOfCell(resourceBaseCenter))
							: null;

						IEnumerable<CPos> resourcesShouldCheck = null;

						if (closestRefinery == null)
							resourcesShouldCheck = nearbyResources.Shuffle(world.LocalRandom).Take(baseBuilder.Info.MaxResourceCellsToCheck);
						else if (requestRef != null)
						{
							resourcesShouldCheck = nearbyResources.OrderBy(c => (c - baseBuilder.RequestedRefineries[requestRef].ResourceLoc).LengthSquared)
								.Take(baseBuilder.Info.MaxResourceCellsToCheck);
						}
						else
							resourcesShouldCheck = nearbyResources.OrderByDescending(c => (c - closestRefinery.Location).LengthSquared)
								.Take(baseBuilder.Info.MaxResourceCellsToCheck);

						foreach (var r in resourcesShouldCheck)
						{
							var found = FindPos(resourceBaseCenter, r, baseBuilder.Info.MinBaseRadius, baseBuilder.Info.MaxBaseRadius);
							if (found.Location != null)
							{
								if (baseBuilder.RequestedRefineries.Count > 0)
									baseBuilder.RequestedRefineries.Remove(requestRef);
								return found;
							}
						}
					}

					if (baseBuilder.RequestedRefineries.Count > 0)
						baseBuilder.RequestedRefineries.Remove(requestRef);

					// Try and find a free spot somewhere else in the base
					return FindPos(baseCenter, baseCenter, baseBuilder.Info.MinBaseRadius, baseBuilder.Info.MaxBaseRadius);

				case BuildingType.Building:
					return FindPos(baseCenter, baseCenter, baseBuilder.Info.MinBaseRadius,
						distanceToBaseIsImportant ? baseBuilder.Info.MaxBaseRadius : world.Map.Grid.MaximumTileSearchRange);
			}

			// Can't find a build location
			return (null, null, 0);
		}
	}
}
