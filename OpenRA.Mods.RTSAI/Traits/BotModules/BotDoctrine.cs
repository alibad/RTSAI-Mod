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
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("How bots of the listed factions play: the doctrine shapes the role mix of every bot profile",
		"(DoctrineUnitBuilderBotModule.RoleShares), the opening (DoctrineBaseBuilderBotModule.InitialBuildOrder)",
		"and the attack-squad size (DoctrineSquadManagerBotModule).",
		"Bot profiles (normal, rush, turtle, naval) set the base plan; the faction doctrine biases it.")]
	public class BotDoctrineInfo : TraitInfo<BotDoctrine>
	{
		[FieldLoader.Require]
		[Desc("Faction internal names that play this doctrine.")]
		public readonly FrozenSet<string> Factions = [];

		[Desc("Stable doctrine identifier, for logs and tooling.")]
		public readonly string Doctrine = null;

		[Desc("Percent multiplier per StrategicRole applied to the bot profile's RoleShares. Unlisted roles keep 100.")]
		public readonly FrozenDictionary<string, int> RoleShareModifiers = FrozenDictionary<string, int>.Empty;

		[ActorReference]
		[Desc("Faction opening. Replaces the bot profile's InitialBuildOrder for these factions when not empty.",
			"A building listed n times is wanted n times (e.g. a second refinery).")]
		public readonly ImmutableArray<string> InitialBuildOrder = [];

		[Desc("Percent multiplier applied to the bot profile's attack-squad size (SquadSize and SquadSizeRandomBonus",
			"of DoctrineSquadManagerBotModule). Below 100 attacks earlier in smaller groups; above 100 masses first.")]
		public readonly int SquadSizeModifier = 100;

		[Desc("Anti-air response for factions whose air defense cannot fight ground units: while the visible enemy",
			"aircraft outvalue AirDefenseRatio percent of the bot's own AirDefenseRole units, that role's share is",
			"raised to at least this value (DoctrineUnitBuilderBotModule). 0 disables the response.")]
		public readonly int AirDefenseShare = 0;

		[Desc("StrategicRole that answers aircraft.")]
		public readonly string AirDefenseRole = "anti-air";

		[Desc("Own air-defense value wanted, in percent of the visible enemy air value.")]
		public readonly int AirDefenseRatio = 100;

		[Desc("Target types that make a visible enemy actor an air threat (airborne units).")]
		public readonly BitSet<TargetableType> AirThreatTargetTypes = new("Air");

		// Called from bot module constructors, while the player actor is still being created.
		public static BotDoctrineInfo For(Actor playerActor)
		{
			var faction = playerActor.Owner.Faction?.InternalName;
			return faction == null ? null : playerActor.Info.TraitInfos<BotDoctrineInfo>()
				.FirstOrDefault(d => d.Factions.Contains(faction));
		}

		// The role shares while answering an air threat: AirDefenseRole raised to AirDefenseShare.
		public FrozenDictionary<string, int> WithAirDefense(FrozenDictionary<string, int> roleShares)
		{
			var shares = roleShares.ToDictionary(kv => kv.Key, kv => kv.Value);
			shares[AirDefenseRole] = Math.Max(shares.GetValueOrDefault(AirDefenseRole), AirDefenseShare);
			return shares.ToFrozenDictionary();
		}

		public FrozenDictionary<string, int> Apply(FrozenDictionary<string, int> roleShares)
		{
			if (RoleShareModifiers.Count == 0)
				return roleShares;

			return roleShares.ToFrozenDictionary(kv => kv.Key,
				kv => RoleShareModifiers.TryGetValue(kv.Key, out var percent) ? kv.Value * percent / 100 : kv.Value);
		}
	}

	public class BotDoctrine { }

	// Opt-in decision log for balance runs: set RTSAI_BOT_LOG=1 to write <support>/Logs/bot-doctrine.log.
	static class DoctrineLog
	{
		const string Channel = "bot-doctrine";
		static readonly bool Enabled = Environment.GetEnvironmentVariable("RTSAI_BOT_LOG") == "1";
		static bool added;

		public static void Write(Player player, string message)
		{
			if (!Enabled)
				return;

			if (!added)
			{
				Log.AddChannel(Channel, "bot-doctrine.log");
				added = true;
			}

			Log.Write(Channel, $"{player.World.WorldTick} {player.InternalName} {player.Faction?.InternalName}: {message}");
		}

		public static string Describe(IEnumerable<string> values) => string.Join(", ", values);
	}
}
