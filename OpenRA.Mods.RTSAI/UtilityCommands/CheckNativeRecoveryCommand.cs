using System;
using System.Linq;
using System.Text.Json;
using OpenRA.Mods.Common.Experience;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.UtilityCommands
{
	public sealed class CheckNativeRecoveryCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--check-native-recovery";
		bool IUtilityCommand.ValidateArguments(string[] args) => args.Length == 1;
		[Desc("Inspect actual loaded mode rules, selectable factions and restored module activation.")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			var mod = utility.ModData;
			Game.ModData = mod;
			var catalog = mod.GetOrNull<ExperienceCatalog>();
			var actors = mod.DefaultRules.Actors;
			var factions = actors[SystemActors.World].TraitInfos<FactionInfo>().Where(f => f.Selectable).Select(f => f.InternalName).ToArray();
			if (catalog == null)
				throw new InvalidOperationException("Recovered mode has no ExperienceCatalog.");
			var selected = catalog.ActiveComponentIds;
			if (mod.Manifest.Id == "rtsai-classic-core" && catalog.ActiveProfile.Id == "world-war-iii" && !factions.Contains("china"))
				throw new InvalidOperationException("Classic modern faction selection is not loaded into the real ruleset.");
			if (mod.Manifest.Id == "rtsai" && catalog.ActiveProfile.Id == "ra2-classic" && factions.Contains("china"))
				throw new InvalidOperationException("Disabled RA2 modern faction leaked into lobby selection.");
			var typed = actors[SystemActors.Player].TraitInfos<TraitInfo>().Select(i => i.GetType().Name).ToArray();
			Console.WriteLine(JsonSerializer.Serialize(new
			{
				mod = mod.Manifest.Id,
				profile = catalog.ActiveProfile.Id,
				modules = selected,
				factions,
				playerTraits = typed,
				actors = actors.Count,
				ruleFiles = mod.Rules,
				weapons = mod.DefaultRules.Weapons.Count,
				fingerprint = mod.GameplayFingerprint,
			}, new JsonSerializerOptions { WriteIndented = true }));
		}
	}
}
