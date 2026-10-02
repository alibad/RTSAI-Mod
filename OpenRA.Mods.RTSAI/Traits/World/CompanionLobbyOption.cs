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
using OpenRA.Network;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	[Desc("The lobby's 'AI co-commander' checkbox. Every player sees it; only the host can change it.",
		"It starts on; CompanionLobbyPolicy (a server trait) turns it off while two or more humans are in the lobby,",
		"until the host sets it explicitly. When off, the companion bridge refuses advice, actions and AUTO for the match.")]
	[TraitLocation(SystemActors.World | SystemActors.EditorWorld)]
	public class CompanionLobbyOptionInfo : TraitInfo<CompanionLobbyOption>, ILobbyOptions
	{
		public const string OptionId = "rtsai-cocommander";

		[FluentReference]
		[Desc("Label of the checkbox in the lobby.")]
		public readonly string CheckboxLabel = "checkbox-ai-cocommander.label";

		[FluentReference]
		[Desc("Tooltip of the checkbox in the lobby.")]
		public readonly string CheckboxDescription = "checkbox-ai-cocommander.description";

		[Desc("Display order of the checkbox in the lobby.")]
		public readonly int CheckboxDisplayOrder = 0;

		IEnumerable<LobbyOption> ILobbyOptions.LobbyOptions(MapPreview map)
		{
			yield return new LobbyBooleanOption(map, OptionId, CheckboxLabel, CheckboxDescription, true, CheckboxDisplayOrder, true, false);
		}

		/// <summary>
		/// The match's setting. Without the option (an old lobby or replay) the co-commander is
		/// allowed only when at most one human is present, matching the lobby default.
		/// </summary>
		public static bool AllowedFor(Session lobby)
		{
			var fallback = lobby.NonBotClients.Count() < 2;
			return lobby.GlobalSettings.OptionOrDefault(OptionId, fallback);
		}
	}

	public class CompanionLobbyOption { }
}
