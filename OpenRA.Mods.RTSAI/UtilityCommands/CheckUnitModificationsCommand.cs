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
		bool IUtilityCommand.ValidateArguments(string[] args) => args.Length == 1 || args.Length == 2 && args[1] == "all";
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
				.First(p => p.Value.GetProperty("mod").GetString() == mod.Manifest.Id).Name;
			var results = new List<object>();
			if (args.Length == 2)
			{
				using var pilotStream = mod.DefaultFileSystem.Open("ra2|shared-content/manifest.json");
				using var pilot = JsonDocument.Parse(pilotStream);
				var pilotTarget = pilot.RootElement.GetProperty("targets").GetProperty(target);
				foreach (var unit in registry.RootElement.GetProperty("units").EnumerateObject())
				{
					if (!unit.Value.GetProperty("bindings").TryGetProperty(target, out var binding)) continue;
					var actor = binding.GetProperty("actor").GetString().ToLowerInvariant();
					var info = mod.DefaultRules.Actors[actor];
					var overrides = doc.RootElement.GetProperty("units");
					overrides.TryGetProperty(unit.Name, out var values);
					foreach (var field in binding.GetProperty("baseline").EnumerateObject())
					{
						if (field.Value.ValueKind == JsonValueKind.Null) continue;
						var expected = field.Value.GetInt32();
						if (binding.TryGetProperty("inheritance", out var inheritance) && inheritance.TryGetProperty(field.Name, out var ancestors))
							foreach (var ancestor in ancestors.EnumerateArray())
								if (overrides.TryGetProperty(unit.Value.GetProperty("mode").GetString() + ":" + ancestor.GetString(), out var parent)
									&& parent.TryGetProperty(field.Name, out var inherited))
								{ expected = inherited.GetInt32(); break; }
						if (field.Name == "cost" && actor == pilotTarget.GetProperty("actor").GetString().ToLowerInvariant()) expected = pilotTarget.GetProperty("cost").GetInt32();
						if (values.ValueKind == JsonValueKind.Object && values.TryGetProperty(field.Name, out var value)) expected = value.GetInt32();
						var actual = field.Name switch
						{
							"cost" => info.TraitInfo<ValuedInfo>().Cost,
							"health" => info.TraitInfo<HealthInfo>().HP,
							"speed" => info.TraitInfoOrDefault<MobileInfo>()?.Speed ?? info.TraitInfo<AircraftInfo>().Speed,
							_ => throw new InvalidDataException("Unsupported stat")
						};
						if (actual != expected) throw new InvalidDataException($"{target} {actor} {field.Name}: {actual} != {expected}");
						results.Add(new { actor, field = field.Name, value = actual });
					}
				}
			}
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
					if (args.Length == 1) results.Add(new { actor, field = field.Name, value = actual });
				}
			}
			var unitDetails = new List<object>();
			if (doc.RootElement.TryGetProperty("details", out var detailed))
				foreach (var unit in detailed.EnumerateObject())
				{
					if (!registry.RootElement.GetProperty("units").GetProperty(unit.Name).GetProperty("bindings").TryGetProperty(target, out var binding)) continue;
					var actor = binding.GetProperty("actor").GetString().ToLowerInvariant();
					var info = mod.DefaultRules.Actors[actor];
					unitDetails.Add(new { unit = unit.Name, actor,
						armor = info.TraitInfos<ArmorInfo>().FirstOrDefault()?.Type,
						buildDuration = info.TraitInfoOrDefault<BuildableInfo>()?.BuildDuration,
						sight = info.TraitInfos<RevealsShroudInfo>().FirstOrDefault(t => t.InstanceName == null)?.Range.Length,
						weapons = info.TraitInfos<ArmamentInfo>().Select(arm =>
						{
							var w = mod.DefaultRules.Weapons[arm.Weapon.ToLowerInvariant()];
							return new { name = arm.Weapon, range = w.Range.Length, reload = w.ReloadDelay, burst = w.Burst,
								damage = w.Warheads.OfType<OpenRA.Mods.Common.Warheads.DamageWarhead>().Sum(d => d.Damage) };
						}).ToArray() });
				}
			Console.WriteLine(JsonSerializer.Serialize(new { passed = true, target,
				revision = doc.RootElement.GetProperty("revision").GetString(), fields = results, unitDetails }, new JsonSerializerOptions { WriteIndented = true }));
		}
	}
}
