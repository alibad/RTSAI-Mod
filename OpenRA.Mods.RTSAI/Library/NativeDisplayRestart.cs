using System;
using System.IO;
using System.Text.Json;
using OpenRA.Primitives;

namespace OpenRA.Mods.RTSAI.Library
{
	public sealed record DisplaySnapshot(WindowMode Mode, int WindowWidth, int WindowHeight, int FullWidth, int FullHeight,
		int Display, float Scale, GLProfile Profile)
	{
		public static DisplaySnapshot Capture(GraphicSettings settings) => new(settings.Mode, settings.WindowedSize.X,
			settings.WindowedSize.Y, settings.FullscreenSize.X, settings.FullscreenSize.Y, settings.VideoDisplay, settings.UIScale, settings.GLProfile);
		public void Restore(GraphicSettings settings)
		{
			settings.Mode = Mode; settings.WindowedSize = new int2(WindowWidth, WindowHeight);
			settings.FullscreenSize = new int2(FullWidth, FullHeight); settings.VideoDisplay = Display;
			settings.UIScale = Scale; settings.GLProfile = Profile;
		}
	}
	public static class NativeDisplayRestart
	{
		static string PendingFile => Path.Combine(Platform.SupportDir, "pending-display.json");
		public static bool HasPending => File.Exists(PendingFile);
		public static void Apply(GraphicSettings previous)
		{
			File.WriteAllText(PendingFile, JsonSerializer.Serialize(DisplaySnapshot.Capture(previous)));
			Game.Settings.Save();
			NativeGameLibrary.Open(Game.ModData.Manifest.Id, "display-confirm");
		}
		public static void Keep()
		{
			if (File.Exists(PendingFile)) File.Delete(PendingFile);
			Game.Settings.Save();
		}
		public static void Revert()
		{
			if (!HasPending) return;
			var previous = JsonSerializer.Deserialize<DisplaySnapshot>(File.ReadAllText(PendingFile));
			previous?.Restore(Game.Settings.Graphics);
			File.Delete(PendingFile);
			Game.Settings.Save();
			NativeGameLibrary.Open(Game.ModData.Manifest.Id);
		}
	}
}
