using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using OpenRA.Mods.Common.Experience;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.RTSAI.Library;
using OpenRA.Mods.RTSAI.Widgets;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	public sealed class RTSAILibraryLogic : ChromeLogic
	{
		readonly LibrarySurfaceWidget surface;
		readonly ModData mod;
		readonly CommunityInstall installer = new();
		readonly Dictionary<string, bool> installed = new();
		string page = "library", filter = "All", query = "", message = "";
		int selected, selectedGame = 1;
		bool reviewed, wasBusy;
		TextFieldWidget search;
		DateTime lastPoll;

		[ObjectCreator.UseCtor]
		public RTSAILibraryLogic(LibrarySurfaceWidget widget, ModData modData)
		{
			surface = widget; mod = modData;
			selectedGame = Math.Max(0, Array.FindIndex(NativeGameLibrary.Games, g => g.Id == Game.Settings.GetOrCreate<RTSAILauncherSettings>(null).LastGame));
			if (Environment.GetEnvironmentVariable("RTSAI_LIBRARY_SCREEN") == "community" || widget.Id == "RTSAI_COMMUNITY") page = "community";
			Environment.SetEnvironmentVariable("RTSAI_LIBRARY_SCREEN", null);
			surface.OnBack = () => { if (page != "library") { page = "library"; Build(); } };
			surface.OnTick = () =>
			{
				if ((DateTime.UtcNow - lastPoll).TotalMilliseconds < 500) return;
				lastPoll = DateTime.UtcNow; installer.Poll();
				if (wasBusy && !installer.Busy) Build();
				wasBusy = installer.Busy;
			};
			Build();
			Console.WriteLine("RTSAI_LIBRARY|" + page);
		}
		void Go(string destination) { page = destination; message = ""; Build(); }
		void Build()
		{
			surface.Clear(); surface.Quiet = page != "library";
			foreach (var release in CommunityInstall.Releases) installed[release.Id] = CommunityInstall.InstalledExecutable(release) != null;
			Nav("Library", 360, () => Go("library"), page == "library");
			Nav("Community", 540, () => Go("community"), page == "community");
			Nav("Downloads", 1560, () => Go("downloads"), page == "downloads");
			surface.RenderContent = Draw;
			if (page == "library") Library();
			else if (page == "community") Community();
			else if (page == "preferences") Preferences();
			else if (page == "import") Import();
			else if (page == "sources") Sources();
			else Downloads();
		}
		void Nav(string text, int x, Action action, bool selectedState)
		{
			var b = surface.Button(mod, "NAV_" + text, text, x, 34, 180, 54, action); b.Flat = true; b.IsHighlighted = () => selectedState;
		}
		void Library()
		{
			for (var i = 0; i < NativeGameLibrary.Games.Length; i++)
			{
				var index = i; var game = NativeGameLibrary.Games[i]; var x = 78 + i * 590;
				var select = surface.Button(mod, "SELECT_" + game.Id, "", x, 265, 560, 525, () => { selectedGame = index; Build(); });
				select.Invisible = true;
				var open = surface.Button(mod, "OPEN_" + game.Id, "Open " + game.Name, x + 38, 810, 484, 68, () => Open(game.Id), i == selectedGame);
				open.TextSize = 32;
			}
			surface.Button(mod, "PREFERENCES", "Launcher preferences", 78, 992, 330, 52, () => Go("preferences")).Flat = true;
			surface.Button(mod, "QUIT", "Quit", 1692, 992, 150, 52, Game.Exit).Flat = true;
			var n = 0;
			foreach (var release in CommunityInstall.Releases.Where(r => installed[r.Id]))
			{
				var r = release;
				surface.Button(mod, "OPEN_COMMUNITY_" + r.Id, "Open " + r.Name, 610 + n++ * 370, 933, 350, 55, () => Try(() => CommunityInstall.Launch(r)));
			}
		}
		void Open(string id)
		{
			message = "Opening " + NativeGameLibrary.Name(id) + "…";
			Game.RunAfterTick(() => Try(() => NativeGameLibrary.Open(id)));
		}
		void Community()
		{
			search = new TextFieldWidget { Id = "COMMUNITY_SEARCH", Text = query, Font = "Regular", MaxLength = 80 };
			search.OnTextEdited = () => { query = search.Text; Refilter(); };
			surface.Place(search, 80, 260, 700, 55);
			foreach (var (name, x) in new[] { ("All", 80), ("Complete games", 320), ("Add-ons", 560) })
			{
				var value = name;
				var b = surface.Button(mod, "FILTER_" + name, name, x, 338, 220, 50, () => { filter = value; reviewed = false; Build(); });
				b.IsHighlighted = () => filter == value;
			}
			for (var i = 0; i < CommunityInstall.Releases.Length; i++)
			{
				var index = i; var release = CommunityInstall.Releases[i];
				var row = surface.Button(mod, "PACK_" + release.Id, release.Name, 80, 416 + i * 126, 700, 112,
					() => { selected = index; reviewed = false; message = ""; Build(); });
				row.Flat = true; row.TextSize = 32;
				row.IsVisible = () => filter != "Add-ons" && release.Name.Contains(query, StringComparison.OrdinalIgnoreCase);
				row.IsHighlighted = () => selected == index;
			}
			var current = CommunityInstall.Releases[selected];
			var action = surface.Button(mod, "INSTALL", "Check & install", 860, 790, 610, 70, () =>
			{
				var chosen = CommunityInstall.Releases[selected];
				if (installer.Busy) { installer.Cancel(); return; }
				if (installed[chosen.Id]) { Try(() => CommunityInstall.Launch(chosen)); return; }
				if (!reviewed) { reviewed = true; message = "Official Windows x64 release · includes its compatible engine. Ready to install."; Build(); return; }
				wasBusy = true; installer.RequestInstall(chosen);
			}, true);
			action.GetText = () => installer.Busy ? "Pause download" : installed[CommunityInstall.Releases[selected].Id] ? "Open " + CommunityInstall.Releases[selected].Name : reviewed ? $"Install · {CommunityInstall.Releases[selected].Bytes / 1048576d:0} MB" : "Check & install";
			action.IsVisible = () => filter != "Add-ons";
			surface.Button(mod, "SOURCE_PROJECTS", "Other downloaded projects", 80, 727, 700, 58, () => Go("sources")).Flat = true;
			surface.Button(mod, "IMPORT", "Import downloaded pack…", 1470, 986, 375, 58, () => Go("import")).Flat = true;
			surface.Button(mod, "BACK", "Back to Library", 80, 986, 330, 58, () => Go("library")).Flat = true;
			surface.Button(mod, "IMPORT_ADDON", "Import an add-on", 860, 790, 610, 70, () => Go("import"), true).IsVisible = () => filter == "Add-ons";
			Refilter();
		}
		void Refilter()
		{
			var match = Array.FindIndex(CommunityInstall.Releases, r => r.Name.Contains(query, StringComparison.OrdinalIgnoreCase));
			if (match >= 0 && !CommunityInstall.Releases[selected].Name.Contains(query, StringComparison.OrdinalIgnoreCase))
			{
				selected = match; reviewed = false;
			}
		}
		void Preferences()
		{
			var preferences = Game.Settings.GetOrCreate<RTSAILauncherSettings>(null);
			surface.Button(mod, "OPEN_STORAGE", "Open local storage", 100, 410, 620, 72,
				() => Try(() => System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(NativeGameLibrary.Root) { UseShellExecute = true })));
			surface.Button(mod, "OPEN_DOWNLOADS", "Open downloaded packages", 780, 410, 620, 72,
				() => Try(() =>
				{
					var downloads = Path.Combine(NativeGameLibrary.Root, "Downloads"); Directory.CreateDirectory(downloads);
					System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(downloads) { UseShellExecute = true });
				}));
			surface.Button(mod, "KEEP_LIBRARY", preferences.KeepLibraryOpen ? "Keep Library open: ON" : "Keep Library open: OFF", 100, 700, 900, 72, () =>
			{
				preferences.KeepLibraryOpen = !preferences.KeepLibraryOpen; Game.Settings.Save(); Build();
			});
			surface.Button(mod, "BACK", "Back to Library", 100, 920, 330, 64, () => Go("library"), true);
		}
		void Downloads()
		{
			surface.Button(mod, "CANCEL_DOWNLOAD", "Pause download", 100, 520, 400, 66, installer.Cancel).IsVisible = () => installer.Busy;
			surface.Button(mod, "BACK", "Back to Community", 100, 920, 380, 64, () => Go("community"), true);
		}
		void Sources()
		{
			surface.Button(mod, "BACK", "Back to Community", 100, 920, 380, 64, () => Go("community"), true);
		}
		void Import()
		{
			foreach (var (label, x, target) in new[] { ("Complete game ZIP", 100, "game"), ("Classic add-on", 540, "rtsai-classic-core"), ("RA2 add-on", 980, "rtsai-ra2"), ("RTS add-on", 1420, "rtsai") })
			{
				var mode = target;
				surface.Button(mod, "IMPORT_" + target, label, x, 405, 400, 80, () =>
				{
					Game.OpenWindow("RTSAI_PACKAGE_BROWSER", new WidgetArgs
					{
						{ "initialDirectory", (string)null }, { "onCancel", (Action)(() => { }) },
						{ "onSelected", (Action<string>)(source => ImportSelected(source, mode)) }
					});
				});
			}
			surface.Button(mod, "BACK", "Back to Community", 100, 920, 380, 64, () => Go("community"), true);
		}
		void ImportSelected(string source, string target)
		{
			Try(() =>
			{
				if (target == "game")
				{
					using var stream = File.OpenRead(source);
					var sha = Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
					var release = CommunityInstall.Releases.FirstOrDefault(r => r.Sha256 == sha)
						?? throw new InvalidDataException("This is not a supported official portable game package. Choose OpenHV or Combined Arms from Community.");
					selected = Array.IndexOf(CommunityInstall.Releases, release); page = "community"; reviewed = true; Build();
					wasBusy = true; installer.RequestInstall(release, source);
				}
				else
				{
					NativeGameLibrary.Open(target, "customize", importPack: source);
				}
			});
		}
		void Try(Action action) { try { action(); } catch (Exception e) { message = e.Message; } }
		void Draw()
		{
			surface.Image("frontline-assets", "logo", 80, 27, 234, 78);
			surface.Rule(80, 112, 1760);
			if (page == "library") DrawLibrary();
			else if (page == "community") DrawCommunity();
			else if (page == "preferences")
			{
				surface.Text(100, 165, "Launcher preferences", 64, display: true);
				surface.Text(100, 275, "Game settings live inside Classic, RA2 and RTS.", 30);
				surface.Text(100, 340, "Downloads and installed community games are kept together in local storage.", 26);
				surface.Text(100, 550, "Each game keeps its own display, audio, controls, setups and saves.", 28);
				surface.Text(100, 610, "Choose a game from Library, then open its Settings menu.", 26, LibrarySurfaceWidget.Muted);
			}
			else if (page == "sources") DrawSources();
			else if (page == "import")
			{
				surface.Text(100, 165, "Import a downloaded pack", 64, display: true);
				surface.Text(100, 275, "Choose where it belongs. We validate the package before installing it.", 30);
				surface.Text(100, 545, "Complete games: official portable OpenHV and Combined Arms ZIP releases.", 28);
				surface.Text(100, 615, "Add-ons: a compatible capability-pack ZIP or folder for the game you select.", 28);
				surface.Text(100, 695, "A source-code checkout is not an installed game.", 28, LibrarySurfaceWidget.Muted);
			}
			else
			{
				surface.Text(100, 165, "Downloads", 64, display: true);
				surface.Text(100, 300, installer.Status, 30, width: 1600);
				surface.Rect(100, 425, 1600, 12, LibrarySurfaceWidget.LineColor);
				surface.Rect(100, 425, 1600 * (float)installer.Progress, 12, LibrarySurfaceWidget.Amber);
				surface.Text(100, 625, "Interrupted downloads resume from the last received byte.", 26, LibrarySurfaceWidget.Muted);
			}
			if (message != "") surface.Text(100, 865, message, 24, LibrarySurfaceWidget.Amber, 1700);
		}
		void DrawLibrary()
		{
			surface.Text(495, 140, "Choose your game.", 80, display: true);
			for (var i = 0; i < NativeGameLibrary.Games.Length; i++)
			{
				var game = NativeGameLibrary.Games[i]; var x = 78 + i * 590;
				surface.Image("library-" + game.Art, "poster", x, 265, 560, 635);
				surface.Rect(x, 265, 560, 160, OpenRA.Primitives.Color.FromArgb(185, 8, 12, 14));
				surface.Rect(x, 737, 560, 163, OpenRA.Primitives.Color.FromArgb(200, 8, 12, 14));
				surface.Text(x + 38, 290, game.Name.ToUpperInvariant(), 64, display: true);
				surface.Text(x + 38, 382, game.Subtitle, 25, width: 490);
				surface.Text(x + 38, 758, i == 2 ? "INSTALLED · EXPERIMENTAL" : "INSTALLED", 22, i == 2 ? LibrarySurfaceWidget.Amber : LibrarySurfaceWidget.Cream);
				surface.Frame(x, 265, 560, 635, i == selectedGame ? LibrarySurfaceWidget.Amber : LibrarySurfaceWidget.LineColor);
			}
			surface.Text(80, 1052, "Downloads · Storage", 18, LibrarySurfaceWidget.Muted);
			if (!installed.Values.Any(v => v)) surface.Text(618, 948, "Each opens its own menu, campaigns and settings.", 25, LibrarySurfaceWidget.Muted);
		}
		void DrawCommunity()
		{
			surface.Text(80, 145, "Find your next battlefield.", 64, display: true);
			surface.Text(80, 225, "Install a complete game, or an add-on for one of yours.", 26, LibrarySurfaceWidget.Muted);
			var release = CommunityInstall.Releases[selected];
			if (filter == "Add-ons")
			{
				surface.Text(860, 430, "Add something to your game.", 48, display: true);
				surface.Text(860, 535, "Import a compatible add-on, then enable it in that game’s Customize screen.", 30, width: 900);
				surface.Text(80, 440, "Your authored additions already live inside each game.", 28, width: 670);
				return;
			}
			if (!CommunityInstall.Releases.Any(r => r.Name.Contains(query, StringComparison.OrdinalIgnoreCase)))
				surface.Text(80, 550, "No games match your search.", 28, LibrarySurfaceWidget.Muted);
			surface.Image("library-" + release.Art, "landscape", 860, 277, 950, 250);
			surface.Rect(860, 277, 950, 250, OpenRA.Primitives.Color.FromArgb(75, 5, 10, 12));
			surface.Text(880, 485, "MENU ILLUSTRATION · NOT GAMEPLAY", 18, LibrarySurfaceWidget.Cream);
			surface.Text(860, 552, release.Name, 56, display: true);
			surface.Text(860, 632, release.Description, 28, width: 930);
			surface.Text(860, 720, $"Complete game · version {release.Version} · {release.Bytes / 1048576d:0} MB · Windows x64", 25, LibrarySurfaceWidget.Muted);
			surface.Text(860, 900, installer.Busy || installer.ActiveId == release.Id ? installer.Status : "Includes its own compatible engine. Your games stay intact.", 23,
				LibrarySurfaceWidget.Amber, 930);
			if (installer.Busy) surface.Rect(860, 965, 950 * (float)installer.Progress, 6, LibrarySurfaceWidget.Amber);
		}
		void DrawSources()
		{
			surface.Text(100, 165, "Downloaded source projects", 64, display: true);
			surface.Text(100, 270, "Preserved for experimentation. These are not packaged installations yet.", 30);
			var names = new[] { "Cameo", "Generals Alpha", "RA+", "Romanov’s Vengeance", "Shattered Paradise", "OpenRA RA2", "OpenRA Mod SDK (tooling)" };
			for (var i = 0; i < names.Length; i++)
			{
				surface.Text(110, 365 + i * 65, names[i], 30);
				surface.Text(1000, 369 + i * 65, "Needs a compatible packaged runtime", 24, LibrarySurfaceWidget.Muted);
				surface.Rule(100, 420 + i * 65, 1700);
			}
		}
	}
}
