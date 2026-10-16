using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.UtilityCommands
{
	public sealed class CheckSharedContentCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--check-shared-content";
		bool IUtilityCommand.ValidateArguments(string[] args) => args.Length == 1;
		[Desc("Verify the shared content revision against this mod's actual merged engine rules.")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			var mod = utility.ModData;
			Game.ModData = mod;
			using var stream = mod.DefaultFileSystem.Open("ra2|shared-content/manifest.json");
			using var doc = JsonDocument.Parse(stream);
			var targets = doc.RootElement.GetProperty("targets").EnumerateObject()
				.Where(p => p.Value.GetProperty("mod").GetString() == mod.Manifest.Id).ToArray();
			if (targets.Length != 1)
				throw new InvalidDataException("No unique shared content target for " + mod.Manifest.Id);
			var target = targets[0];
			var actor = target.Value.GetProperty("actor").GetString().ToLowerInvariant();
			var expected = target.Value.GetProperty("cost").GetInt32();
			var actual = mod.DefaultRules.Actors[actor].TraitInfo<ValuedInfo>().Cost;
			using var rules = mod.DefaultFileSystem.Open(target.Value.GetProperty("rules").GetString());
			var sha = Convert.ToHexString(SHA256.HashData(rules)).ToLowerInvariant();
			if (actual != expected || sha != target.Value.GetProperty("rulesSha256").GetString())
				throw new InvalidDataException($"Shared content drift: {actor} costs {actual}, expected {expected}; overlay {sha}");
			Console.WriteLine(JsonSerializer.Serialize(new
			{
				passed = true, target = target.Name, mod = mod.Manifest.Id, actor,
				cost = actual, revision = doc.RootElement.GetProperty("revision").GetString(), rulesSha256 = sha,
			}, new JsonSerializerOptions { WriteIndented = true }));
		}
	}
}
