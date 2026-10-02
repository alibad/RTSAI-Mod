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

using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Common.Widgets.Logic;
using OpenRA.Mods.RTSAI.Traits;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	public static class AIControlDisplay
	{
		public static bool IsExplicitManualModeState(string state)
		{
			if (string.IsNullOrWhiteSpace(state))
				return false;

			var separator = state.IndexOf(':');
			var lifecycle = separator < 0 ? state : state[..separator];

			// Only the companion's durable, strategy-qualified idle state means
			// AUTO was explicitly disabled. Transient voice states such as
			// no-speech, interrupted, listening, and errors must preserve AUTO.
			return lifecycle == "disabled" || (lifecycle == "ready" && separator >= 0);
		}

		public static string AutoButtonText(bool requestPending, bool companionAvailable, bool autoActEnabled)
		{
			if (!companionAvailable)
				return "AUTO: STARTING…";

			if (requestPending)
				return "AUTO: …";

			return autoActEnabled ? "AUTO: ON" : "AUTO: OFF";
		}
	}
}
