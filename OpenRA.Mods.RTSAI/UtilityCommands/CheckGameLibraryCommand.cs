using System;
using System.IO;
using System.Linq;
using OpenRA.Mods.Common.Experience;
using OpenRA.Mods.RTSAI.Library;
using OpenRA.Mods.RTSAI.Widgets.Logic;

namespace OpenRA.Mods.RTSAI.UtilityCommands
{
	public sealed class CheckGameLibraryCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--check-game-library";
		bool IUtilityCommand.ValidateArguments(string[] args) => args.Length == 1;
		[Desc("Verify game identities, settings isolation, customization dependencies and installer path boundaries.")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			if (NativeGameLibrary.Games.Select(g => g.Id).Distinct().Count() != 3) throw new InvalidDataException("Game identities collide.");
			foreach (var game in NativeGameLibrary.Games)
				if (!utility.Mods.ContainsKey(game.Id)) throw new InvalidDataException("Game manifest missing: " + game.Id);
			foreach (var invalid in new[] { "../outside.exe", "nested/../../outside.exe", "C:/outside.exe", "\\\\server\\share\\outside.exe" })
			{
				try { CommunityInstall.SafeEntryPath(Path.GetTempPath(), invalid); throw new InvalidOperationException("Archive traversal accepted."); }
				catch (InvalidDataException) { }
			}
			CheckLaunchArguments();
			var temporary = Path.Combine(Path.GetTempPath(), "rtsai-library-test-" + Guid.NewGuid().ToString("N") + ".yaml");
			try
			{
				var settings = new Settings(temporary, Arguments.Empty);
				foreach (var game in NativeGameLibrary.Games)
				{
					settings.GetOrCreate<ExperienceSettings>(null, game.Id).EnabledComponents = game.Id;
					settings.GetOrCreate<RTSAICustomSetup>(null, game.Id).Components = "saved-" + game.Id;
				}
				settings.Save();
				var reloaded = new Settings(temporary, Arguments.Empty);
				foreach (var game in NativeGameLibrary.Games)
					if (reloaded.GetOrCreate<ExperienceSettings>(null, game.Id).EnabledComponents != game.Id ||
						reloaded.GetOrCreate<RTSAICustomSetup>(null, game.Id).Components != "saved-" + game.Id)
						throw new InvalidDataException("A game setup leaked into another game.");
			}
			finally { if (File.Exists(temporary)) File.Delete(temporary); }
			// Shared engine sections are isolated by support file, not by mod key.
			var files = NativeGameLibrary.Games.Select((g, i) => temporary + "." + i).ToArray();
			try
			{
				for (var i = 0; i < files.Length; i++)
				{
					var own = new Settings(files[i], Arguments.Empty);
					own.Graphics.Mode = (WindowMode)i;
					own.Graphics.WindowedSize = new int2(1200 + i * 100, 720 + i * 10);
					own.Sound.SoundVolume = (i + 1) / 10f;
					own.Save();
				}
				for (var i = 0; i < files.Length; i++)
				{
					var own = new Settings(files[i], Arguments.Empty);
					if (own.Graphics.Mode != (WindowMode)i || own.Graphics.WindowedSize.X != 1200 + i * 100 ||
						Math.Abs(own.Sound.SoundVolume - (i + 1) / 10f) > .001)
						throw new InvalidDataException("Display/audio settings did not remain independent.");
				}
			}
			finally { foreach (var file in files) if (File.Exists(file)) File.Delete(file); }
			var catalog = utility.ModData.GetOrNull<ExperienceCatalog>();
			if (catalog != null)
			{
				foreach (var component in catalog.Components.Values.Where(c => c.IsSelectable))
				{
					var enabled = catalog.ToggleComponent([], component.Id, true);
					if (!enabled.Contains(component.Id) || component.Dependencies.Any(d => !enabled.Contains(d)))
						throw new InvalidDataException("Required additions missing for " + component.Id);
				}
			}
			Console.WriteLine("Game library checks passed: three identities; independent saved setups and display/audio files; dependency closure; safe extraction boundaries.");
		}

		static void CheckLaunchArguments()
		{
			var root = Path.Combine(Path.GetTempPath(), "rtsai launch test " + Guid.NewGuid().ToString("N"));
			var bin = Path.Combine(root, "RTS AI.app", "Contents", "MacOS");
			var engine = Path.Combine(root, "RTS AI.app", "Contents", "Resources");
			try
			{
				Directory.CreateDirectory(bin);
				foreach (var arch in new[] { "arm64", "x86_64" })
					foreach (var id in NativeGameLibrary.Games.Select(g => g.Id).Append(NativeGameLibrary.Hub))
					{
						var runtime = Path.Combine(bin, arch);
						var host = Path.Combine(bin, "apphost-" + arch);
						var info = NativeGameLibrary.CreateLaunchInfo(id, root, engine, runtime, host);
						var args = info.ArgumentList.ToArray();
						if (info.FileName != host || info.WorkingDirectory != engine || info.UseShellExecute || args.Length != 8 ||
							args[0] != Path.Combine(runtime, "libhostfxr.dylib") || args[1] != Path.Combine(runtime, "OpenRA.dll") ||
							args[2] != "Game.Mod=" + id || args[5] != "Engine.SupportDir=" + Path.Combine(root, "Games", id) ||
							args[7] != "Engine.LaunchPath=" + Path.Combine(bin, "Launcher") || info.Environment["RTSAI_LIBRARY_SUPPORT"] != root)
							throw new InvalidDataException("The Mac Library handoff lost its runtime, game identity or independent storage.");
					}
				var windows = NativeGameLibrary.CreateLaunchInfo("rtsai-ra2", root, engine, bin, Path.Combine(bin, "RTSAI.exe"));
				if (windows.ArgumentList.Count != 6 || windows.ArgumentList[0] != "Game.Mod=rtsai-ra2")
					throw new InvalidDataException("A packaged Windows game received Mac host arguments.");
				File.WriteAllText(Path.Combine(bin, "OpenRA.exe"), "");
				var development = NativeGameLibrary.CreateLaunchInfo("rtsai", root, engine, bin, "dotnet");
				if (development.FileName != Path.Combine(bin, "OpenRA.exe") || development.ArgumentList.Count != 5)
					throw new InvalidDataException("The development Library handoff changed.");
			}
			finally { if (Directory.Exists(root)) Directory.Delete(root, true); }
			Console.WriteLine("Game Library launch checks passed: both Mac architectures, all three games and return to Library; paths with spaces; Windows and development arguments.");
		}

	}
}
