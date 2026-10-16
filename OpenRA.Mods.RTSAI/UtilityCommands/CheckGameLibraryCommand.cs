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
			Console.WriteLine("Game library checks passed: three identities; independent saved setups; dependency closure; safe extraction boundaries.");
		}
	}
}
