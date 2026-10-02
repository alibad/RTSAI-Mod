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

using System.Collections.Generic;
using System.Linq;
using OpenRA.GameRules;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	/// <summary>Coarse attack domains based on the current mod's public target definitions.</summary>
	public sealed class ObservationWeaponTargets
	{
		readonly BitSet<TargetableType>[] targetProfiles;
		readonly Dictionary<WeaponInfo, (bool Air, bool Ground)> cache = [];

		public ObservationWeaponTargets(IEnumerable<BitSet<TargetableType>> targetProfiles)
		{
			this.targetProfiles = targetProfiles.Where(profile => !profile.IsEmpty).Distinct().ToArray();
		}

		public (bool Air, bool Ground) Summarize(IEnumerable<WeaponInfo> weapons)
		{
			var air = false;
			var ground = false;
			foreach (var weapon in weapons)
			{
				if (!cache.TryGetValue(weapon, out var domains))
				{
					foreach (var profile in targetProfiles)
					{
						if (!weapon.ValidTargets.Overlaps(profile) || weapon.InvalidTargets.Overlaps(profile))
							continue;

						if (profile.Contains("Air"))
							domains.Air = true;
						else
							domains.Ground = true;
					}

					cache.Add(weapon, domains);
				}

				air |= domains.Air;
				ground |= domains.Ground;
			}

			return (air, ground);
		}
	}
}
