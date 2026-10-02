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

using System.Collections.Frozen;
using System.Collections.Generic;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	public interface IStrategicRole
	{
		IReadOnlyCollection<string> Roles { get; }
		IReadOnlyCollection<string> Counters { get; }
		string Domain { get; }
		int AIWeight { get; }
		int TransportWeight { get; }
		string VeterancyCurve { get; }
	}

	// Moved from the alibad/OpenRA fork's Mods.Common (Traits/WorldWarIII/FactionDoctrine.cs) with the
	// modern faction data. It does not change the simulation; DoctrineUnitBuilderBotModule.RoleShares
	// reads it to recruit combined-arms armies.
	[Desc("Declares reusable strategic roles and balance metadata without changing actor simulation behavior.")]
	public class StrategicRoleInfo : TraitInfo
	{
		[Desc("Stable role tags used by doctrine AI, mission tooling, and composition templates.")]
		public readonly FrozenSet<string> Roles = FrozenSet<string>.Empty;

		[Desc("Role tags that this actor is designed to counter.")]
		public readonly FrozenSet<string> Counters = FrozenSet<string>.Empty;

		[Desc("Strategic domain: infantry, ground, air, naval, building, defense, logistics, or support.")]
		public readonly string Domain = "support";

		[Desc("Relative desirability used by composition-aware AI.")]
		public readonly int AIWeight = 100;

		[Desc("Cargo footprint used by transport and evacuation planning.")]
		public readonly int TransportWeight = 1;

		[Desc("Stable identifier for the intended veterancy progression.")]
		public readonly string VeterancyCurve = "standard";

		public override object Create(ActorInitializer init) { return new StrategicRole(this); }
	}

	public sealed class StrategicRole : IStrategicRole
	{
		readonly StrategicRoleInfo info;

		public StrategicRole(StrategicRoleInfo info) { this.info = info; }

		public IReadOnlyCollection<string> Roles => info.Roles;
		public IReadOnlyCollection<string> Counters => info.Counters;
		public string Domain => info.Domain;
		public int AIWeight => info.AIWeight;
		public int TransportWeight => info.TransportWeight;
		public string VeterancyCurve => info.VeterancyCurve;
	}
}
