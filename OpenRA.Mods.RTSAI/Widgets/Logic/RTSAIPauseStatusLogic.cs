using OpenRA.Mods.Common.Widgets;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	public sealed class RTSAIPauseStatusLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public RTSAIPauseStatusLogic(ButtonWidget widget, World world)
		{
			// Keep pause visible instead of alternating it with the small sidebar clock.
			widget.IsVisible = () => world.Paused && !world.IsGameOver;
			widget.IsDisabled = () => !Game.IsHost && (world.LocalPlayer == null || world.LocalPlayer.WinState == WinState.Lost);
			widget.OnClick = () => world.SetPauseState(false);
		}
	}
}
