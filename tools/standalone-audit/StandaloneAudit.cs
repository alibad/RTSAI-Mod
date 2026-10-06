#region Copyright & License Information
/*
 * Copyright (c) The RTS AI authors. GPL-3.0, like the rest of this mod.
 */
#endregion

// Standalone-dependency audit for the RTS AI mod (RA2 mode).
//
// An OpenRA utility command, compiled against the mod's engine by tools/standalone-audit.py and loaded through a
// disposable copy of mod.yaml. It asks the engine's own file system which mounted package provides every file the
// mod references (sprites per tileset, terrain tiles, voxel models, palettes, cursors, chrome, fonts, sounds, music),
// classifies each package as EA content, mod-shipped or engine-shipped, and works out which actors each modern
// faction can actually reach in a skirmish. It reads only names, frame counts and frame sizes from EA packages:
// no pixels or samples are written anywhere.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using OpenRA.FileSystem;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Terrain;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAIAudit
{
	public sealed class StandaloneAuditCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--standalone-audit";

		bool IUtilityCommand.ValidateArguments(string[] args) { return args.Length >= 2; }

		const BindingFlags Inst = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;

		ModData modData;
		OpenRA.FileSystem.FileSystem fs;
		string modDir, engineDir;
		readonly Dictionary<IReadOnlyPackage, string> packageClass = [];
		readonly Dictionary<string, object> resolveCache = [];

		[Desc("OUTPUT.json", "Resolve every asset reference to the package that provides it (EA content, mod or engine).")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			modData = Game.ModData = utility.ModData;
			fs = modData.ModFiles;
			modDir = Path.GetFullPath(modData.Manifest.Package.Name).TrimEnd('\\', '/');
			engineDir = Path.GetFullPath(Platform.EngineDir).TrimEnd('\\', '/');

			var report = new Dictionary<string, object>
			{
				["mod"] = modData.Manifest.Id,
				["modDir"] = modDir,
				["packages"] = Packages(),
			};

			report["sprites"] = Sprites();
			report["terrain"] = Terrain();
			report["models"] = Models();
			report["palettes"] = Palettes();
			report["cursors"] = Cursors();
			report["chrome"] = Chrome();
			report["fonts"] = Fonts();
			report["loadScreen"] = LoadScreen();
			report["audio"] = Audio();
			report["actors"] = Actors();
			report["reachable"] = Reachability();
			report["maps"] = Maps();

			File.WriteAllText(args[1], JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
			Console.WriteLine($"wrote {args[1]}");
		}

		// ---------------------------------------------------------------- packages and resolution
		string Classify(IReadOnlyPackage p)
		{
			if (packageClass.TryGetValue(p, out var c))
				return c;

			if (p is Folder)
			{
				var path = Path.GetFullPath(p.Name).TrimEnd('\\', '/');
				if (path.StartsWith(modDir, StringComparison.OrdinalIgnoreCase))
					c = "mod";
				else if (path.StartsWith(engineDir, StringComparison.OrdinalIgnoreCase) && !path.Contains("Support"))
					c = "engine";
				else
					c = "ea";
			}
			else
				c = "ea";   // the mod ships no .mix/.bag: every archive package is installed EA content

			return packageClass[p] = c;
		}

		List<object> Packages()
		{
			return fs.MountedPackages.Select(p => (object)new Dictionary<string, object>
			{
				["name"] = p.Name,
				["prefix"] = fs.GetPrefix(p),
				["type"] = p.GetType().Name,
				["class"] = Classify(p),
				["entries"] = p.Contents.Count(),
			}).ToList();
		}

		// Which package wins for this path, and is the file also available from a non-EA package?
		Dictionary<string, object> Resolve(string path)
		{
			if (string.IsNullOrEmpty(path))
				return null;

			if (resolveCache.TryGetValue(path, out var cached))
				return (Dictionary<string, object>)cached;

			var r = new Dictionary<string, object> { ["file"] = path };
			if (fs.Exists(path) && fs.TryGetPackageContaining(path, out var pkg, out var inner) && pkg.Contains(inner))
			{
				r["by"] = Classify(pkg);
				r["package"] = pkg.Name;
				if (Classify(pkg) == "ea")
				{
					var bare = path.Contains('|') ? path[(path.IndexOf('|') + 1)..] : path;
					var alt = fs.MountedPackages.FirstOrDefault(q => Classify(q) != "ea" && q.Contains(bare));
					if (alt != null)
						r["alsoIn"] = alt.Name;
				}
			}
			else
				r["by"] = "missing";

			resolveCache[path] = r;
			return r;
		}

		static string By(Dictionary<string, object> r) { return r == null ? "none" : (string)r["by"]; }

		// ---------------------------------------------------------------- sprites (every image, every tileset)
		Dictionary<string, object> Sprites()
		{
			var perTileset = new Dictionary<string, object>();
			var fileInfo = new Dictionary<string, Dictionary<string, object>>();
			var imageFiles = new Dictionary<string, SortedSet<string>>();

			foreach (var tileset in modData.DefaultTerrainInfo.Keys)
			{
				var seqs = new SequenceSet(modData.DefaultFileSystem, modData, tileset, null);
				var cache = seqs.SpriteCache;
				var byFile = (Dictionary<string, List<int>>)typeof(SpriteCache).GetField("reservationsByFilename", Inst).GetValue(cache);
				var tokenFile = new Dictionary<int, string>();
				foreach (var kv in byFile)
					foreach (var t in kv.Value)
						tokenFile[t] = kv.Key;

				var images = new Dictionary<string, object>();
				foreach (var image in seqs.Images)
				{
					var seqFiles = new Dictionary<string, List<string>>();
					foreach (var seqName in seqs.Sequences(image))
					{
						var seq = seqs.GetSequence(image, seqName);
						var files = new List<string>();
						var toLoad = FindField(seq.GetType(), "spritesToLoad")?.GetValue(seq) as IEnumerable;
						if (toLoad != null)
							foreach (var res in toLoad)
							{
								var token = (int)res.GetType().GetField("Token").GetValue(res);
								if (tokenFile.TryGetValue(token, out var f))
									files.Add(f);
							}

						var depth = FindField(seq.GetType(), "depthSpriteReservation")?.GetValue(seq) as int?;
						if (depth.HasValue && tokenFile.TryGetValue(depth.Value, out var df))
							files.Add(df);

						seqFiles[seqName] = files.Distinct().ToList();
						foreach (var f in files)
							imageFiles.GetOrAdd(image, _ => []).Add(f);
					}

					images[image] = seqFiles;
				}

				foreach (var f in byFile.Keys)
				{
					if (fileInfo.ContainsKey(f))
						continue;

					var r = new Dictionary<string, object>(Resolve(f));
					if (By(r) == "ea")
					{
						try
						{
							var frames = cache.LoadFramesUncached(f);
							if (frames != null)
							{
								r["frames"] = frames.Length;
								r["w"] = frames.Max(x => x.FrameSize.Width);
								r["h"] = frames.Max(x => x.FrameSize.Height);
							}
						}
						catch (Exception e)
						{
							r["frameError"] = e.GetType().Name;
						}
					}

					fileInfo[f] = r;
				}

				perTileset[tileset] = new Dictionary<string, object>
				{
					["images"] = images.Count,
					["files"] = byFile.Count,
					["imageSequences"] = images,
				};

				seqs.Dispose();
			}

			return new Dictionary<string, object>
			{
				["tilesets"] = perTileset,
				["files"] = fileInfo,
				["imageFiles"] = imageFiles.ToDictionary(kv => kv.Key, kv => kv.Value.ToList()),
				["imageSources"] = YamlKeySources(modData.Manifest.Sequences),
			};
		}

		static FieldInfo FindField(Type t, string name)
		{
			for (; t != null; t = t.BaseType)
			{
				var f = t.GetField(name, Inst | BindingFlags.DeclaredOnly);
				if (f != null)
					return f;
			}

			return null;
		}

		// top-level key -> every manifest file that defines or overrides it, in load order
		Dictionary<string, List<string>> YamlKeySources(IEnumerable<string> files)
		{
			var result = new Dictionary<string, List<string>>();
			foreach (var file in files)
			{
				using var s = fs.Open(file);
				foreach (var node in MiniYaml.FromStream(s, file))
					result.GetOrAdd(node.Key.TrimStart('-'), _ => []).Add(file);
			}

			return result;
		}

		// ---------------------------------------------------------------- terrain templates
		Dictionary<string, object> Terrain()
		{
			var result = new Dictionary<string, object>();
			foreach (var (tileset, info) in modData.DefaultTerrainInfo)
			{
				if (info is not DefaultTerrain dt)
					continue;

				var files = new Dictionary<string, object>();
				var templates = new Dictionary<string, object>();
				foreach (var (id, t) in dt.Templates)
				{
					var ti = (DefaultTerrainTemplateInfo)t;
					var imgs = ti.Images.Concat(ti.DepthImages.IsDefault ? [] : ti.DepthImages).ToList();
					foreach (var i in imgs)
						files[i] = Resolve(i);

					templates[id.ToString()] = new Dictionary<string, object>
					{
						["images"] = imgs,
						["size"] = new[] { t.Size.X, t.Size.Y },
						["tiles"] = t.TilesCount,
						["by"] = imgs.Select(i => By(Resolve(i))).Distinct().ToList(),
					};
				}

				result[tileset] = new Dictionary<string, object>
				{
					["palette"] = dt.Palette,
					["templates"] = templates,
					["files"] = files,
				};
			}

			return result;
		}

		// ---------------------------------------------------------------- voxel models
		Dictionary<string, object> Models()
		{
			var result = new Dictionary<string, object>();
			var nodes = MiniYaml.Load(fs, modData.Manifest.ModelSequences, null);
			foreach (var node in nodes)
			{
				if (node.Key.StartsWith('^'))
					continue;

				var seqs = new Dictionary<string, object>();
				foreach (var s in node.Value.Nodes)
				{
					var vxl = node.Key;
					var hva = node.Key;
					if (!string.IsNullOrEmpty(s.Value.Value))
					{
						var f = s.Value.Value.Split(',', StringSplitOptions.RemoveEmptyEntries);
						vxl = hva = f[0].Trim();
						if (f.Length > 1)
							hva = f[1].Trim();
					}

					seqs[s.Key] = new[] { Resolve(vxl + ".vxl"), Resolve(hva + ".hva") };
				}

				result[node.Key] = seqs;
			}

			return new Dictionary<string, object>
			{
				["images"] = result,
				["imageSources"] = YamlKeySources(modData.Manifest.ModelSequences),
			};
		}

		// ---------------------------------------------------------------- palettes and other Filename fields in rules
		List<object> Palettes()
		{
			var result = new List<object>();
			foreach (var actor in modData.DefaultRules.Actors.Values)
				foreach (var ti in actor.TraitInfos<TraitInfo>())
					foreach (var f in ti.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
					{
						if (f.FieldType != typeof(string) || !f.Name.EndsWith("Filename", StringComparison.Ordinal))
							continue;

						var v = (string)f.GetValue(ti);
						if (string.IsNullOrEmpty(v))
							continue;

						var name = ti.GetType().GetField("Name")?.GetValue(ti) as string;
						var tileset = ti.GetType().GetField("Tileset")?.GetValue(ti) as string;
						result.Add(new Dictionary<string, object>
						{
							["actor"] = actor.Name,
							["trait"] = ti.GetType().Name,
							["name"] = name,
							["tileset"] = tileset,
							["resolve"] = Resolve(v),
						});
					}

			return result;
		}

		// ---------------------------------------------------------------- cursors, chrome, load screen
		List<object> Cursors()
		{
			var result = new List<object>();
			foreach (var top in MiniYaml.Load(fs, modData.Manifest.Cursors, null))
				foreach (var n in top.Value.Nodes)
					result.Add(new Dictionary<string, object>
					{
						["section"] = top.Key,
						["resolve"] = Resolve(top.Key == "Cursors" ? n.Key : n.Value.Value),
						["sequences"] = top.Key == "Cursors" ? n.Value.Nodes.Length : 0,
					});

			return result;
		}

		List<object> Chrome()
		{
			var result = new List<object>();
			foreach (var c in MiniYaml.Load(fs, modData.Manifest.Chrome, null))
				foreach (var key in new[] { "Image", "Image2x", "Image3x" })
				{
					var n = c.Value.NodeWithKeyOrDefault(key);
					if (n != null)
						result.Add(new Dictionary<string, object> { ["collection"] = c.Key, ["key"] = key, ["resolve"] = Resolve(n.Value.Value) });
				}

			return result;
		}

		List<object> Fonts()
		{
			using var s = modData.Manifest.Package.GetStream("mod.yaml");
			var fonts = MiniYaml.FromStream(s, "mod.yaml").FirstOrDefault(n => n.Key == "Fonts");
			return fonts == null ? [] : fonts.Value.Nodes.Select(n => (object)Resolve(n.Value.NodeWithKeyOrDefault("Font")?.Value.Value)).ToList();
		}

		List<object> LoadScreen()
		{
			var ls = modData.Manifest.LoadScreen;
			return ls == null ? [] : ls.Nodes.Where(n => n.Key.StartsWith("Image", StringComparison.Ordinal))
				.Select(n => (object)Resolve(n.Value.Value)).ToList();
		}

		// ---------------------------------------------------------------- audio
		Dictionary<string, object> Audio()
		{
			var rules = modData.DefaultRules;
			var factions = rules.Actors[SystemActors.World].TraitInfos<TraitInfo>()
				.Where(t => t.GetType().Name == "FactionInfo")
				.Select(t => (string)t.GetType().GetField("InternalName").GetValue(t)).ToList();

			Dictionary<string, object> Sets(IReadOnlyDictionary<string, GameRules.SoundInfo> sets, bool voices)
			{
				var outSets = new Dictionary<string, object>();
				foreach (var (setName, info) in sets)
				{
					var defs = voices ? info.Voices : info.Notifications;
					var perVariant = new Dictionary<string, object>();
					foreach (var variant in new string[] { null }.Concat(factions))
					{
						var files = new List<object>();
						foreach (var (def, clips) in defs)
							foreach (var clip in clips)
							{
								var suffix = info.DefaultVariant;
								var prefix = info.DefaultPrefix;
								if (variant != null)
								{
									if (info.Variants.TryGetValue(variant, out var v) && !info.DisableVariants.Contains(def))
										suffix = v[0];
									if (info.Prefixes.TryGetValue(variant, out var p) && !info.DisablePrefixes.Contains(def))
										prefix = p[0];
								}

								files.Add(new Dictionary<string, object> { ["def"] = def, ["r"] = Resolve(prefix + clip + suffix) });
							}

						perVariant[variant ?? "_default"] = files;
					}

					outSets[setName] = perVariant;
				}

				return outSets;
			}

			var music = rules.Music.Select(m => (object)new Dictionary<string, object>
			{
				["key"] = m.Key, ["title"] = m.Value.Title, ["hidden"] = m.Value.Hidden, ["r"] = Resolve(m.Value.Filename),
			}).ToList();

			// Sound filenames written directly in rules and weapons (Report, ImpactSounds, *Sound*, ...)
			var ruleSounds = new Dictionary<string, object>();
			foreach (var actor in rules.Actors.Values)
				foreach (var ti in actor.TraitInfos<TraitInfo>())
					foreach (var s in SoundStrings(ti))
						ruleSounds[$"actor:{actor.Name}:{ti.GetType().Name}:{s}"] = Resolve(s);

			foreach (var (wname, w) in rules.Weapons)
			{
				foreach (var s in SoundStrings(w))
					ruleSounds[$"weapon:{wname}:{s}"] = Resolve(s);
				if (w.Projectile != null)
					foreach (var s in SoundStrings(w.Projectile))
						ruleSounds[$"weapon:{wname}:projectile:{s}"] = Resolve(s);
				foreach (var wh in w.Warheads)
					foreach (var s in SoundStrings(wh))
						ruleSounds[$"weapon:{wname}:{wh.GetType().Name}:{s}"] = Resolve(s);
			}

			return new Dictionary<string, object>
			{
				["factions"] = factions,
				["voices"] = Sets(rules.Voices, true),
				["notifications"] = Sets(rules.Notifications, false),
				["music"] = music,
				["ruleSounds"] = ruleSounds,
				["voiceSources"] = YamlKeySources(modData.Manifest.Voices),
				["notificationSources"] = YamlKeySources(modData.Manifest.Notifications),
			};
		}

		static IEnumerable<string> SoundStrings(object o)
		{
			foreach (var f in o.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
			{
				if (!(f.Name.Contains("Sound", StringComparison.Ordinal) || f.Name.Contains("Report", StringComparison.Ordinal)))
					continue;

				foreach (var s in Strings(f.GetValue(o)))
					if (s.EndsWith(".wav", StringComparison.OrdinalIgnoreCase) || s.EndsWith(".aud", StringComparison.OrdinalIgnoreCase))
						yield return s;
			}
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

			if (v is IDictionary d)
			{
				foreach (DictionaryEntry e in d)
				{
					foreach (var x in Strings(e.Key))
						yield return x;
					foreach (var x in Strings(e.Value))
						yield return x;
				}

				yield break;
			}

			if (v.GetType().GetProperty("IsDefault")?.GetValue(v) is true)
				yield break;

			if (v is IEnumerable en)
				foreach (var x in en)
					foreach (var y in Strings(x))
						yield return y;
		}

		// ---------------------------------------------------------------- actors: images, models, weapons, voices
		Dictionary<string, object> Actors()
		{
			var rules = modData.DefaultRules;
			var result = new Dictionary<string, object>();
			var ruleSources = YamlKeySources(modData.Manifest.Rules);
			foreach (var actor in rules.Actors.Values)
			{
				var images = new SortedSet<string>();
				var voiceSets = new SortedSet<string>();
				var weapons = new SortedSet<string>();
				foreach (var ti in actor.TraitInfos<TraitInfo>())
				{
					var tn = ti.GetType().Name;
					foreach (var f in ti.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
					{
						if (f.Name == "Image" || f.Name.EndsWith("Image", StringComparison.Ordinal) || f.Name == "FactionImages" || f.Name.EndsWith("Images", StringComparison.Ordinal))
							foreach (var s in Strings(f.GetValue(ti)))
								images.Add(s);
						if (f.GetCustomAttribute<WeaponReferenceAttribute>() != null)
							foreach (var s in Strings(f.GetValue(ti)))
								weapons.Add(s.ToLowerInvariant());
						if (f.Name == "VoiceSet")
							foreach (var s in Strings(f.GetValue(ti)))
								voiceSets.Add(s);
					}

					if (tn is "RenderSpritesInfo" or "RenderVoxelsInfo" && ti.GetType().GetField("Image")?.GetValue(ti) == null)
						images.Add(actor.Name);
				}

				var weaponImages = new SortedSet<string>();
				foreach (var wn in weapons)
				{
					if (!rules.Weapons.TryGetValue(wn, out var w))
						continue;
					foreach (var o in new object[] { w.Projectile }.Concat(w.Warheads))
						if (o != null)
							foreach (var f in o.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
								if (f.Name == "Image" || f.Name.EndsWith("Image", StringComparison.Ordinal))
									foreach (var s in Strings(f.GetValue(o)))
										weaponImages.Add(s);
				}

				result[actor.Name] = new Dictionary<string, object>
				{
					["sources"] = ruleSources.TryGetValue(actor.Name, out var src) ? src : [],
					["images"] = images.ToList(),
					["weapons"] = weapons.ToList(),
					["weaponImages"] = weaponImages.ToList(),
					["voiceSets"] = voiceSets.ToList(),
					["buildable"] = actor.TraitInfos<TraitInfo>().Any(t => t.GetType().Name == "BuildableInfo"),
				};
			}

			return result;
		}

		// ---------------------------------------------------------------- what each faction can reach in a skirmish
		static bool IsA(object o, string typeName)
		{
			for (var t = o.GetType(); t != null; t = t.BaseType)
				if (t.Name == typeName)
					return true;
			return false;
		}

		static T Get<T>(object o, string field) { return (T)o.GetType().GetField(field).GetValue(o); }

		static readonly HashSet<string> NonSpawningReferences =
		[
			"RepairableInfo", "RepairableNearInfo", "RearmableInfo", "TransformsIntoRepairableInfo", "GrantConditionOnProductionInfo",
			"ProductionCostMultiplierInfo", "ProductionTimeMultiplierInfo", "AutoTargetPriorityInfo",
		];

		Dictionary<string, object> Reachability()
		{
			var rules = modData.DefaultRules;
			var world = rules.Actors[SystemActors.World];
			var player = rules.Actors[SystemActors.Player];
			var factionInfos = world.TraitInfos<TraitInfo>().Where(t => IsA(t, "FactionInfo")).ToList();
			var result = new Dictionary<string, object>();

			foreach (var fi in factionInfos)
			{
				var faction = Get<string>(fi, "InternalName");
				if (!Get<bool>(fi, "Selectable"))
					continue;

				bool FactionOk(object t)
				{
					var fs2 = t.GetType().GetField("Factions")?.GetValue(t) as IEnumerable;
					var list = fs2 == null ? [] : fs2.Cast<object>().Select(x => x.ToString()).ToList();
					return list.Count == 0 || list.Contains(faction);
				}

				var provided = new HashSet<string>();
				var queues = new HashSet<string>();
				foreach (var t in player.TraitInfos<TraitInfo>())
				{
					if (IsA(t, "ProvidesPrerequisiteInfo") && FactionOk(t))
						provided.Add(Get<string>(t, "Prerequisite") ?? "player");
					if (IsA(t, "ProvidesTechPrerequisiteInfo"))
						foreach (var s in Strings(t.GetType().GetField("Prerequisites").GetValue(t)))
							provided.Add(s);
					if (IsA(t, "ProductionQueueInfo") && FactionOk(t))
						queues.Add(Get<string>(t, "Type"));
				}

				var reach = new HashSet<string>();
				var why = new Dictionary<string, string>();
				void Add(string a, string reason)
				{
					a = a.ToLowerInvariant();
					if (rules.Actors.ContainsKey(a) && reach.Add(a))
						why[a] = reason;
				}

				foreach (var su in world.TraitInfos<TraitInfo>().Where(t => IsA(t, "StartingUnitsInfo") && FactionOk(t)))
				{
					Add(Get<string>(su, "BaseActor") ?? "", "starting units");
					foreach (var s in Strings(su.GetType().GetField("SupportActors").GetValue(su)))
						Add(s, "starting units");
				}

				var produced = new HashSet<string>();
				var changed = true;
				while (changed)
				{
					changed = false;
					var before = reach.Count + provided.Count + produced.Count;
					foreach (var a in reach.ToList())
					{
						foreach (var t in rules.Actors[a].TraitInfos<TraitInfo>())
						{
							if (IsA(t, "ProvidesPrerequisiteInfo") && FactionOk(t))
								provided.Add(Get<string>(t, "Prerequisite") ?? a);
							if (IsA(t, "ProductionInfo"))
								foreach (var s in Strings(t.GetType().GetField("Produces").GetValue(t)))
									produced.Add(s);
							if (IsA(t, "ProductionQueueInfo") && FactionOk(t))
								queues.Add(Get<string>(t, "Type"));

							// Follow references that bring an actor into the game (transform, spawn, free actor, cargo,
							// support-power aircraft); skip ones that only name an actor someone else must own.
							if (NonSpawningReferences.Contains(t.GetType().Name))
								continue;

							foreach (var f in t.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
								if (f.GetCustomAttribute<ActorReferenceAttribute>() != null)
									foreach (var s in Strings(f.GetValue(t)))
										Add(s, $"{a}.{t.GetType().Name.Replace("Info", "")}.{f.Name}");
						}
					}

					foreach (var (name, actor) in rules.Actors)
					{
						if (reach.Contains(name) || name.StartsWith('^'))
							continue;
						var b = actor.TraitInfos<TraitInfo>().FirstOrDefault(t => IsA(t, "BuildableInfo"));
						if (b == null)
							continue;
						var q = Strings(b.GetType().GetField("Queue").GetValue(b)).ToList();
						if (!q.Any(x => queues.Contains(x) && produced.Contains(x)))
							continue;
						var ok = true;
						foreach (var p in Strings(b.GetType().GetField("Prerequisites").GetValue(b)))
						{
							var tok = p.TrimStart('~');
							if (tok.StartsWith('!'))
								ok &= !provided.Contains(tok[1..]);
							else
								ok &= provided.Contains(tok);
						}

						if (ok)
							Add(name, "buildable");
					}

					changed = reach.Count + provided.Count + produced.Count != before;
				}

				result[faction] = new Dictionary<string, object>
				{
					["side"] = Get<string>(fi, "Side"),
					["actors"] = why.OrderBy(kv => kv.Key).ToDictionary(kv => kv.Key, kv => (object)kv.Value),
					["prerequisites"] = provided.OrderBy(x => x).ToList(),
				};
			}

			return result;
		}

		// ---------------------------------------------------------------- shipped maps
		List<object> Maps()
		{
			var result = new List<object>();
			foreach (var (folder, cls) in modData.Manifest.MapFolders)
			{
				IReadOnlyPackage pkg;
				try { pkg = fs.OpenPackage(folder); }
				catch { continue; }
				if (pkg == null)
					continue;

				foreach (var entry in pkg.Contents)
				{
					IReadOnlyPackage mp;
					try { mp = pkg.OpenPackage(entry, fs); }
					catch { continue; }
					if (mp == null || !mp.Contains("map.yaml"))
						continue;

					try
					{
						var map = new Map(modData, mp);
						var types = new SortedDictionary<ushort, int>();
						var resources = new SortedDictionary<byte, int>();
						foreach (var cell in map.AllCells)
						{
							var t = map.Tiles[cell];
							types[t.Type] = types.GetValueOrDefault(t.Type) + 1;
							var r = map.Resources[cell];
							if (r.Type != 0)
								resources[r.Type] = resources.GetValueOrDefault(r.Type) + 1;
						}

						var actorTypes = new SortedDictionary<string, int>();
						foreach (var a in map.ActorDefinitions)
							actorTypes[a.Value.Value] = actorTypes.GetValueOrDefault(a.Value.Value) + 1;

						result.Add(new Dictionary<string, object>
						{
							["folder"] = entry,
							["title"] = map.Title,
							["author"] = map.Author,
							["tileset"] = map.Tileset,
							["size"] = new[] { map.MapSize.Width, map.MapSize.Height },
							["players"] = map.PlayerDefinitions.Count(p => p.Value.NodeWithKeyOrDefault("Playable")?.Value.Value == "True"),
							["visibility"] = map.Visibility.ToString(),
							["templates"] = types.ToDictionary(kv => kv.Key.ToString(), kv => kv.Value),
							["resources"] = resources.ToDictionary(kv => kv.Key.ToString(), kv => kv.Value),
							["actors"] = actorTypes,
							["customRules"] = map.RuleDefinitions != null,
							["customSequences"] = map.SequenceDefinitions != null,
							["files"] = mp.Contents.ToList(),
						});
					}
					catch (Exception e)
					{
						result.Add(new Dictionary<string, object> { ["folder"] = entry, ["error"] = e.Message });
					}
				}
			}

			return result;
		}
	}
}
