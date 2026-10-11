using System;
using System.Linq;
using System.Runtime.InteropServices;
using OpenRA.Mods.RTSAI.Companion;
using System.Text.Json;
using OpenRA.Mods.RTSAI.Traits;

namespace OpenRA.Mods.RTSAI.UtilityCommands
{
	sealed class CheckVoiceLanguageCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--check-voice-language";
		bool IUtilityCommand.ValidateArguments(string[] args) => true;
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			Game.ModData = utility.ModData;
			var rules = utility.ModData.DefaultRules;
			using var stream = utility.ModData.DefaultFileSystem.Open("ra2|standalone/audio/voice-language-contract.json");
			using var contract = JsonDocument.Parse(stream);
			var families = 0;
			var events = 0;
			foreach (var family in contract.RootElement.GetProperty("voiceSets").EnumerateObject())
			{
				var original = family.Name.ToLowerInvariant();
				var source = rules.Voices[original];
				foreach (var language in new[] { "faction", "en", "invalid" })
				{
					var selected = RTSAIVoiced.Resolve(family.Name, rules, language);
					if (selected != original + "__" + (language == "en" ? "en" : "faction"))
						throw new InvalidOperationException("Invalid voice selection: " + selected);
					var actual = rules.Voices[selected];
					foreach (var evt in family.Value.GetProperty("events").EnumerateObject())
					{
						var key = language == "en" ? "english" : "faction";
						var expected = evt.Value.GetProperty(key).EnumerateArray().Select(x => x.GetString()).ToArray();
						if (!actual.Voices[evt.Name].SequenceEqual(expected))
							throw new InvalidOperationException($"Wrong pool {selected}/{evt.Name}");
					}
					foreach (var evt in source.Voices)
						if (!family.Value.GetProperty("events").TryGetProperty(evt.Key, out _) && !actual.Voices[evt.Key].SequenceEqual(evt.Value))
							throw new InvalidOperationException($"Inherited event changed: {selected}/{evt.Key}");
				}
				families++;
				events += family.Value.GetProperty("events").EnumerateObject().Count();
			}
			foreach (var voice in rules.Voices.Keys.Where(x => !x.Contains("__") && !rules.Voices.ContainsKey(x + "__faction")))
				if (RTSAIVoiced.Resolve(voice, rules, "en") != voice)
					throw new InvalidOperationException("Unfiltered animal/shared family changed: " + voice);
			if (RTSAISettings.Normalize(null) != "faction" || RTSAISettings.Normalize("EN") != "faction")
				throw new InvalidOperationException("Invalid setting fallback");
			if (CompanionHost.ArchitectureSupported("arm64", Architecture.X64) || !CompanionHost.ArchitectureSupported("arm64", Architecture.Arm64))
				throw new InvalidOperationException("Companion architecture gate");
			Console.WriteLine($"VOICE LANGUAGE PASS: {families} same-family sets, {events} events; English/faction/invalid pools and inherited events verified.");
		}
	}
}
