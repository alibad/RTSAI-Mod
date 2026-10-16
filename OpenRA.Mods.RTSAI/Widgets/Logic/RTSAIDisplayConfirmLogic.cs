using System;
using OpenRA.Mods.RTSAI.Library;
using OpenRA.Mods.RTSAI.Widgets;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	public sealed class RTSAIDisplayConfirmLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public RTSAIDisplayConfirmLogic(LibrarySurfaceWidget widget, ModData modData)
		{
			var expires = DateTime.UtcNow.AddSeconds(20);
			var reverting = false;
			widget.Quiet = true;
			widget.RenderContent = () =>
			{
				widget.Text(230, 270, "Keep these display settings?", 64, display: true);
				widget.Text(230, 405, NativeGameLibrary.Name(modData.Manifest.Id) + " restarted using the selected display mode.", 32);
				widget.Text(230, 485, $"Reverting automatically in {Math.Max(0, (int)(expires - DateTime.UtcNow).TotalSeconds)} seconds.", 32, LibrarySurfaceWidget.Amber);
			};
			widget.Button(modData, "KEEP_DISPLAY", "Keep changes", 230, 630, 590, 90, () => { NativeDisplayRestart.Keep(); Ui.CloseWindow(); }, true);
			widget.Button(modData, "REVERT_DISPLAY", "Revert", 860, 630, 590, 90, NativeDisplayRestart.Revert);
			widget.OnBack = NativeDisplayRestart.Revert;
			widget.OnTick = () =>
			{
				if (!reverting && DateTime.UtcNow >= expires) { reverting = true; NativeDisplayRestart.Revert(); }
			};
		}
	}
}
