using System;
using OpenRA.Mods.Common.Experience;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Common.Widgets.Logic;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	// Adapt the established menu state machine rather than duplicating lobby,
	// mission, save-game or connection logic. All existing actions remain owned
	// by MainMenuLogic, including their exit and match-start callbacks.
	public sealed class RTSAIFrontlineMainMenuLogic : MainMenuLogic
	{
		public static void PrepareModeChange() => lastGameState = MenuPanel.None;

		[ObjectCreator.UseCtor]
		public RTSAIFrontlineMainMenuLogic(Widget widget, World world, ModData modData)
			: base(widget, world, modData)
		{
			widget.Get("MAIN_MENU").IsVisible = () => false;
			widget.Get("SINGLEPLAYER_MENU").IsVisible = () => false;
			var home = Game.LoadWidget(world, "RTSAI_DESKTOP_HOME", widget, new WidgetArgs { { "mainMenu", widget } });
			home.IsVisible = () => menuType == MenuType.Main || menuType == MenuType.Singleplayer;
			Console.WriteLine("RTSAI_NATIVE_MODE|" + modData.Manifest.Id);
		}
	}

	public sealed class RTSAIDesktopHomeLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public RTSAIDesktopHomeLogic(Widget widget, World world, Widget mainMenu)
		{
			var classic = widget.Get<ButtonWidget>("CLASSIC");
			var ra2 = widget.Get<ButtonWidget>("RA2");
			classic.OnClick = () => Select("rtsai-classic-core");
			ra2.OnClick = () => Select("rtsai");
			classic.IsHighlighted = () => Game.ModData.Manifest.Id == "rtsai-classic-core";
			ra2.IsHighlighted = () => Game.ModData.Manifest.Id == "rtsai";

			void Singleplayer(string action)
			{
				mainMenu.Get<ButtonWidget>("SINGLEPLAYER_BUTTON").OnClick();
				mainMenu.Get<ButtonWidget>(action).OnClick();
			}
			var skirmish = mainMenu.Get<ButtonWidget>("SKIRMISH_BUTTON");
			var missions = mainMenu.Get<ButtonWidget>("MISSIONS_BUTTON");
			widget.Get<ButtonWidget>("CONTINUE").IsDisabled = skirmish.IsDisabled;
			widget.Get<ButtonWidget>("SKIRMISH").IsDisabled = skirmish.IsDisabled;
			widget.Get<ButtonWidget>("CAMPAIGN").IsDisabled = missions.IsDisabled;
			widget.Get<ButtonWidget>("CONTINUE").OnClick = () => Singleplayer("SKIRMISH_BUTTON");
			widget.Get<ButtonWidget>("SKIRMISH").OnClick = () => Singleplayer("SKIRMISH_BUTTON");
			widget.Get<ButtonWidget>("CAMPAIGN").OnClick = () => Singleplayer("MISSIONS_BUTTON");
			widget.Get<ButtonWidget>("MULTIPLAYER").OnClick = mainMenu.Get<ButtonWidget>("MULTIPLAYER_BUTTON").OnClick;
			widget.Get<ButtonWidget>("SETTINGS").OnClick = mainMenu.Get<ButtonWidget>("SETTINGS_BUTTON").OnClick;
			widget.Get<ButtonWidget>("TOOLS").OnClick = mainMenu.Get<ButtonWidget>("EXTRAS_BUTTON").OnClick;
			widget.Get<ButtonWidget>("EXPANSIONS").OnClick = () =>
			{
				if (Game.ModData.GetOrNull<ExperienceCatalog>() != null)
					Game.OpenWindow("EXPERIENCE_COMPOSER_PANEL", new WidgetArgs { { "onExit", (Action)(() => { }) } });
			};
			widget.Get<ButtonWidget>("PACKS").OnClick = () => Game.OpenWindow("RTSAI_PACK_LIBRARY", new WidgetArgs());
			widget.Get<ButtonWidget>("QUIT").OnClick = Game.Exit;

			var tools = mainMenu.Get("EXTRAS_MENU");
			var studio = tools.Get<ButtonWidget>("STUDIO_TOOLS");
			studio.IsVisible = () => Game.ModData.Manifest.Id == "rtsai-classic-core";
			studio.OnClick = mainMenu.Get<ButtonWidget>("EARTH_STUDIO_BUTTON").OnClick;
			tools.Get<ButtonWidget>("SAVED_GAMES_TOOLS").OnClick = () => Singleplayer("LOAD_BUTTON");
			tools.Get<ButtonWidget>("SAVED_GAMES_TOOLS").IsDisabled = mainMenu.Get<ButtonWidget>("LOAD_BUTTON").IsDisabled;

			Console.WriteLine("RTSAI_NATIVE_SCREEN|home|" + Game.ModData.Manifest.Id);
			var screen = Environment.GetEnvironmentVariable("RTSAI_RECOVERY_SCREEN");
			if (screen == "switch-classic" || screen == "switch-ra2")
			{
				Environment.SetEnvironmentVariable("RTSAI_RECOVERY_SCREEN", null);
				Game.RunAfterTick(() => widget.Get<ButtonWidget>(screen == "switch-classic" ? "CLASSIC" : "RA2").OnClick());
			}
			else if (screen == "settings-return" || screen == "campaign-return" || screen == "packs-return")
				Game.RunAfterTick(() =>
				{
					widget.Get<ButtonWidget>(screen == "settings-return" ? "SETTINGS" : screen == "campaign-return" ? "CAMPAIGN" : "PACKS").OnClick();
					Ui.CurrentWindow().Get<ButtonWidget>(screen == "packs-return" ? "CLOSE" : "BACK_BUTTON").OnClick();
					if (!widget.IsVisible())
						throw new InvalidOperationException("Frontline home was not restored after " + screen);
					Console.WriteLine("RTSAI_NATIVE_RETURN|" + screen + "|" + Game.ModData.Manifest.Id);
				});
			else if (screen == "studio")
				Game.RunAfterTick(studio.OnClick);
			else if (screen == "settings" || screen == "display" || screen == "packs" || screen == "composer" || screen == "composer-popup"
				|| screen == "campaign" || screen == "skirmish" || screen == "play" || screen == "multiplayer" || screen == "tools")
				Game.RunAfterTick(() =>
				{
					var id = screen switch
					{
						"settings" or "display" => "SETTINGS",
						"packs" => "PACKS",
						"composer" or "composer-popup" => "EXPANSIONS",
						"campaign" => "CAMPAIGN",
						"skirmish" => "SKIRMISH",
						"multiplayer" => "MULTIPLAYER",
						"tools" => "TOOLS",
						_ => "CONTINUE"
					};
					widget.Get<ButtonWidget>(id).OnClick();
					if (screen == "display")
						Ui.CurrentWindow().Get<ButtonWidget>("DISPLAY_PANEL").OnClick();
					if (screen == "composer-popup")
						Ui.CurrentWindow().Get<ButtonWidget>("PROFILE_DROPDOWN").OnClick();
					Console.WriteLine("RTSAI_NATIVE_SCREEN|" + screen);
				});
		}

		static void Select(string mod)
		{
			if (Game.ModData.Manifest.Id != mod)
			{
				// Returning from a previous match must not reopen its lobby in
				// the newly selected foundation when the shellmap loads.
				RTSAIFrontlineMainMenuLogic.PrepareModeChange();
				Game.RunAfterTick(() => Game.InitializeMod(Game.Mods[mod], new Arguments()));
			}
		}
	}

	public sealed class RTSAIPackLibraryLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public RTSAIPackLibraryLogic(Widget widget, World world)
		{
			widget.Get<ButtonWidget>("CLOSE").OnClick = Ui.CloseWindow;
			widget.Get<ButtonWidget>("COMPOSER").IsDisabled = () => Game.ModData.GetOrNull<ExperienceCatalog>() == null;
			widget.Get<ButtonWidget>("COMPOSER").OnClick = () => Game.OpenWindow("EXPERIENCE_COMPOSER_PANEL",
				new WidgetArgs { { "onExit", (Action)(() => { }) } });
		}
	}
}
