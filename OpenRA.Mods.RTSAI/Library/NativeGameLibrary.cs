using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace OpenRA.Mods.RTSAI.Library
{
	public sealed record LibraryGame(string Id, string Name, string Subtitle, string Art);

	public static class NativeGameLibrary
	{
		public static readonly LibraryGame[] Games =
		[
			new("rtsai-classic-core", "Classic", "The original, with your additions.", "classic"),
			new("rtsai-ra2", "RA2", "The isometric game, expanded.", "ra2"),
			new("rtsai", "RTS", "New ideas. A separate playground.", "rts")
		];
		public const string Hub = "rtsai-library";
		public static string Root => Environment.GetEnvironmentVariable("RTSAI_LIBRARY_SUPPORT") ?? Platform.SupportDir;
		public static string GameDirectory(string id) => Path.Combine(Root, "Games", id);
		public static string Name(string id) => Games.FirstOrDefault(g => g.Id == id)?.Name ?? "Library";

		public static void Prepare(string id)
		{
			var target = GameDirectory(id);
			Directory.CreateDirectory(target);
			var settings = Path.Combine(target, "settings.yaml");
			if (!File.Exists(settings))
			{
				var previous = Path.Combine(Root, "settings.yaml");
				if (File.Exists(previous))
					File.Copy(previous, settings);
				File.WriteAllText(Path.Combine(target, "migration.json"), JsonSerializer.Serialize(new
				{
					source = previous, game = id, createdUtc = DateTime.UtcNow, originalPreserved = true
				}));
			}
			// Classic alone uses the already installed freeware content. Copy it once;
			// all other games and their support directories remain independent.
			var content = Path.Combine(Root, "Content");
			if (id == "rtsai-classic-core" && Directory.Exists(content) && !Directory.Exists(Path.Combine(target, "Content")))
				CopyDirectory(content, Path.Combine(target, "Content"));
		}

		static void CopyDirectory(string source, string destination)
		{
			Directory.CreateDirectory(destination);
			foreach (var file in Directory.EnumerateFiles(source))
				File.Copy(file, Path.Combine(destination, Path.GetFileName(file)), false);
			foreach (var directory in Directory.EnumerateDirectories(source))
			{
				if ((File.GetAttributes(directory) & FileAttributes.ReparsePoint) != 0)
					throw new IOException("A linked content folder needs to be resolved before migration.");
				CopyDirectory(directory, Path.Combine(destination, Path.GetFileName(directory)));
			}
		}

		public static void Open(string id, string screen = null, bool exitCurrent = true, string importPack = null)
		{
			if (id != Hub && !Games.Any(g => g.Id == id))
				throw new ArgumentException("Unknown game.", nameof(id));
			Prepare(id);
			Game.Settings.Save();
			var info = new ProcessStartInfo(Path.Combine(Platform.EngineDir, "bin", "OpenRA.exe"))
			{
				UseShellExecute = false, WorkingDirectory = Platform.EngineDir, CreateNoWindow = true
			};
			foreach (var arg in new[] { "Game.Mod=" + id, "Engine.EngineDir=" + Platform.EngineDir,
				"Engine.ModSearchPaths=" + Path.Combine(Platform.EngineDir, "mods"),
				"Engine.SupportDir=" + GameDirectory(id), "Game.FetchNews=false" })
				info.ArgumentList.Add(arg);
			info.Environment["RTSAI_LIBRARY_SUPPORT"] = Root;
			info.Environment.Remove("OPENRA_UTILITY_EXPERIENCE_PROFILE");
			info.Environment.Remove("RTSAI_RECOVERY_SCREEN");
			info.Environment["RTSAI_LIBRARY_SCREEN"] = screen ?? "";
			if (importPack != null) info.Environment["RTSAI_PENDING_ADDON"] = Path.GetFullPath(importPack);
			_ = Process.Start(info) ?? throw new IOException("The game process could not be started.");
			if (exitCurrent)
				Game.Exit();
		}
	}
}
