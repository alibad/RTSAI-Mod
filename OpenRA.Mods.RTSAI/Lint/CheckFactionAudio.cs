#region Copyright & License Information
/*
 * Copyright (c) The OpenRA Developers and Contributors
 * This file is part of OpenRA, which is free software. It is made
 * available to you under the terms of the GNU General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version. For more
 * information, see COPYING.
 */
#endregion

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using OpenRA.GameRules;
using OpenRA.Mods.Common.Lint;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Lint
{
	/// <summary>
	/// Every sound the mod ships itself (an explicit `package|path` clip or prefix) must exist and decode,
	/// and every playable faction needs an entry in each voice or notification set that is keyed by faction,
	/// otherwise the engine silently looks up an unprefixed file that does not exist.
	/// </summary>
	sealed class CheckFactionAudio : ILintRulesPass
	{
		// The pass runs for the mod rules and again for every map; decode each file once per mod load.
		static ModData decodedFor;
		static readonly Dictionary<string, string> DecodeFailures = [];

		void ILintRulesPass.Run(Action<string> emitError, Action<string> emitWarning, ModData modData, Ruleset rules)
		{
			var factions = rules.Actors[SystemActors.World].TraitInfos<FactionInfo>()
				.Where(f => f.Selectable && f.RandomFactionMembers.Count == 0)
				.Select(f => f.InternalName)
				.ToList();

			if (decodedFor != modData)
			{
				decodedFor = modData;
				DecodeFailures.Clear();
			}

			var reported = new HashSet<string>();
			void Check(string filename, string context)
			{
				if (!DecodeFailures.TryGetValue(filename, out var reason))
				{
					reason = Decodes(modData, filename, out var failure) ? null : failure;
					DecodeFailures[filename] = reason;
				}

				if (reason != null && reported.Add(filename))
					emitError($"{context}: `{filename}` {reason}.");
			}

			foreach (var (set, info) in rules.Voices)
			{
				CheckFactionKeys(emitError, factions, "Voices", set, info);
				foreach (var (definition, clips) in info.Voices)
					foreach (var clip in clips.Where(c => c.Contains('|')))
						Check(info.DefaultPrefix + clip + info.DefaultVariant, $"Voice `{set}.{definition}`");
			}

			foreach (var (type, info) in rules.Notifications)
			{
				CheckFactionKeys(emitError, factions, "Notifications", type, info);
				foreach (var (faction, prefixes) in info.Prefixes)
				{
					foreach (var prefix in prefixes.Where(p => p.Contains('|')))
					{
						foreach (var (definition, clips) in info.Notifications)
						{
							if (info.DisablePrefixes.Contains(definition))
								continue;

							var suffix = info.Variants.TryGetValue(faction, out var variants) && !info.DisableVariants.Contains(definition)
								? variants[0] : info.DefaultVariant;
							foreach (var clip in clips.Where(c => !string.IsNullOrEmpty(c)))
								Check(prefix + clip + suffix, $"Notification `{type}.{definition}` for faction `{faction}`");
						}
					}
				}
			}
		}

		static void CheckFactionKeys(Action<string> emitError, List<string> factions, string kind, string set, SoundInfo info)
		{
			foreach (var (name, keyed) in new[] { ("Prefixes", info.Prefixes), ("Variants", info.Variants) })
			{
				if (keyed.Count == 0)
					continue;

				foreach (var faction in factions.Where(f => !keyed.ContainsKey(f)))
					emitError($"{kind} `{set}` defines faction {name} but none for playable faction `{faction}`.");
			}
		}

		static bool Decodes(ModData modData, string filename, out string reason)
		{
			if (!modData.DefaultFileSystem.TryOpen(filename, out var stream))
			{
				reason = "does not exist";
				return false;
			}

			using (stream)
			{
				foreach (var loader in modData.SoundLoaders)
				{
					stream.Position = 0;
					if (!loader.TryParseSound(stream, out var format))
						continue;

					try
					{
						using (var pcm = format.GetPCMInputStream())
						{
							var buffer = new byte[16384];
							long total = 0;
							int read;
							while ((read = pcm.Read(buffer, 0, buffer.Length)) > 0)
								total += read;

							if (total == 0)
							{
								reason = "decodes to no audio";
								return false;
							}
						}
					}
					catch (Exception e) when (e is IOException or InvalidDataException or NotSupportedException or IndexOutOfRangeException)
					{
						reason = $"fails to decode ({e.Message})";
						return false;
					}

					reason = null;
					return true;
				}
			}

			reason = "is not in a supported sound format";
			return false;
		}
	}
}
