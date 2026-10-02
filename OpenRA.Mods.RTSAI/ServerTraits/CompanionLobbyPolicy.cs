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
using System.Linq;
using OpenRA.Mods.RTSAI.Traits;
using OpenRA.Network;
using OpenRA.Server;
using S = OpenRA.Server.Server;

namespace OpenRA.Mods.RTSAI.Server
{
	/// <summary>
	/// Multiplayer policy for the "AI co-commander" lobby option: on in single-human games, off
	/// while two or more humans are in the lobby. Once the host sets the option explicitly, the
	/// host's choice is kept. Must be listed before LobbyCommands in mod.yaml so it sees the
	/// host's "option" command before LobbyCommands consumes it.
	/// </summary>
	public class CompanionLobbyPolicy : ServerTrait, IInterpretCommand, INotifySyncLobbyInfo
	{
		bool hostChose;

		public static string DefaultFor(int humans) => (humans < 2).ToString();

		bool IInterpretCommand.InterpretCommand(S server, Connection conn, Session.Client client, string cmd)
		{
			if (client != null && client.IsAdmin)
			{
				if (cmd.StartsWith($"option {CompanionLobbyOptionInfo.OptionId} ", StringComparison.Ordinal))
					hostChose = true;
				else if (cmd == "reset_options")
					hostChose = false;
			}

			// Never consume the command: LobbyCommands validates and applies it.
			return false;
		}

		void INotifySyncLobbyInfo.LobbyInfoSynced(S server)
		{
			if (hostChose || server.State != ServerState.WaitingPlayers)
				return;

			lock (server.LobbyInfoLock)
			{
				if (!server.LobbyInfo.GlobalSettings.LobbyOptions.TryGetValue(CompanionLobbyOptionInfo.OptionId, out var option)
					|| option.IsLocked)
					return;

				var desired = DefaultFor(server.LobbyInfo.NonBotClients.Count());
				if (option.Value == desired)
					return;

				// Value only: PreferredValue stays the map default, so a map change re-applies the policy.
				option.Value = desired;
			}

			server.SyncLobbyGlobalSettings();
		}
	}
}
