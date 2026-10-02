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
using System.Collections.Immutable;
using System.Linq;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	// The upstream UnitBuilderBotModule plus the alibad/OpenRA fork's role-aware production
	// (54a854e4a5, c3eb3dd94f, 97631433cb): StrategicRole shares balanced per production queue.
	// RTS AI adds the faction doctrine (BotDoctrine), which biases the profile's role shares.
	[TraitLocation(SystemActors.Player)]
	[Desc("Controls AI unit production by battlefield role (combined arms) and per-actor shares.")]
	public class DoctrineUnitBuilderBotModuleInfo : ConditionalTraitInfo
	{
		[Desc("If > 0, only produce units as long as there are less than this amount of units idling inside the base.",
			"Beware: if it is less than squad size, e.g. the `SquadSize` from `SquadManagerBotModule`, " +
			"the bot might get stuck as there aren't enough idle units to create squad.")]
		public readonly int IdleBaseUnitsMaximum = -1;

		[Desc("Production queues AI uses for producing units.")]
		public readonly ImmutableArray<string> UnitQueues = ["Vehicle", "Infantry", "Plane", "Ship", "Aircraft"];

		[Desc("What units to the AI should build.", "What relative share of the total army must be this type of unit.")]
		public readonly FrozenDictionary<string, int> UnitsToBuild = FrozenDictionary<string, int>.Empty;

		[Desc("Optional strategic-role shares used before actor-specific shares.",
			"Roles are supplied by StrategicRole traits and let new faction actors join doctrine AI without editing this list.",
			"Composition is balanced within each production queue so unrelated queues cannot starve specialist roles.",
			"A BotDoctrine for the player's faction scales these shares.")]
		public readonly FrozenDictionary<string, int> RoleShares = FrozenDictionary<string, int>.Empty;

		[Desc("What units should the AI have a maximum limit to train.")]
		public readonly FrozenDictionary<string, int> UnitLimits = null;

		[Desc("When should the AI start train specific units.")]
		public readonly FrozenDictionary<string, int> UnitDelays = null;

		[Desc("Only queue construction of a new unit when above this requirement.")]
		public readonly int ProductionMinCashRequirement = 500;

		public static IReadOnlyCollection<string> GetUnitTypesToTrack(FrozenDictionary<string, int> unitsToBuild,
			FrozenDictionary<string, int> roleShares, ImmutableArray<string> unitQueues, IEnumerable<ActorInfo> actors)
		{
			return unitsToBuild.Keys.Concat(actors.Where(actor => !actor.Name.StartsWith('^') &&
				actor.TraitInfoOrDefault<BuildableInfo>() is { } buildable && buildable.Queue.Any(unitQueues.Contains) &&
				actor.TraitInfos<StrategicRoleInfo>().Any(role => role.Roles.Any(id =>
					roleShares.TryGetValue(id, out var share) && share > 0))).Select(actor => actor.Name)).Distinct().ToArray();
		}

		public override object Create(ActorInitializer init) { return new DoctrineUnitBuilderBotModule(init.Self, this); }
	}

	public class DoctrineUnitBuilderBotModule : ConditionalTrait<DoctrineUnitBuilderBotModuleInfo>,
		IBotTick, IBotNotifyIdleBaseUnits, IBotRequestUnitProduction, IGameSaveTraitData, INotifyActorDisposing
	{
		public const int FeedbackTime = 30; // ticks; = a bit over 1s. must be >= netlag.

		readonly World world;
		readonly Player player;

		readonly List<string> queuedBuildRequests = [];
		readonly ActorIndex.OwnerAndNames unitsToBuild;

		// The profile's role shares after the faction doctrine.
		public readonly FrozenDictionary<string, int> RoleShares;

		// Anti-air response (BotDoctrine.AirDefenseShare): the shares in use switch to airDefenseShares while the
		// visible enemy air value exceeds the bot's own air defense.
		const int AirCheckInterval = 150;
		readonly BotDoctrineInfo doctrine;
		readonly FrozenDictionary<string, int> airDefenseShares;
		FrozenDictionary<string, int> activeRoleShares;
		bool airAlert;

		IBotRequestPauseUnitProduction[] requestPause;
		int idleUnitCount;
		int currentQueueIndex = 0;
		PlayerResources playerResources;

		int ticks;

		public DoctrineUnitBuilderBotModule(Actor self, DoctrineUnitBuilderBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
			doctrine = BotDoctrineInfo.For(self);
			RoleShares = doctrine?.Apply(info.RoleShares) ?? info.RoleShares;
			activeRoleShares = RoleShares;
			airDefenseShares = doctrine != null && doctrine.AirDefenseShare > 0 ? doctrine.WithAirDefense(RoleShares) : null;
			unitsToBuild = new ActorIndex.OwnerAndNames(world,
				DoctrineUnitBuilderBotModuleInfo.GetUnitTypesToTrack(info.UnitsToBuild, RoleShares, info.UnitQueues, world.Map.Rules.Actors.Values),
				player);
		}

		protected override void Created(Actor self)
		{
			requestPause = self.Owner.PlayerActor.TraitsImplementing<IBotRequestPauseUnitProduction>().ToArray();
			playerResources = self.Owner.PlayerActor.Trait<PlayerResources>();
		}

		protected override void TraitEnabled(Actor self)
		{
			var doctrine = BotDoctrineInfo.For(self);
			DoctrineLog.Write(player, $"doctrine {doctrine?.Doctrine ?? "none"}; role shares " +
				DoctrineLog.Describe(RoleShares.Where(kv => kv.Value > 0).OrderByDescending(kv => kv.Value).Select(kv => $"{kv.Key} {kv.Value}")));
		}

		void IBotNotifyIdleBaseUnits.UpdatedIdleBaseUnits(List<Actor> idleUnits)
		{
			idleUnitCount = idleUnits.Count;
		}

		void IBotTick.BotTick(IBot bot)
		{
			// PERF: We shouldn't be queueing new units when we're low on cash
			if (playerResources.GetCashAndResources() < Info.ProductionMinCashRequirement || requestPause.Any(rp => rp.PauseUnitProduction))
				return;

			ticks++;

			if (airDefenseShares != null && ticks % AirCheckInterval == 0)
				UpdateAirDefense();

			if (ticks % FeedbackTime == 0)
			{
				ILookup<string, ProductionQueue> queuesByCategory = null;

				var buildRequest = queuedBuildRequests.FirstOrDefault();
				if (buildRequest != null)
				{
					queuesByCategory ??= AIUtils.FindQueuesByCategory(player);
					BuildUnit(bot, buildRequest, queuesByCategory);
					queuedBuildRequests.Remove(buildRequest);
				}

				if (Info.IdleBaseUnitsMaximum <= 0 || Info.IdleBaseUnitsMaximum > idleUnitCount)
				{
					queuesByCategory ??= AIUtils.FindQueuesByCategory(player);
					for (var i = 0; i < Info.UnitQueues.Length; i++)
					{
						if (++currentQueueIndex >= Info.UnitQueues.Length)
							currentQueueIndex = 0;

						var category = Info.UnitQueues[currentQueueIndex];
						var queues = queuesByCategory[category].ToArray();
						if (queues.Length != 0)
						{
							// PERF: We tick only one type of valid queue at a time
							// if AI gets enough cash, it can fill all of its queues with enough ticks
							BuildRandomUnit(bot, queues);
							break;
						}
					}
				}
			}
		}

		void IBotRequestUnitProduction.RequestUnitProduction(IBot bot, string requestedActor)
		{
			queuedBuildRequests.Add(requestedActor);
		}

		int IBotRequestUnitProduction.RequestedProductionCount(IBot bot, string requestedActor)
		{
			return queuedBuildRequests.Count(r => r == requestedActor);
		}

		void BuildRandomUnit(IBot bot, ProductionQueue[] queues)
		{
			if (Info.UnitsToBuild.Count == 0 && activeRoleShares.Count == 0)
				return;

			// Pick a free queue
			var queue = queues.FirstOrDefault(q => !q.AllQueued().Any());
			if (queue == null)
				return;

			var unit = ChooseRandomUnitToBuild(queue);

			if (unit == null)
				return;

			bot.QueueOrder(Order.StartProduction(queue.Actor, unit.Name, 1));
			DoctrineLog.Write(player, $"unit {queue.Info.Type} {unit.Name} " +
				$"[{DoctrineLog.Describe(unit.TraitInfos<StrategicRoleInfo>().SelectMany(r => r.Roles))}]");
		}

		// In cases where we want to build a specific unit but don't know the queue name (because there's more than one possibility)
		void BuildUnit(IBot bot, string name, ILookup<string, ProductionQueue> queuesByCategory)
		{
			var actorInfo = world.Map.Rules.Actors[name];
			if (actorInfo == null)
				return;

			var buildableInfo = actorInfo.TraitInfoOrDefault<BuildableInfo>();
			if (buildableInfo == null)
				return;

			ProductionQueue queue = null;
			foreach (var pq in buildableInfo.Queue)
			{
				queue = queuesByCategory[pq].FirstOrDefault(q => !q.AllQueued().Any());
				if (queue != null)
					break;
			}

			if (queue != null)
			{
				bot.QueueOrder(Order.StartProduction(queue.Actor, name, 1));
				AIUtils.BotDebug("{0} decided to build {1} (external request)", queue.Actor.Owner, name);
				DoctrineLog.Write(player, $"unit {queue.Info.Type} {name} [requested]");
			}
		}

		ActorInfo ChooseRandomUnitToBuild(ProductionQueue queue)
		{
			var buildableThings = queue.BuildableItems().Shuffle(world.LocalRandom).ToArray();
			var allUnits = unitsToBuild.Actors.Where(a => !a.IsDead).Select(actor => actor.Info).ToArray();
			return ChooseUnitToBuild(Info, activeRoleShares, buildableThings, allUnits, world.WorldTick, HasAdequateAirUnitReloadBuildings, queue.Info.Type);
		}

		static int CostOf(ActorInfo actor) => actor.TraitInfoOrDefault<ValuedInfo>()?.Cost ?? 0;

		void UpdateAirDefense()
		{
			var enemyAir = 0;
			foreach (var actor in world.Actors)
			{
				if (actor.IsDead || !actor.IsInWorld || actor.Owner == null || player.RelationshipWith(actor.Owner) != PlayerRelationship.Enemy)
					continue;

				if (actor.GetEnabledTargetTypes().Overlaps(doctrine.AirThreatTargetTypes) && actor.CanBeViewedByPlayer(player))
					enemyAir += CostOf(actor.Info);
			}

			var ownAirDefense = unitsToBuild.Actors.Where(a => !a.IsDead && a.Info.TraitInfos<StrategicRoleInfo>()
				.Any(r => r.Roles.Contains(doctrine.AirDefenseRole))).Sum(a => CostOf(a.Info));
			var alert = enemyAir > 0 && (long)ownAirDefense * 100 < (long)enemyAir * doctrine.AirDefenseRatio;
			if (alert == airAlert)
				return;

			airAlert = alert;
			activeRoleShares = alert ? airDefenseShares : RoleShares;
			DoctrineLog.Write(player, $"air defense {(alert ? "on" : "off")}: enemy air {enemyAir}, own {ownAirDefense}");
		}

		public static ActorInfo ChooseUnitToBuild(DoctrineUnitBuilderBotModuleInfo info, FrozenDictionary<string, int> roleShares,
			ActorInfo[] candidates, ActorInfo[] allUnits, int currentTick, Func<ActorInfo, bool> isAvailable, string productionQueue = null)
		{
			// Reject blocked candidates before ranking. A preferred aircraft without
			// a rearm slot must not starve another usable aircraft in the same queue.
			var buildableThings = candidates.Where(unit =>
				(info.UnitDelays == null || !info.UnitDelays.TryGetValue(unit.Name, out var delay) || delay <= currentTick) &&
				(info.UnitLimits == null || !info.UnitLimits.TryGetValue(unit.Name, out var limit) ||
					allUnits.Count(owned => owned.Name == unit.Name) < limit) && isAvailable(unit)).ToArray();
			var roleUnit = ChooseRoleUnitToBuild(roleShares, buildableThings, allUnits, productionQueue);
			if (roleUnit != null)
				return roleUnit;

			ActorInfo desiredUnit = null;
			var desiredError = int.MaxValue;
			foreach (var unit in buildableThings)
			{
				if (!info.UnitsToBuild.TryGetValue(unit.Name, out var share) || share <= 0)
					continue;

				var unitCount = allUnits.Count(a => a.Name == unit.Name);
				var error = allUnits.Length > 0 ? unitCount * 100 / allUnits.Length - share : -1;
				if (error < 0)
					return unit;

				if (error < desiredError)
				{
					desiredError = error;
					desiredUnit = unit;
				}
			}

			return desiredUnit;
		}

		static ActorInfo ChooseRoleUnitToBuild(FrozenDictionary<string, int> roleShares, ActorInfo[] buildableThings, ActorInfo[] allUnits,
			string productionQueue)
		{
			if (roleShares.Count == 0)
				return null;

			// Limits, delays and rearm requirements have already removed candidates
			// we cannot recruit. Normalize only the roles still available in this
			// queue, deduplicating roles shared by several alternative actors.
			var availableRoles = buildableThings.SelectMany(a => a.TraitInfos<StrategicRoleInfo>())
				.SelectMany(role => role.Roles).Distinct()
				.Where(role => roleShares.TryGetValue(role, out var share) && share > 0)
				.ToDictionary(role => role, role => roleShares[role]);
			if (availableRoles.Count == 0)
				return null;

			// Independent queues fill at different rates. Comparing a factory's tank,
			// artillery and drone roles with a rapidly growing infantry/naval army can
			// leave tanks permanently deficient and prevent the first drone forever.
			// Keep explicitly tracked transformed actors without Buildable metadata.
			var taggedUnits = allUnits.Where(a => (productionQueue == null ||
				!a.HasTraitInfo<BuildableInfo>() || a.TraitInfo<BuildableInfo>().Queue.Contains(productionQueue)) &&
				a.TraitInfos<StrategicRoleInfo>()
				.Any(role => role.Roles.Any(availableRoles.ContainsKey))).ToArray();
			var totalShare = availableRoles.Values.Sum(share => (long)share);
			var desiredError = long.MaxValue;
			ActorInfo desiredUnit = null;

			foreach (var unit in buildableThings)
			{
				foreach (var role in unit.TraitInfos<StrategicRoleInfo>().SelectMany(roleInfo => roleInfo.Roles).Distinct())
				{
					if (!availableRoles.TryGetValue(role, out var share))
						continue;

					var roleCount = taggedUnits.Count(a => a.TraitInfos<StrategicRoleInfo>()
						.Any(roleInfo => roleInfo.Roles.Contains(role)));

					// Cross-multiply normalized shares: no floating point or percentage
					// rounding, and multiplying every configured weight changes nothing.
					var error = taggedUnits.Length > 0 ? roleCount * totalShare - (long)share * taggedUnits.Length : -share;
					if (error < desiredError)
					{
						desiredError = error;
						desiredUnit = unit;
					}
				}
			}

			return desiredUnit;
		}

		// For mods like RA (number of RearmActors must match the number of aircraft)
		bool HasAdequateAirUnitReloadBuildings(ActorInfo actorInfo)
		{
			var aircraftInfo = actorInfo.TraitInfoOrDefault<AircraftInfo>();
			if (aircraftInfo == null)
				return true;

			// If actor isn't Rearmable, it doesn't need a RearmActor to reload
			var rearmableInfo = actorInfo.TraitInfoOrDefault<RearmableInfo>();
			if (rearmableInfo == null)
				return true;

			var countOwnAir = AIUtils.CountActorsWithNameAndTrait<IPositionable>(actorInfo.Name, player);
			var countBuildings = rearmableInfo.RearmActors.Sum(b => AIUtils.CountActorsWithNameAndTrait<Building>(b, player));
			if (countOwnAir >= countBuildings)
				return false;

			return true;
		}

		List<MiniYamlNode> IGameSaveTraitData.IssueTraitData(Actor self)
		{
			if (IsTraitDisabled)
				return null;

			return
			[
				new("QueuedBuildRequests", FieldSaver.FormatValue(queuedBuildRequests.ToArray())),
				new("IdleUnitCount", FieldSaver.FormatValue(idleUnitCount))
			];
		}

		void IGameSaveTraitData.ResolveTraitData(Actor self, MiniYaml data)
		{
			if (self.World.IsReplay)
				return;

			var queuedBuildRequestsNode = data.NodeWithKeyOrDefault("QueuedBuildRequests");
			if (queuedBuildRequestsNode != null)
			{
				queuedBuildRequests.Clear();
				queuedBuildRequests.AddRange(FieldLoader.GetValue<ImmutableArray<string>>("QueuedBuildRequests", queuedBuildRequestsNode.Value.Value));
			}

			var idleUnitCountNode = data.NodeWithKeyOrDefault("IdleUnitCount");
			if (idleUnitCountNode != null)
				idleUnitCount = FieldLoader.GetValue<int>("IdleUnitCount", idleUnitCountNode.Value.Value);
		}

		void INotifyActorDisposing.Disposing(Actor self)
		{
			unitsToBuild.Dispose();
		}
	}
}
