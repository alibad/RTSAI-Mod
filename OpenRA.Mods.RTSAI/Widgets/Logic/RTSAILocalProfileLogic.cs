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
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	/// <summary>
	/// Loads the RTS AI main menu's compact forum-profile line (RTSAI_LOCAL_PROFILE_PANEL in
	/// chrome/rtsai-mainmenu.yaml) instead of the stock LOCAL_PROFILE_PANEL box. The panel keeps the stock widget ids,
	/// so the stock LocalProfileLogic drives it unchanged; it hides while another window is open, as the stock one does.
	/// </summary>
	public class RTSAILocalProfileLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public RTSAILocalProfileLogic(Widget widget, World world)
		{
			Func<bool> minimalProfile = () => Ui.CurrentWindow() != null;
			Game.LoadWidget(world, "RTSAI_LOCAL_PROFILE_PANEL", widget, new WidgetArgs()
			{
				{ "minimalProfile", minimalProfile }
			});
		}
	}
}
