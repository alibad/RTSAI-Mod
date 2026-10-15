using System;
using System.IO;
using System.Linq;
using OpenRA.Mods.Common.Experience;
using OpenRA.Mods.RTSAI.Traits;

namespace OpenRA.Mods.RTSAI.UtilityCommands
{
	public sealed class CheckDesktopSettingsCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--check-desktop-settings";
		bool IUtilityCommand.ValidateArguments(string[] args) => args.Length == 1;
		[Desc("Verify independent mode preferences, saved experience profiles, shared display settings and legacy voice fallback.")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			var path = Path.Combine(Path.GetTempPath(), "rtsai-mode-check-" + Guid.NewGuid().ToString("N") + ".yaml");
			try
			{
				var settings = new Settings(path, Arguments.Empty);
				var classic = new RTSAIModePreferences(new MiniYaml(null, [new MiniYamlNode("Mod", "rtsai-classic-core")]));
				var ra2 = new RTSAIModePreferences(new MiniYaml(null, [new MiniYamlNode("Mod", "rtsai")]));
				settings.Graphics.UIScale = 1.5f;
				settings.GetOrCreate<RTSAISettings>(null).VoiceLanguage = "en";
				classic.Activate(settings);
				settings.Game.MouseControlStyle = MouseControlStyle.Classic;
				settings.Game.StatusBars = StatusBarsType.AlwaysShow;
				settings.Graphics.ViewportDistance = WorldViewport.Close;
				classic.Capture(settings);
				ra2.Activate(settings);
				settings.Game.MouseControlStyle = MouseControlStyle.Modern;
				settings.Game.StatusBars = StatusBarsType.DamageShow;
				settings.Graphics.ViewportDistance = WorldViewport.Far;
				ra2.Capture(settings);
				settings.GetOrCreate<RTSAIModeSettings>(null, "rtsai").VoiceLanguage = "faction";
				settings.GetOrCreate<ExperienceSettings>(null, "rtsai").Profile = "ra2-classic";
				settings.GetOrCreate<ExperienceSettings>(null, "rtsai-classic-core").Profile = "layered-defense";
				settings.Save();
				var reloaded = new Settings(path, Arguments.Empty);
				classic.Activate(reloaded);
				if (reloaded.Game.MouseControlStyle != MouseControlStyle.Classic || reloaded.Game.StatusBars != StatusBarsType.AlwaysShow || reloaded.Graphics.ViewportDistance != WorldViewport.Close)
					throw new InvalidDataException("Classic gameplay preferences did not survive switching/reload.");
				ra2.Activate(reloaded);
				if (reloaded.Game.MouseControlStyle != MouseControlStyle.Modern || reloaded.Game.StatusBars != StatusBarsType.DamageShow || reloaded.Graphics.ViewportDistance != WorldViewport.Far)
					throw new InvalidDataException("RA2 gameplay preferences did not survive switching/reload.");
				if (reloaded.Graphics.UIScale != 1.5f)
					throw new InvalidDataException("Shared display preferences changed while switching modes.");
				if (reloaded.GetOrCreate<ExperienceSettings>(null, "rtsai").Profile != "ra2-classic" || reloaded.GetOrCreate<ExperienceSettings>(null, "rtsai-classic-core").Profile != "layered-defense")
					throw new InvalidDataException("Experience profiles leaked between modes.");
				if (reloaded.GetOrCreate<RTSAIModeSettings>(null, "rtsai").VoiceLanguage != "faction" || reloaded.GetOrCreate<RTSAIModeSettings>(null, "rtsai-classic-core").VoiceLanguage != null || reloaded.GetOrCreate<RTSAISettings>(null).VoiceLanguage != "en")
					throw new InvalidDataException("Mode voice settings or legacy preference were lost.");
				Console.WriteLine("Desktop mode settings: independent gameplay/profiles/voices and shared display round-trip passed.");
			}
			finally
			{
				if (File.Exists(path))
					File.Delete(path);
			}
		}
	}
}
