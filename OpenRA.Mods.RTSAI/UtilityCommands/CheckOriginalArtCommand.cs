using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using OpenRA.Graphics;
using OpenRA.Mods.Cnc.Traits.Render;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Traits.Render;
using OpenRA.Mods.RTSAI.Widgets;
using OpenRA.Mods.RTSAI.Rendering;

namespace OpenRA.Mods.RTSAI.UtilityCommands
{
	public sealed class CheckOriginalArtCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--check-original-art";
		bool IUtilityCommand.ValidateArguments(string[] args) => args.Length == 1;
		[Desc("Check loaded original-country image/model bindings and preserved modern faction images.")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			Game.ModData = utility.ModData;
			using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(Platform.EngineDir, "native-original-art.json")));
			var root = document.RootElement;
			if (!root.GetProperty("renderOnly").GetBoolean() || root.GetProperty("countries").GetArrayLength() != 9 ||
				root.GetProperty("modernFactionsPreserved").GetArrayLength() != 7)
				throw new InvalidDataException("Original-art scope is not nine original and seven modern factions.");
			var actors = utility.ModData.DefaultRules.Actors;
			OriginalSupportPowersWidget.CheckCompatibility();
			var powers = actors["player"].TraitInfoOrDefault<FactionSupportPowerIconsInfo>()
				?? throw new InvalidDataException("Original support-power icon mapping is absent.");
			foreach (var country in root.GetProperty("countries").EnumerateArray())
				if (!powers.Factions.Contains(country.GetString()))
					throw new InvalidDataException("Original support-power icon country is missing.");
			foreach (var country in root.GetProperty("modernFactionsPreserved").EnumerateArray())
				if (powers.Factions.Contains(country.GetString()))
					throw new InvalidDataException("Modern support-power icons would be replaced.");
			var sequences = new SequenceSet(utility.ModData.DefaultFileSystem, utility.ModData,
				utility.ModData.DefaultTerrainInfo.Keys.First(), null);
			foreach (var icon in new[] { "gps", "invuln", "chrono", "abomb", "paradrop", "airborne", "lightningstorm" })
				if (!sequences.HasSequence(powers.Image, icon))
					throw new InvalidDataException("Original support-power icon sequence missing: " + icon);
			var originalBindings = 0;
			var modernBindings = 0;
			foreach (var group in new[] { "expectedOriginalImages", "expectedModernImages" })
				foreach (var actor in root.GetProperty(group).EnumerateObject())
				{
					var info = actors[actor.Name];
					var sprites = info.TraitInfo<RenderSpritesInfo>();
					var declared = root.GetProperty(group == "expectedOriginalImages" ? "countries" : "modernFactionsPreserved");
					foreach (var country in declared.EnumerateArray())
						if (!actor.Value.TryGetProperty(country.GetString(), out _))
							throw new InvalidDataException(actor.Name + ": incomplete faction image gate.");
					foreach (var faction in actor.Value.EnumerateObject())
					{
						var expected = faction.Value.GetString().ToLowerInvariant();
						if (sprites.GetImage(info, faction.Name) != expected)
							throw new InvalidDataException($"{actor.Name}/{faction.Name}: image binding differs from approved native plan.");
						if (group == "expectedOriginalImages") originalBindings++; else modernBindings++;
					}
				}
			var voxelBindings = 0;
			foreach (var actor in root.GetProperty("expectedVoxelImages").EnumerateObject())
			{
				if (actors[actor.Name].TraitInfo<RenderVoxelsInfo>().Image != actor.Value.GetString())
					throw new InvalidDataException(actor.Name + ": original voxel binding is inactive.");
				voxelBindings++;
			}
			Console.WriteLine($"Native original art passed: {originalBindings} original-country image bindings, " +
				$"{modernBindings} unchanged modern image bindings, {voxelBindings} original voxel bindings.");
		}
	}
}
