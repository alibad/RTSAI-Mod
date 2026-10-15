using System;
using OpenRA.Mods.Common.Experience;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	public sealed class RTSAIDesktopEntryLogic : ChromeLogic
	{
		static bool entered;

		[ObjectCreator.UseCtor]
		public RTSAIDesktopEntryLogic(Widget widget, World world)
		{
			var open = widget.GetOrNull<ButtonWidget>("DESKTOP_HOME_BUTTON");
			if (open != null)
				open.OnClick = () => Game.OpenWindow("RTSAI_DESKTOP_HOME", new WidgetArgs());
			if (!entered && string.IsNullOrEmpty(Environment.GetEnvironmentVariable("RTSAI_VERIFY_MODE_SWITCH")))
			{
				entered = true;
				Game.RunAfterTick(() => Game.OpenWindow("RTSAI_DESKTOP_HOME", new WidgetArgs()));
			}
			Console.WriteLine("RTSAI_NATIVE_MODE|" + Game.ModData.Manifest.Id);
		}
	}

	public sealed class RTSAIDesktopHomeLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public RTSAIDesktopHomeLogic(Widget widget, World world)
		{
			widget.Get<ButtonWidget>("CLASSIC").OnClick = () => Select("rtsai-classic-core");
			widget.Get<ButtonWidget>("RA2").OnClick = () => Select("rtsai");
			widget.Get<ButtonWidget>("CONTINUE").OnClick = Ui.CloseWindow;
			widget.Get<ButtonWidget>("SETTINGS").OnClick = () => Game.OpenWindow("SETTINGS_PANEL",
				new WidgetArgs { { "onExit", (Action)(() => { }) } });
			widget.Get<ButtonWidget>("EXPANSIONS").OnClick = () =>
			{
				if (Game.ModData.GetOrNull<ExperienceCatalog>() != null)
					Game.OpenWindow("EXPERIENCE_COMPOSER_PANEL", new WidgetArgs { { "onExit", (Action)(() => { }) } });
				else
					Game.OpenWindow("RTSAI_PACK_LIBRARY", new WidgetArgs());
			};
			widget.Get<ButtonWidget>("PACKS").OnClick = () => Game.OpenWindow("RTSAI_PACK_LIBRARY", new WidgetArgs());
			var studio = widget.Get<ButtonWidget>("STUDIO");
			studio.IsVisible = () => Game.ModData.Manifest.Id == "rtsai-classic-core";
			studio.OnClick = () =>
			{
				Ui.CloseWindow();
				Ui.Root.Get<ButtonWidget>("EARTH_STUDIO_BUTTON").OnClick();
			};
			widget.Get<ButtonWidget>("QUIT").OnClick = Game.Exit;
			widget.Get<LabelWidget>("CURRENT").GetText = () => "Current experience: " +
				(Game.ModData.Manifest.Id == "rtsai-classic-core" ? "Classic" : Game.ModData.Manifest.Id == "rtsai" ? "RA2" : "Standalone top-down");
			Console.WriteLine("RTSAI_NATIVE_SCREEN|home|" + Game.ModData.Manifest.Id);
			var screen = Environment.GetEnvironmentVariable("RTSAI_RECOVERY_SCREEN");
			if (screen == "switch-classic" || screen == "switch-ra2")
			{
				Environment.SetEnvironmentVariable("RTSAI_RECOVERY_SCREEN", null);
				Game.RunAfterTick(() => widget.Get<ButtonWidget>(screen == "switch-classic" ? "CLASSIC" : "RA2").OnClick());
			}
			else if (screen == "studio")
				Game.RunAfterTick(studio.OnClick);
			else if (screen == "settings" || screen == "display" || screen == "packs" || screen == "composer" || screen == "composer-popup")
				Game.RunAfterTick(() =>
				{
					widget.Get<ButtonWidget>(screen == "settings" || screen == "display" ? "SETTINGS" : screen == "packs" ? "PACKS" : "EXPANSIONS").OnClick();
					if (screen == "display")
						Ui.CurrentWindow().Get<ButtonWidget>("DISPLAY_PANEL").OnClick();
					if (screen == "composer-popup")
						Ui.CurrentWindow().Get<ButtonWidget>("PROFILE_DROPDOWN").OnClick();
					Console.WriteLine("RTSAI_NATIVE_SCREEN|" + screen);
				});
		}

		static void Select(string mod)
		{
			Ui.CloseWindow();
			if (Game.ModData.Manifest.Id != mod)
				Game.RunAfterTick(() => Game.InitializeMod(Game.Mods[mod], new Arguments()));
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
