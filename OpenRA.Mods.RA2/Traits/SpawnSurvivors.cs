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
using OpenRA.Mods.Common.Activities;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.RA2.Traits
{
	[Desc("Spawns survivors when an actor is destroyed or sold.")]
	public class SpawnSurvivorsInfo : ConditionalTraitInfo
	{
		[ActorReference]
		[FieldLoader.Require]
		[Desc("The actors spawned.")]
		public readonly string[] Actors = Array.Empty<string>();

		[Desc("DeathType(s) that trigger spawning. Leave empty to always spawn.")]
		public readonly BitSet<DamageType> DeathTypes = default;

		public override object Create(ActorInitializer actor) { return new SpawnSurvivors(this); }
	}

	[TraitLocation(SystemActors.Player)]
	[Desc("Swaps the actor types that " + nameof(SpawnSurvivors) + " creates for players of the listed factions,",
		"e.g. so a modern faction's destroyed building drops its own riflemen instead of a stock infantry type.")]
	public class SurvivorReplacementsInfo : TraitInfo<SurvivorReplacements>
	{
		[Desc("Factions this applies to. Leave empty for all factions.")]
		public readonly FrozenSet<string> Factions = FrozenSet<string>.Empty;

		[ActorReference(dictionaryReference: LintDictionaryReference.Keys | LintDictionaryReference.Values)]
		[Desc("Survivor actor type => the type spawned instead.")]
		public readonly Dictionary<string, string> Replacements = [];
	}

	public class SurvivorReplacements { }

	public class SpawnSurvivors : ConditionalTrait<SpawnSurvivorsInfo>, INotifyKilled
	{
		public SpawnSurvivors(SpawnSurvivorsInfo info)
			: base(info) { }

		void INotifyKilled.Killed(Actor self, AttackInfo attack)
		{
			if (IsTraitDisabled)
				return;

			if (!Info.DeathTypes.IsEmpty && !attack.Damage.DamageTypes.Overlaps(Info.DeathTypes))
				return;

			Spawn(self);
		}

		void Spawn(Actor self)
		{
			var buildingInfo = self.Info.TraitInfoOrDefault<BuildingInfo>();
			var eligibleLocations = buildingInfo != null
				? buildingInfo.Tiles(self.Location).ToList()
				: new List<CPos>() { self.World.Map.CellContaining(self.CenterPosition) };

			var faction = self.Owner.Faction.InternalName;
			var replacements = self.Owner.PlayerActor.Info.TraitInfos<SurvivorReplacementsInfo>()
				.Where(r => r.Factions.Count == 0 || r.Factions.Contains(faction))
				.ToList();

			self.World.AddFrameEndTask(w =>
			{
				foreach (var survivor in Info.Actors)
				{
					var actorType = survivor;
					foreach (var r in replacements)
						if (r.Replacements.TryGetValue(survivor, out var replacement))
							actorType = replacement;

					var td = new TypeDictionary
					{
						new OwnerInit(self.Owner),
						new LocationInit(eligibleLocations.Random(w.SharedRandom))
					};

					var unit = w.CreateActor(true, actorType.ToLowerInvariant(), td);
					if (unit.TraitOrDefault<Mobile>() != null)
						unit.QueueActivity(false, new Nudge(unit));
				}
			});
		}
	}
}
