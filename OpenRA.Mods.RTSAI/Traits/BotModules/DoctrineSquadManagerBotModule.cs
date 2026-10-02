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
using System.Reflection;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("The upstream SquadManagerBotModule, with the attack-squad size scaled by the faction's BotDoctrine",
		"(SquadSizeModifier). Bot profiles keep their own SquadSize; the doctrine biases it per faction.")]
	public class DoctrineSquadManagerBotModuleInfo : SquadManagerBotModuleInfo
	{
		// The upstream module reads these from its Info, so each doctrine bot gets its own copy of the info.
		static readonly FieldInfo SquadSizeField = typeof(SquadManagerBotModuleInfo).GetField(nameof(SquadSize));
		static readonly FieldInfo SquadSizeRandomBonusField = typeof(SquadManagerBotModuleInfo).GetField(nameof(SquadSizeRandomBonus));

		public override object Create(ActorInitializer init)
		{
			var doctrine = BotDoctrineInfo.For(init.Self);
			var info = this;
			if (doctrine != null && doctrine.SquadSizeModifier != 100)
			{
				info = (DoctrineSquadManagerBotModuleInfo)MemberwiseClone();
				SquadSizeField.SetValue(info, Scale(SquadSize, doctrine.SquadSizeModifier, 1));
				SquadSizeRandomBonusField.SetValue(info, Scale(SquadSizeRandomBonus, doctrine.SquadSizeModifier, 0));
			}

			// Every bot profile's module is created for every player; log the bots' (one line per profile).
			if (init.Self.Owner.IsBot)
				DoctrineLog.Write(init.Self.Owner, $"doctrine {doctrine?.Doctrine ?? "none"}; squad size {info.SquadSize} + random " +
					$"{info.SquadSizeRandomBonus} ({RequiresCondition?.Expression})");

			return new SquadManagerBotModule(init.Self, info);
		}

		static int Scale(int value, int percent, int minimum) => Math.Max(minimum, (value * percent + 50) / 100);
	}
}
