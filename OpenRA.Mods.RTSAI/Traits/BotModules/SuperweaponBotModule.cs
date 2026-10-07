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
using OpenRA.Mods.Cnc.Traits;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("Lets bots fire the two superweapons the stock SupportPowerBotModule cannot aim:",
		"a teleport (ChronoshiftPower: own army -> beside an enemy base, then attack) and a protection field",
		"(GrantExternalConditionPower: over the most valuable own army group that is in combat).")]
	public class SuperweaponBotModuleInfo : ConditionalTraitInfo, Requires<SupportPowerManagerInfo>
	{
		[Desc("OrderName of the teleport power (a ChronoshiftPower).")]
		public readonly string TeleportOrderName = "Chronoshift";

		[Desc("OrderName of the protection power (a GrantExternalConditionPower).")]
		public readonly string ShieldOrderName = "GrantExternalConditionPowerInfoOrder";

		[Desc("Own actor types never counted as army (harvesters, MCVs, engineers...).")]
		public readonly HashSet<string> ExcludeTypes = [];

		[Desc("Minimum value (cost) of the army group the teleport moves.")]
		public readonly int MinimumTeleportValue = 3000;

		[Desc("Only teleport a group at least this many cells away from the target (closer groups can drive).")]
		public readonly int MinimumTeleportDistance = 24;

		[Desc("Landing cells are searched on rings this many cells around the target building.")]
		public readonly int LandingMinRadius = 3;

		public readonly int LandingMaxRadius = 7;

		[Desc("Percentage of the group's value that must be able to land.")]
		public readonly int MinimumLandedPercent = 60;

		[Desc("Enemy armed actors within this many cells of the landing count as its defence.")]
		public readonly int DefenseRadius = 8;

		[Desc("Skip a target whose defence value exceeds this percentage of the landing group's value.")]
		public readonly int MaximumDefensePercent = 125;

		[Desc("Minimum value of own army inside the protection field.")]
		public readonly int MinimumShieldValue = 1800;

		[Desc("Fire the protection field only when enemy armed actors worth this much are this close.")]
		public readonly WDist ShieldEnemyRange = WDist.FromCells(7);

		public readonly int MinimumShieldEnemyValue = 1000;

		[Desc("Ticks between scans for a ready power that found no use.")]
		public readonly int ScanInterval = 75;

		[Desc("Ticks after a teleport before the landed units are sent at the target.")]
		public readonly int AttackDelay = 15;

		public override object Create(ActorInitializer init) { return new SuperweaponBotModule(init.Self, this); }
	}

	public class SuperweaponBotModule : ConditionalTrait<SuperweaponBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		readonly Dictionary<string, int> nextScan = [];
		readonly List<(int Tick, Actor[] Units, CPos Target)> pendingAttacks = [];
		SupportPowerManager supportPowerManager;

		public SuperweaponBotModule(Actor self, SuperweaponBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		protected override void Created(Actor self)
		{
			supportPowerManager = self.Owner.PlayerActor.Trait<SupportPowerManager>();
			base.Created(self);
		}

		void IBotTick.BotTick(IBot bot)
		{
			for (var i = pendingAttacks.Count - 1; i >= 0; i--)
			{
				var (tick, units, target) = pendingAttacks[i];
				if (tick > world.WorldTick)
					continue;

				foreach (var u in units.Where(u => !u.IsDead && u.IsInWorld && u.Owner == player))
					bot.QueueOrder(new Order("AttackMove", u, Target.FromCell(world, target), false));

				pendingAttacks.RemoveAt(i);
			}

			foreach (var sp in supportPowerManager.Powers.Values)
			{
				if (sp.Disabled || !sp.Ready || sp.Instances.Count == 0)
					continue;

				var orderName = sp.Info.OrderName;
				if (orderName != Info.TeleportOrderName && orderName != Info.ShieldOrderName)
					continue;

				if (nextScan.TryGetValue(sp.Key, out var next) && next > world.WorldTick)
					continue;

				nextScan[sp.Key] = world.WorldTick + Info.ScanInterval;
				if (orderName == Info.TeleportOrderName)
					TryTeleport(bot, sp);
				else
					TryShield(bot, sp);
			}
		}

		bool IsArmy(Actor a)
		{
			return a.Owner == player && a.IsInWorld && !a.IsDead && !Info.ExcludeTypes.Contains(a.Info.Name)
				&& a.Info.HasTraitInfo<MobileInfo>() && a.Info.HasTraitInfo<AttackBaseInfo>();
		}

		static int Value(Actor a) => a.Info.TraitInfoOrDefault<ValuedInfo>()?.Cost ?? 0;

		bool IsEnemy(Actor a) => !a.IsDead && a.IsInWorld && !a.Owner.NonCombatant
			&& player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy;

		// ------------------------------------------------------------------ teleport
		void TryTeleport(IBot bot, SupportPowerInstance sp)
		{
			var power = sp.Instances[0];
			var info = power.Info;
			var dims = (CVec)info.GetType().GetField("Dimensions").GetValue(info);
			var footprint = ((string)info.GetType().GetField("Footprint").GetValue(info)).Where(c => !char.IsWhiteSpace(c)).ToArray();

			Actor[] UnitsAt(CPos center) => power.CellsMatching(center, footprint, dims)
				.SelectMany(c => world.ActorMap.GetActorsAt(c)).Distinct()
				.Where(a => IsArmy(a) && a.TraitsImplementing<Chronoshiftable>().Any(cs => !cs.IsTraitDisabled))
				.ToArray();

			// The most valuable army group the field can hold.
			var army = world.ActorsHavingTrait<Chronoshiftable>().Where(IsArmy).ToList();
			if (army.Sum(Value) < Info.MinimumTeleportValue)
				return;

			var bestSource = CPos.Zero;
			var bestUnits = Array.Empty<Actor>();
			var bestValue = 0;
			foreach (var cell in army.Select(a => a.Location).Distinct())
			{
				var units = UnitsAt(cell);
				var value = units.Sum(Value);
				if (value > bestValue)
					(bestSource, bestUnits, bestValue) = (cell, units, value);
			}

			if (bestValue < Info.MinimumTeleportValue)
				return;

			// Known enemy buildings: the most valuable cluster that the group can take on.
			var enemyBuildings = world.ActorsHavingTrait<Building>()
				.Where(a => IsEnemy(a) && Value(a) > 0 && player.Shroud.IsExplored(a.Location)).ToList();
			if (enemyBuildings.Count == 0)
				return;

			var enemyArmed = world.ActorsHavingTrait<AttackBase>()
				.Where(a => IsEnemy(a) && player.Shroud.IsExplored(a.Location)).ToList();

			var targets = enemyBuildings
				.Where(b => (b.Location - bestSource).Length >= Info.MinimumTeleportDistance)
				.Select(b =>
				{
					var cluster = enemyBuildings.Where(o => (o.Location - b.Location).LengthSquared <= 36).Sum(Value);
					var defence = enemyArmed.Where(o => (o.Location - b.Location).LengthSquared <= Info.DefenseRadius * Info.DefenseRadius).Sum(Value);
					return (Building: b, Score: cluster - defence, Defence: defence);
				})
				.Where(t => t.Defence * 100 <= bestValue * Info.MaximumDefensePercent)
				.OrderByDescending(t => t.Score)
				.Take(3)
				.ToList();

			foreach (var (target, _, _) in targets)
			{
				var bestLanding = CPos.Zero;
				var bestLanded = 0;
				foreach (var landing in world.Map.FindTilesInAnnulus(target.Location, Info.LandingMinRadius, Info.LandingMaxRadius))
				{
					if (!player.Shroud.IsExplored(landing))
						continue;

					var delta = landing - bestSource;
					var landed = 0;
					foreach (var u in bestUnits)
					{
						var cell = u.Location + delta;
						var cs = u.TraitsImplementing<Chronoshiftable>().FirstOrDefault(c => !c.IsTraitDisabled);
						if (cs != null && player.Shroud.IsExplored(cell) && cs.CanChronoshiftTo(u, cell))
							landed += Value(u);
					}

					if (landed > bestLanded)
						(bestLanding, bestLanded) = (landing, landed);
				}

				if (bestLanded * 100 < bestValue * Info.MinimumLandedPercent)
					continue;

				bot.QueueOrder(new Order(sp.Key, supportPowerManager.Self, Target.FromCell(world, bestLanding), false)
				{
					ExtraLocation = bestSource,
					SuppressVisualFeedback = true
				});

				pendingAttacks.Add((world.WorldTick + Info.AttackDelay, bestUnits, target.Location));
				DoctrineLog.Write(player, $"superweapon teleport: {bestUnits.Length} units worth {bestValue} from {bestSource} " +
					$"to {bestLanding} beside {target.Info.Name} at {target.Location} ({bestLanded} can land)");
				return;
			}
		}

		// ------------------------------------------------------------------ protection field
		void TryShield(IBot bot, SupportPowerInstance sp)
		{
			if (sp.Instances[0] is not GrantExternalConditionPower power)
				return;

			var bestCenter = CPos.Zero;
			var bestValue = 0;
			foreach (var cell in world.ActorsHavingTrait<AttackBase>().Where(IsArmy).Select(a => a.Location).Distinct())
			{
				var value = power.UnitsInRange(cell).Where(IsArmy).Sum(Value);
				if (value <= bestValue)
					continue;

				var threat = world.FindActorsInCircle(world.Map.CenterOfCell(cell), Info.ShieldEnemyRange)
					.Where(a => IsEnemy(a) && a.Info.HasTraitInfo<AttackBaseInfo>() && a.CanBeViewedByPlayer(player))
					.Sum(Value);
				if (threat < Info.MinimumShieldEnemyValue)
					continue;

				(bestCenter, bestValue) = (cell, value);
			}

			if (bestValue < Info.MinimumShieldValue)
				return;

			bot.QueueOrder(new Order(sp.Key, supportPowerManager.Self, Target.FromCell(world, bestCenter), false)
			{
				SuppressVisualFeedback = true
			});

			DoctrineLog.Write(player, $"superweapon shield: army worth {bestValue} at {bestCenter}");
		}
	}
}
