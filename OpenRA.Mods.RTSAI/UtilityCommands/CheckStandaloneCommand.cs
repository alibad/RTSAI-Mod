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

		[Desc("[--strict]", "Fail if the standalone mod can load any Red Alert 2 file (see docs/standalone.md).")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			var strict = args.Contains("--strict");
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
					if (c.Value.NodeWithKeyOrDefault(key) is MiniYamlNode n && !fs.Exists(n.Value.Value))
						Error($"Chrome {c.Key}.{key}: {n.Value.Value} not found");

			if (manifest.LoadScreen != null)
				foreach (var n in manifest.LoadScreen.Nodes.Where(n => n.Key.StartsWith("Image", StringComparison.Ordinal)))
					if (!fs.Exists(n.Value.Value))
						Error($"LoadScreen.{n.Key}: {n.Value.Value} not found");

			// 6. Audio: warnings until the audio deliveries land.
			var rules = modData.DefaultRules;
			var factions = rules.Actors[SystemActors.World].TraitInfos<FactionInfo>().Where(f => f.Selectable && f.RandomFactionMembers.Count == 0)
				.Select(f => f.InternalName).ToList();
			var missingAudio = new SortedSet<string>();
			foreach (var (sets, voices) in new[] { (rules.Voices, true), (rules.Notifications, false) })
				foreach (var info in sets.Values)
					foreach (var (def, clips) in voices ? info.Voices : info.Notifications)
						foreach (var faction in factions)
						{
							var prefix = info.Prefixes.TryGetValue(faction, out var p) && !info.DisablePrefixes.Contains(def) ? p[0] : info.DefaultPrefix;
							var suffix = info.Variants.TryGetValue(faction, out var vv) && !info.DisableVariants.Contains(def) ? vv[0] : info.DefaultVariant;
							foreach (var clip in clips)
								if (!fs.Exists(prefix + clip + suffix))
									missingAudio.Add(prefix + clip + suffix);
						}

			foreach (var w in rules.Weapons.Values.Where(w => !w.Report.IsDefaultOrEmpty))
				foreach (var r in w.Report.Where(r => !fs.Exists(r)))
					missingAudio.Add(r);

			var missingMusic = rules.Music.Values.Count(m => !fs.Exists(m.Filename));
			if (missingAudio.Count > 0)
				Soft($"{missingAudio.Count} voice, notification or weapon sound files are missing (silent in game), e.g. {string.Join(", ", missingAudio.Take(6))}");
			if (missingMusic > 0)
				Soft($"{missingMusic} music tracks are missing");

			// 7. Placeholder debt: code-drawn stand-ins named after EA files (Phase 3 replaces them).
			var placeholders = fs.MountedPackages.FirstOrDefault(p => p.Name.Replace('\\', '/').EndsWith("standalone/placeholders", StringComparison.Ordinal));
			if (placeholders != null && placeholders.Contents.Any())
			{
				var count = placeholders.Contents.Count(c => c.Contains('.'));
				var shadowed = placeholders.Contents.Count(c => fs.TryGetPackageContaining(c, out var owner, out _) && owner != placeholders);
				Soft($"{count} placeholder files still stand in for EA files ({shadowed} already overridden by deliveries)");
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
