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
using System.Reflection;
using System.Text.RegularExpressions;
using OpenRA.FileSystem;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Terrain;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Traits.Render;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.UtilityCommands
{
	/// <summary>
	/// The standalone guarantee, run by `make test`: the game must not be able to load anything from Red Alert 2.
	/// No content installer, no archive formats, only mod and engine folders mounted, no archive files in the mod,
	/// every sprite/tile/model/palette/cursor/chrome/font reference resolvable, and no "Red Alert" branding.
	/// Missing audio and placeholder stand-ins are reported as warnings until the Phase 3 deliveries land
	/// (pass --strict to make them errors too). See docs/standalone.md.
	/// </summary>
	sealed class CheckStandaloneCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--check-standalone";

		bool IUtilityCommand.ValidateArguments(string[] args) { return true; }

		static readonly string[] ArchiveExtensions = [".mix", ".bag", ".idx", ".big", ".vqa", ".cab", ".hdr"];

		// Actor references that name an actor some other actor must own, rather than bring one into the game.
		static readonly HashSet<string> NonSpawningReferences =
		[
			"RepairableInfo", "RepairableNearInfo", "RearmableInfo", "TransformsIntoRepairableInfo",
			"GrantConditionOnProductionInfo", "ProductionCostMultiplierInfo", "ProductionTimeMultiplierInfo",
			"AutoTargetPriorityInfo",
		];

		static bool IsA(object o, string typeName)
		{
			for (var t = o.GetType(); t != null; t = t.BaseType)
				if (t.Name == typeName)
					return true;
			return false;
		}

		static IEnumerable<string> Strings(object v)
		{
			if (v == null)
				yield break;
			if (v is string s)
			{
				yield return s;
				yield break;
			}

			if (v.GetType().GetProperty("IsDefault")?.GetValue(v) is true)
				yield break;
			if (v is System.Collections.IDictionary d)
			{
				foreach (System.Collections.DictionaryEntry e in d)
				{
					foreach (var x in Strings(e.Key))
						yield return x;
					foreach (var x in Strings(e.Value))
						yield return x;
				}

				yield break;
			}

			if (v is System.Collections.IEnumerable en)
				foreach (var x in en)
					foreach (var y in Strings(x))
						yield return y;
		}

		static FieldInfo FindField(Type t, string name)
		{
			for (; t != null; t = t.BaseType)
			{
				var f = t.GetField(name, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly);
				if (f != null)
					return f;
			}

			return null;
		}

		/// <summary>Actors a faction can field in a skirmish: starting units, everything buildable from what it owns
		/// (prerequisites, production queues), and actors those bring into the game (transforms, free actors,
		/// spawns, cargo, support powers, survivors after SurvivorReplacements).</summary>
		static HashSet<string> Reachable(Ruleset rules, string faction)
		{
			var world = rules.Actors[SystemActors.World];
			var player = rules.Actors[SystemActors.Player];
			bool FactionOk(object t)
			{
				var list = Strings(t.GetType().GetField("Factions")?.GetValue(t)).ToList();
				return list.Count == 0 || list.Contains(faction);
			}

			var provided = new HashSet<string>();
			var queues = new HashSet<string>();
			var survivors = new Dictionary<string, string>();
			foreach (var t in player.TraitInfos<TraitInfo>())
			{
				if (IsA(t, "ProvidesPrerequisiteInfo") && FactionOk(t))
					provided.Add((string)t.GetType().GetField("Prerequisite").GetValue(t) ?? "player");
				if (IsA(t, "ProvidesTechPrerequisiteInfo"))
					provided.UnionWith(Strings(t.GetType().GetField("Prerequisites").GetValue(t)));
				if (IsA(t, "ProductionQueueInfo") && FactionOk(t))
					queues.Add((string)t.GetType().GetField("Type").GetValue(t));
				if (IsA(t, "SurvivorReplacementsInfo") && FactionOk(t))
					foreach (System.Collections.DictionaryEntry e in (System.Collections.IDictionary)t.GetType().GetField("Replacements").GetValue(t))
						survivors[(string)e.Key] = (string)e.Value;
			}

			var reach = new HashSet<string>();
			void Add(string a)
			{
				a = a?.ToLowerInvariant();
				if (a != null && rules.Actors.ContainsKey(a))
					reach.Add(a);
			}

			foreach (var su in world.TraitInfos<TraitInfo>().Where(t => IsA(t, "StartingUnitsInfo") && FactionOk(t)))
			{
				Add((string)su.GetType().GetField("BaseActor").GetValue(su));
				foreach (var s in Strings(su.GetType().GetField("SupportActors").GetValue(su)))
					Add(s);
			}

			var produced = new HashSet<string>();
			var before = -1;
			while (before != reach.Count + provided.Count + produced.Count)
			{
				before = reach.Count + provided.Count + produced.Count;
				foreach (var a in reach.ToList())
					foreach (var t in rules.Actors[a].TraitInfos<TraitInfo>())
					{
						if (IsA(t, "ProvidesPrerequisiteInfo") && FactionOk(t))
							provided.Add((string)t.GetType().GetField("Prerequisite").GetValue(t) ?? a);
						if (IsA(t, "ProductionInfo"))
							produced.UnionWith(Strings(t.GetType().GetField("Produces").GetValue(t)));
						if (IsA(t, "ProductionQueueInfo") && FactionOk(t))
							queues.Add((string)t.GetType().GetField("Type").GetValue(t));
						if (NonSpawningReferences.Contains(t.GetType().Name) || !FactionOk(t))
							continue;
						foreach (var field in t.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
							if (field.GetCustomAttribute<ActorReferenceAttribute>() != null)
								foreach (var s in Strings(field.GetValue(t)))
									Add(t.GetType().Name == "SpawnSurvivorsInfo" && survivors.TryGetValue(s, out var r) ? r : s);
					}

				foreach (var (name, actor) in rules.Actors)
				{
					if (reach.Contains(name) || name.StartsWith('^'))
						continue;
					var b = actor.TraitInfos<TraitInfo>().FirstOrDefault(t => IsA(t, "BuildableInfo"));
					if (b == null || !Strings(b.GetType().GetField("Queue").GetValue(b)).Any(q => queues.Contains(q) && produced.Contains(q)))
						continue;
					var ok = true;
					foreach (var p in Strings(b.GetType().GetField("Prerequisites").GetValue(b)))
					{
						var tok = p.TrimStart('~');
						ok &= tok.StartsWith('!') ? !provided.Contains(tok[1..]) : provided.Contains(tok);
					}

					if (ok)
						reach.Add(name);
				}
			}

			return reach;
		}

		[Desc("[--strict] [--strict-audio] [--list-placeholders]", "Fail if the standalone mod can load any Red Alert 2 file (see docs/standalone.md).")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			var strict = args.Contains("--strict");
			var strictAudio = strict || args.Contains("--strict-audio");
			var listPlaceholders = args.Contains("--list-placeholders");
			var modData = Game.ModData = utility.ModData;
			var manifest = modData.Manifest;
			var fs = modData.ModFiles;
			var errors = new List<string>();
			var warnings = new List<string>();
			void Error(string e) => errors.Add(e);
			void Soft(string w) { if (strict) errors.Add(w); else warnings.Add(w); }

			var modDir = Path.GetFullPath(manifest.Package.Name).TrimEnd('\\', '/');
			var modsRoot = Path.GetDirectoryName(modDir);
			var engineDir = Path.GetFullPath(Platform.EngineDir).TrimEnd('\\', '/');

			// 1. Manifest: plain file system, no content, no archive formats.
			if (manifest.FileSystem.Value != "DefaultFileSystem")
				Error($"FileSystem is `{manifest.FileSystem.Value}`; the standalone game must use DefaultFileSystem (no content installer).");
			foreach (var n in manifest.FileSystem.Nodes.SelectMany(n => n.Value.Nodes.Prepend(n)))
				if (n.Key.Contains("^SupportDir", StringComparison.Ordinal) || n.Key.Contains("Content", StringComparison.OrdinalIgnoreCase))
					Error($"FileSystem mounts `{n.Key}`: player content must not be mounted.");
			if (manifest.PackageFormats.Length > 0)
				Error($"PackageFormats lists {string.Join(", ", manifest.PackageFormats)}: no archive format may be registered.");

			// 2. Mounted packages: folders inside this mod set or the engine only.
			foreach (var p in fs.MountedPackages)
			{
				if (p is not Folder)
				{
					Error($"Mounted package `{p.Name}` is a {p.GetType().Name}, not a folder.");
					continue;
				}

				var path = Path.GetFullPath(p.Name).TrimEnd('\\', '/');
				var inMods = path.StartsWith(modsRoot, StringComparison.OrdinalIgnoreCase);
				var inEngine = path.StartsWith(engineDir, StringComparison.OrdinalIgnoreCase) && !path.Contains("Support", StringComparison.OrdinalIgnoreCase);
				if (!inMods && !inEngine)
					Error($"Mounted folder `{p.Name}` is outside the mods and engine directories.");
			}

			// 3. No archive or video file anywhere in the mod.
			foreach (var f in Directory.EnumerateFiles(modDir, "*", SearchOption.AllDirectories))
				if (ArchiveExtensions.Contains(Path.GetExtension(f).ToLowerInvariant()))
					Error($"Archive file shipped in the mod: {Path.GetRelativePath(modDir, f)}");

			// 4. Every visual reference resolves (sprites for every tileset, terrain tiles).
			foreach (var (tileset, terrainInfo) in modData.DefaultTerrainInfo)
			{
				if (terrainInfo is ITemplatedTerrainInfo templated)
					foreach (var ttr in modData.DefaultRules.Actors[SystemActors.World].TraitInfos<ITiledTerrainRendererInfo>())
						ttr.ValidateTileSprites(templated, e => Error($"{tileset} terrain: {e}"));

				using var sequences = new SequenceSet(modData.DefaultFileSystem, modData, tileset, null);
				sequences.SpriteCache.LoadReservations(modData);
				foreach (var (filename, location) in sequences.SpriteCache.MissingFiles)
					Error($"{tileset}: {location}: sprite {filename} not found");
			}

			// 5. Models, palettes and other Filename fields, cursors, chrome, fonts, load screen.
			foreach (var node in MiniYaml.Load(fs, manifest.ModelSequences, null).Where(n => !n.Key.StartsWith('^')))
				foreach (var s in node.Value.Nodes)
				{
					var parts = (s.Value.Value ?? node.Key).Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
					var vxl = parts.Length > 0 ? parts[0] : node.Key;
					var hva = parts.Length > 1 ? parts[1] : vxl;
					foreach (var f in new[] { vxl + ".vxl", hva + ".hva" })
						if (!fs.Exists(f))
							Error($"Model {node.Key}.{s.Key}: {f} not found");
				}

			foreach (var actor in modData.DefaultRules.Actors.Values)
				foreach (var ti in actor.TraitInfos<TraitInfo>())
					foreach (var field in ti.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
						if (field.FieldType == typeof(string) && field.Name.EndsWith("Filename", StringComparison.Ordinal)
							&& field.GetValue(ti) is string v && v.Length > 0 && !fs.Exists(v))
							Error($"{actor.Name}.{ti.GetType().Name}.{field.Name}: {v} not found");

			foreach (var top in MiniYaml.Load(fs, manifest.Cursors, null).Where(n => n.Key == "Cursors"))
				foreach (var n in top.Value.Nodes)
					if (!fs.Exists(n.Key))
						Error($"Cursor sheet {n.Key} not found");

			foreach (var c in MiniYaml.Load(fs, manifest.Chrome, null))
				foreach (var key in new[] { "Image", "Image2x", "Image3x" })
				{
					if (c.Value.NodeWithKeyOrDefault(key) is not MiniYamlNode n)
						continue;

					if (!fs.Exists(n.Value.Value))
					{
						Error($"Chrome {c.Key}.{key}: {n.Value.Value} not found");
						continue;
					}

					// A chrome sheet becomes one texture, and the renderer refuses non-power-of-two sizes at first draw.
					using var s = fs.Open(n.Value.Value);
					var header = new byte[24];
					if (s.Read(header, 0, 24) == 24 && header[1] == 'P' && header[2] == 'N' && header[3] == 'G')
					{
						var w = (header[16] << 24) | (header[17] << 16) | (header[18] << 8) | header[19];
						var h = (header[20] << 24) | (header[21] << 16) | (header[22] << 8) | header[23];
						if (!Exts.IsPowerOf2(w) || !Exts.IsPowerOf2(h))
							Error($"Chrome {c.Key}.{key}: {n.Value.Value} is {w}x{h}; chrome sheets must be power-of-two sized");
					}
				}

			if (manifest.LoadScreen != null)
				foreach (var n in manifest.LoadScreen.Nodes.Where(n => n.Key.StartsWith("Image", StringComparison.Ordinal)))
					if (!fs.Exists(n.Value.Value))
						Error($"LoadScreen.{n.Key}: {n.Value.Value} not found");

			// 6. Audio, for what the game's factions can actually field: their reachable actors' voices, those actors'
			// weapons, and the faction notifications. Rules for actors nobody can reach (kept for the classic add-on)
			// do not count. Warnings unless --strict.
			var rules = modData.DefaultRules;
			var factions = rules.Actors[SystemActors.World].TraitInfos<FactionInfo>().Where(f => f.Selectable && f.RandomFactionMembers.Count == 0)
				.Select(f => f.InternalName).ToList();
			var reach = factions.ToDictionary(f => f, f => Reachable(rules, f));
			var missingAudio = new SortedSet<string>();
			void CheckSound(string name)
			{
				if (!string.IsNullOrEmpty(name) && !fs.Exists(name))
					missingAudio.Add(name);
			}

			foreach (var faction in factions)
			{
				var voiceSets = new HashSet<string>();
				var weapons = new HashSet<string>();
				foreach (var a in reach[faction])
					foreach (var ti in rules.Actors[a].TraitInfos<TraitInfo>())
						foreach (var field in ti.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
						{
							if (field.Name == "VoiceSet" && field.GetValue(ti) is string vs && vs.Length > 0)
								voiceSets.Add(vs.ToLowerInvariant());
							if (field.GetCustomAttribute<WeaponReferenceAttribute>() != null)
								foreach (var w in Strings(field.GetValue(ti)))
									weapons.Add(w.ToLowerInvariant());
						}

				var sets = rules.Voices.Where(kv => voiceSets.Contains(kv.Key)).Select(kv => (kv.Value, true))
					.Concat(rules.Notifications.Select(kv => (kv.Value, false)));
				foreach (var (info, voices) in sets)
					foreach (var (def, clips) in voices ? info.Voices : info.Notifications)
					{
						var prefix = info.Prefixes.TryGetValue(faction, out var p) && !info.DisablePrefixes.Contains(def) ? p[0] : info.DefaultPrefix;
						var suffix = info.Variants.TryGetValue(faction, out var vv) && !info.DisableVariants.Contains(def) ? vv[0] : info.DefaultVariant;
						foreach (var clip in clips)
							CheckSound(prefix + clip + suffix);
					}

				foreach (var wn in weapons)
					if (rules.Weapons.TryGetValue(wn, out var w))
						foreach (var o in new object[] { w }.Concat(w.Warheads))
							foreach (var field in o.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
								if (field.Name.Contains("Report", StringComparison.Ordinal) || field.Name.Contains("Sound", StringComparison.Ordinal))
									foreach (var s in Strings(field.GetValue(o)))
										CheckSound(s);
			}

			var missingMusic = rules.Music.Values.Count(m => !fs.Exists(m.Filename));
			if (missingAudio.Count > 0)
				(strictAudio ? (Action<string>)Error : Soft)($"{missingAudio.Count} voice, notification or weapon sound files are missing (silent in game), e.g. {string.Join(", ", missingAudio.Take(6))}");
			if (missingMusic > 0)
				(strictAudio ? (Action<string>)Error : Soft)($"{missingMusic} music tracks are missing");

			// 7. Placeholder debt: code-drawn stand-ins named after EA files, counted for what the factions can field
			// (their reachable actors' images and their weapons' projectile and effect images). Phase 3 replaces them.
			var placeholders = fs.MountedPackages.FirstOrDefault(p => p.Name.Replace('\\', '/').EndsWith("standalone/placeholders", StringComparison.Ordinal));
			if (placeholders != null && placeholders.Contents.Any())
			{
				var images = new HashSet<string>();
				foreach (var a in reach.Values.SelectMany(r => r).Distinct())
					foreach (var ti in rules.Actors[a].TraitInfos<TraitInfo>())
					{
						foreach (var field in ti.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
						{
							if (field.Name.EndsWith("Image", StringComparison.Ordinal) || field.Name.EndsWith("Images", StringComparison.Ordinal))
								foreach (var s in Strings(field.GetValue(ti)))
									images.Add(s);
							if (field.GetCustomAttribute<WeaponReferenceAttribute>() != null)
								foreach (var wn in Strings(field.GetValue(ti)))
									if (rules.Weapons.TryGetValue(wn.ToLowerInvariant(), out var w))
										foreach (var o in new object[] { w.Projectile }.Concat(w.Warheads).Where(o => o != null))
											foreach (var wf in o.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
												if (wf.Name.EndsWith("Image", StringComparison.Ordinal))
													foreach (var s in Strings(wf.GetValue(o)))
														images.Add(s);
						}

						if (ti is RenderSpritesInfo rs && rs.Image == null)
							images.Add(a);
					}

				var used = new Dictionary<string, SortedSet<string>>();
				foreach (var tileset in modData.DefaultTerrainInfo.Keys)
				{
					using var seqs = new SequenceSet(modData.DefaultFileSystem, modData, tileset, null);
					var byFile = (Dictionary<string, List<int>>)typeof(SpriteCache)
						.GetField("reservationsByFilename", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(seqs.SpriteCache);
					var tokenFile = byFile.SelectMany(kv => kv.Value.Select(t => (t, kv.Key))).ToDictionary(x => x.t, x => x.Key);
					foreach (var image in seqs.Images.Where(images.Contains))
						foreach (var seqName in seqs.Sequences(image))
						{
							var seq = seqs.GetSequence(image, seqName);
							var toLoad = FindField(seq.GetType(), "spritesToLoad")?.GetValue(seq) as System.Collections.IEnumerable;
							if (toLoad == null)
								continue;
							foreach (var res in toLoad)
								if (tokenFile.TryGetValue((int)res.GetType().GetField("Token").GetValue(res), out var f)
									&& fs.TryGetPackageContaining(f, out var owner, out _) && owner == placeholders)
								{
									if (!used.TryGetValue(f, out var users))
										used[f] = users = [];
									users.Add(image);
								}
						}
				}

				Soft($"{used.Count} placeholder files still stand in for EA art the factions use, e.g. {string.Join(", ", used.Keys.Order().Take(6))} " +
					$"({placeholders.Contents.Count(c => c.Contains('.'))} placeholder files in the pack; --list-placeholders lists them all)");

				if (listPlaceholders)
					foreach (var (file, users) in used.OrderBy(kv => kv.Key, StringComparer.Ordinal))
						Console.WriteLine($"placeholder {file}: {string.Join(", ", users)}");
			}

			// 8. Identity: no Red Alert branding in shipped text; ModTabTitle follows the product term.
			string productName = null;
			foreach (var file in manifest.FluentMessages)
			{
				using var s = fs.Open(file);
				var lines = s.ReadAllText().Split('\n');
				for (var i = 0; i < lines.Length; i++)
				{
					var line = lines[i].Trim();
					if (line.StartsWith('#'))
						continue;
					var m = Regex.Match(line, @"^-product-name\s*=\s*(.+)$");
					if (m.Success)
						productName = m.Groups[1].Value.Trim();
					var eq = line.IndexOf('=');
					var value = eq >= 0 ? line[(eq + 1)..] : line;
					if (Regex.IsMatch(value, @"red alert|\bRA2\b|westwood|command\s*&\s*conquer", RegexOptions.IgnoreCase))
						Error($"{file}:{i + 1}: branding in shipped text: {line}");
				}
			}

			var credits = modData.GetOrCreate<ModCredits>();
			if (productName == null)
				Error("No `-product-name` Fluent term (languages/identity.ftl).");
			else if (credits != null && credits.ModTabTitle != productName)
				Error($"ModCredits.ModTabTitle `{credits.ModTabTitle}` differs from -product-name `{productName}`.");

			// 9. The classic add-on (if installed) must still list every shared file of this manifest.
			if (utility.Mods.TryGetValue(manifest.Id + "-classic", out var classic))
			{
				var lists = new (string Name, IEnumerable<string> Mine, IEnumerable<string> Theirs)[]
				{
					("Rules", manifest.Rules, classic.Rules), ("Sequences", manifest.Sequences, classic.Sequences),
					("ModelSequences", manifest.ModelSequences, classic.ModelSequences), ("Weapons", manifest.Weapons, classic.Weapons),
					("Voices", manifest.Voices, classic.Voices), ("Notifications", manifest.Notifications, classic.Notifications),
					("Chrome", manifest.Chrome, classic.Chrome), ("ChromeLayout", manifest.ChromeLayout, classic.ChromeLayout),
					("FluentMessages", manifest.FluentMessages, classic.FluentMessages),
				};
				foreach (var (name, mine, theirs) in lists)
					foreach (var f in mine.Where(f => !f.StartsWith("ra2|standalone/", StringComparison.Ordinal) && !theirs.Contains(f)))
						Error($"mods/{classic.Id}/mod.yaml {name} lacks {f}: run python tools/build-classic-manifest.py");
			}

			foreach (var w in warnings)
				Console.WriteLine($"Warning: {w}");
			foreach (var e in errors)
				Console.WriteLine($"Error: {e}");

			Console.WriteLine(errors.Count == 0
				? $"Standalone check passed ({warnings.Count} warnings)."
				: $"Standalone check FAILED: {errors.Count} errors, {warnings.Count} warnings.");
			if (errors.Count > 0)
				Environment.Exit(1);
		}
	}
}
