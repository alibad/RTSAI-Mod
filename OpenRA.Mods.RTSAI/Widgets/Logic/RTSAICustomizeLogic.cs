using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using OpenRA.Mods.Common.Experience;
using OpenRA.Mods.Common.Server;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.RTSAI.Library;
using OpenRA.Mods.RTSAI.Widgets;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	[SettingsModule.YamlNode("RTSAICustomSetup", shared: false)]
	public sealed class RTSAICustomSetup : SettingsModule
	{
		public bool HasSavedCustom;
		public string Components = "";
	}

	public sealed class RTSAICustomizeLogic : ChromeLogic
	{
		readonly LibrarySurfaceWidget surface;
		readonly ModData mod;
		readonly ExperienceCatalog catalog;
		readonly ExperienceSettings settings;
		readonly RTSAICustomSetup custom;
		readonly World world;
		ImmutableArray<string> selected, customSelection;
		ExperienceComponent[] components;
		string preset, category = "All", message = "", detail;
		int first;
		bool assistant;
		const int PageSize = 4;

		[ObjectCreator.UseCtor]
		public RTSAICustomizeLogic(LibrarySurfaceWidget widget, ModData modData, World world)
		{
			surface = widget; mod = modData; this.world = world;
			catalog = mod.Get<ExperienceCatalog>();
			settings = Game.Settings.GetOrCreate<ExperienceSettings>(null, mod.Manifest.Id);
			custom = Game.Settings.GetOrCreate<RTSAICustomSetup>(null, mod.Manifest.Id);
			selected = catalog.ActiveComponentIds;
			customSelection = custom.HasSavedCustom ? custom.Components.Split(',', StringSplitOptions.RemoveEmptyEntries).Where(catalog.Components.ContainsKey).ToImmutableArray() : selected;
			preset = catalog.UsesCustomComponents ? "Custom" : selected.Length == 0 ? "Original" : "Enhanced";
			var options = Game.Settings.GetOrCreate<SkirmishLogic.SkirmishSettings>(null, mod.Manifest.Id).Yaml.Build().NodeWithKeyOrDefault("Options");
			assistant = options?.Value.NodeWithKeyOrDefault("rtsai-cocommander")?.Value.Value != "False";
			components = catalog.Components.Values.Where(c => c.IsSelectable && c.Kind != ExperienceComponentKind.Authoring)
				.OrderBy(c => c.Kind == ExperienceComponentKind.Faction ? 1 : 0).ThenBy(c => c.Title).ToArray();
			detail = components.FirstOrDefault(c => c.Id == "minefield-generator")?.Id ?? components.FirstOrDefault()?.Id;
			surface.Quiet = true; surface.OnBack = Close;
			surface.OnScroll = direction => { first = Math.Clamp(first + direction * PageSize, 0, Math.Max(0, Filtered().Length - PageSize)); Build(); };
			Build();
			Console.WriteLine("RTSAI_CUSTOMIZE|" + mod.Manifest.Id + "|" + preset);
		}
		ExperienceComponent[] Filtered() => components.Where(c => category == "All" || (category == "Factions" ? c.Kind == ExperienceComponentKind.Faction : c.Kind != ExperienceComponentKind.Faction)).ToArray();
		void Close() => Ui.CloseWindow();
		void ChoosePreset(string value)
		{
			if (preset == "Custom") customSelection = selected;
			preset = value;
			selected = value == "Original" ? [] : value == "Custom" ? customSelection : catalog.ComponentsForProfile(catalog.DefaultProfileId);
			message = value == "Original" ? "Optional gameplay additions disabled. Your custom setup is retained." : "";
			Build();
		}
		void Toggle(ExperienceComponent component)
		{
			try
			{
				var enabled = selected.Contains(component.Id);
				var before = selected;
				selected = catalog.ToggleComponent(selected, component.Id, !enabled);
				var added = selected.Except(before).Where(id => id != component.Id).Select(id => catalog.Components[id].Title).ToArray();
				var removed = before.Except(selected).Where(id => id != component.Id).Select(id => catalog.Components[id].Title).ToArray();
				preset = "Custom"; customSelection = selected; detail = component.Id;
				message = (enabled ? "Disabled " : "Enabled ") + component.Title + ".";
				if (added.Length > 0) message += " Includes: " + string.Join(", ", added) + ".";
				if (removed.Length > 0) message += " Also disables: " + string.Join(", ", removed) + ".";
				Build();
			}
			catch (Exception e) { message = e.Message; }
		}
		void Build()
		{
			surface.Clear(); surface.RenderContent = Draw;
			surface.Button(mod, "BACK", NativeGameLibrary.Name(mod.Manifest.Id) + " menu", 80, 30, 310, 58, Close).Flat = true;
			var names = new[] { "Original", "Enhanced", "Custom" };
			for (var i = 0; i < names.Length; i++)
			{
				var name = names[i];
				var b = surface.Button(mod, "PRESET_" + name, name, 80 + i * 590, 240, 560, 95, () => ChoosePreset(name));
				b.TextSize = 36; b.IsHighlighted = () => preset == name;
			}
			for (var i = 0; i < 3; i++)
			{
				var name = new[] { "All", "Gameplay", "Factions" }[i];
				var b = surface.Button(mod, "CATEGORY_" + name, name, 80 + i * 220, 380, 205, 48, () => { category = name; first = 0; Build(); });
				b.IsHighlighted = () => category == name;
			}
			var ai = surface.Button(mod, "ASSISTANT", "AI co-commander", 80, 454, 685, 63, () => { assistant = !assistant; Build(); });
			ai.Flat = true;
			surface.Button(mod, "ASSISTANT_TOGGLE", assistant ? "ON" : "OFF", 800, 454, 125, 63, () => { assistant = !assistant; Build(); }).IsHighlighted = () => assistant;
			var visible = Filtered().Skip(first).Take(PageSize).ToArray();
			for (var i = 0; i < visible.Length; i++)
			{
				var component = visible[i]; var y = 545 + i * 80;
				var row = surface.Button(mod, "DETAIL_" + component.Id, component.Title, 80, y, 685, 69, () => { detail = component.Id; Build(); });
				row.Flat = true; row.TextSize = 27; row.IsHighlighted = () => detail == component.Id;
				var toggle = surface.Button(mod, "TOGGLE_" + component.Id, selected.Contains(component.Id) ? "ON" : "OFF", 800, y, 125, 69, () => Toggle(component));
				toggle.IsHighlighted = () => selected.Contains(component.Id);
			}
			surface.Button(mod, "PREVIOUS", "Previous", 80, 875, 210, 48, () => { first = Math.Max(0, first - PageSize); Build(); }).IsDisabled = () => first == 0;
			surface.Button(mod, "NEXT", "More additions", 715, 875, 210, 48, () => { first = Math.Min(Math.Max(0, Filtered().Length - PageSize), first + PageSize); Build(); }).IsDisabled = () => first + PageSize >= Filtered().Length;
			if (detail != null)
			{
				var preview = new FactionPackPreviewWidget();
				preview.Update(mod.DefaultFileSystem, catalog.Components[detail].Preview);
				surface.Place(preview, 1020, 405, 790, 260);
			}
			surface.Button(mod, "CANCEL", "Cancel", 1200, 965, 240, 66, Close);
			surface.Button(mod, "SAVE", "Save setup", 1465, 965, 375, 66, Save, true);
			surface.Button(mod, "RESTORE", "Restore original setup", 80, 1035, 370, 40, () => ChoosePreset("Original")).Flat = true;
			surface.Button(mod, "CREATOR_TOOLS", "Creator Tools", 1530, 1035, 310, 40, () =>
			{
				Game.OpenWindow("EXPERIENCE_COMPOSER_PANEL", new WidgetArgs { { "onExit", (Action)(() => { }) } });
			}).Flat = true;
		}
		void Save()
		{
			settings.Profile = preset == "Original" ? (mod.Manifest.Id == "rtsai-classic-core" ? "ai-assistant-only" : "ra2-classic") : catalog.DefaultProfileId;
			settings.UseCustomComponents = preset == "Custom";
			settings.EnabledComponents = preset == "Custom" ? string.Join(",", selected.Order()) : "";
			if (preset == "Custom") { custom.HasSavedCustom = true; custom.Components = settings.EnabledComponents; }
			var skirmish = Game.Settings.GetOrCreate<SkirmishLogic.SkirmishSettings>(null, mod.Manifest.Id);
			var options = skirmish.Yaml.Nodes.FirstOrDefault(n => n.Key == "Options");
			if (options == null) { options = new MiniYamlNodeBuilder("Options", new MiniYamlBuilder(null)); skirmish.Yaml.Nodes.Add(options); }
			options.Value.Nodes.RemoveAll(n => n.Key == "rtsai-cocommander");
			options.Value.Nodes.Add(new MiniYamlNodeBuilder("rtsai-cocommander", new MiniYamlBuilder(assistant ? "True" : "False")));
			Game.Settings.Save();
			Console.WriteLine("RTSAI_SETUP_SAVED|" + mod.Manifest.Id + "|" + preset + "|" + string.Join(",", selected));
			Ui.CloseWindow();
			Game.RunAfterTick(() => Game.InitializeMod(Game.Mods[mod.Manifest.Id], new Arguments()));
		}
		void Draw()
		{
			surface.Image("frontline-assets", "logo", 1605, 28, 234, 78);
			surface.Text(80, 106, "Customize " + NativeGameLibrary.Name(mod.Manifest.Id), 80, display: true);
			surface.Text(80, 202, "Choose how you want to play. Your base game stays intact.", 28, LibrarySurfaceWidget.Muted);
			surface.Text(80, 345, "Gameplay additions", 30);
			surface.Text(80, 523, "Advice and suggested orders. Voice and model settings stay in Settings > AI.", 19, LibrarySurfaceWidget.Muted);
			surface.Text(330, 885, $"{Math.Min(first + 1, Filtered().Length)}–{Math.Min(first + PageSize, Filtered().Length)} of {Filtered().Length}", 22, LibrarySurfaceWidget.Muted);
			if (detail != null)
			{
				var c = catalog.Components[detail];
				surface.Text(1020, 348, c.Kind == ExperienceComponentKind.Faction ? "Faction addition" : "Gameplay addition", 26, LibrarySurfaceWidget.Muted);
				surface.Text(1020, 682, c.Title, 40, display: true);
				var description = c.Effects.Length < 290 ? c.Effects : c.Description;
				surface.Text(1020, 744, description, 25, width: 790);
				var requires = c.Dependencies.Where(id => catalog.Components[id].IsSelectable).Select(id => catalog.Components[id].Title).ToArray();
				surface.Text(1020, 867, requires.Length == 0 ? "Ready for this game" : "Includes: " + string.Join(", ", requires), 22, LibrarySurfaceWidget.Amber, 790);
			}
			surface.Rule(80, 946, 1760);
			surface.Text(80, 961, "Applies to new matches · " + NativeGameLibrary.Name(mod.Manifest.Id) + " only", 25);
			surface.Text(80, 999, "Saved games keep their existing rules.", 22, LibrarySurfaceWidget.Muted);
			if (message != "") surface.Text(80, 925, message.Length > 155 ? message[..152] + "…" : message, 18, LibrarySurfaceWidget.Amber, 1750);
		}
	}
}
