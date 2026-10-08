using System;
using OpenRA.Widgets;
using OpenRA.Mods.Common.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	public sealed class RTSAIGameModesLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public RTSAIGameModesLogic(Widget widget, World world)
		{
			var button = widget.Get<ButtonWidget>("GAME_MODES_BUTTON");
			button.GetText = () => Game.ModData.Manifest.Id == "rtsai-topdown" ? "Game mode: Classic" : "Game mode: Isometric";
			button.OnClick = () => Ui.OpenWindow("RTSAI_GAME_MODES", new WidgetArgs { { "world", world } });
			// Local acceptance harness: exercise the real dialog and reload, once per process.
			var target = Environment.GetEnvironmentVariable("RTSAI_VERIFY_MODE_SWITCH");
			if (target == "rtsai" || target == "rtsai-topdown")
			{
				Environment.SetEnvironmentVariable("RTSAI_VERIFY_MODE_SWITCH", null);
				Game.RunAfterTick(() =>
				{
					button.OnClick();
					Ui.CurrentWindow().Get<ButtonWidget>(target == "rtsai" ? "ISOMETRIC_MODE" : "CLASSIC_MODE").OnClick();
				});
			}
		}
	}

	public sealed class RTSAIGameModeDialogLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public RTSAIGameModeDialogLogic(Widget widget)
		{
			widget.Get<ButtonWidget>("CLASSIC_MODE").OnClick = () => Switch("rtsai-topdown");
			widget.Get<ButtonWidget>("ISOMETRIC_MODE").OnClick = () => Switch("rtsai");
			widget.Get<ButtonWidget>("CANCEL").OnClick = Ui.CloseWindow;
		}

		static void Switch(string mode)
		{
			Ui.CloseWindow();
			if (mode == Game.ModData.Manifest.Id)
				return;
			Game.RunAfterTick(() => Game.InitializeMod(Game.Mods[mode], new Arguments()));
		}
	}
}
