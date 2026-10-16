using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.UtilityCommands
{
	public sealed class CheckUnitModificationsCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--check-unit-modifications";
		bool IUtilityCommand.ValidateArguments(string[] args) => args.Length == 1;
		[Desc("Check saved unit modifications against the actual merged engine rules.")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			var mod = utility.ModData;
			Game.ModData = mod;
			using var source = mod.DefaultFileSystem.Open("ra2|unit-overrides/manifest.json");
			using var doc = JsonDocument.Parse(source);
			using var bindings = mod.DefaultFileSystem.Open("ra2|unit-overrides/bindings.json");
			using var registry = JsonDocument.Parse(bindings);
			var target = doc.RootElement.GetProperty("targets").EnumerateObject()
				.Single(p => p.Value.GetProperty("mod").GetString() == mod.Manifest.Id).Name;
			var results = new List<object>();
			foreach (var unit in doc.RootElement.GetProperty("units").EnumerateObject())
			{
				var entry = registry.RootElement.GetProperty("units").GetProperty(unit.Name).GetProperty("bindings");
				if (!entry.TryGetProperty(target, out var binding))
					continue;
				var actor = binding.GetProperty("actor").GetString().ToLowerInvariant();
				var info = mod.DefaultRules.Actors[actor];
				foreach (var field in unit.Value.EnumerateObject())
				{
					var actual = field.Name switch
					{
						"cost" => info.TraitInfo<ValuedInfo>().Cost,
						"health" => info.TraitInfo<HealthInfo>().HP,
						"speed" => info.TraitInfoOrDefault<MobileInfo>()?.Speed ?? info.TraitInfo<AircraftInfo>().Speed,
						_ => throw new InvalidDataException("Unsupported unit field")
					};
					if (actual != field.Value.GetInt32())
						throw new InvalidDataException($"{target} {actor} {field.Name}: {actual} != {field.Value}");
					results.Add(new { actor, field = field.Name, value = actual });
				}
			}
			Console.WriteLine(JsonSerializer.Serialize(new { passed = true, target,
				revision = doc.RootElement.GetProperty("revision").GetString(), fields = results }, new JsonSerializerOptions { WriteIndented = true }));
		}
	}
}
