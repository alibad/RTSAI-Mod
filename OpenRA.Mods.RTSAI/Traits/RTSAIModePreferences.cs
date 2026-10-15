using System;
using OpenRA.Primitives;

namespace OpenRA.Mods.RTSAI.Traits
{
	[SettingsModule.YamlNode("RTSAIGameplay", shared: false)]
	public sealed class RTSAIModeSettings : SettingsModule
	{
		public bool Initialized;
		public MouseControlStyle MouseControlStyle = MouseControlStyle.Modern;
		public MouseScrollType MouseScroll = MouseScrollType.Joystick;
		public float UIScrollSpeed = 50f;
		public float ZoomSpeed = 0.04f;
		public WorldViewport BattlefieldCamera = WorldViewport.Medium;
		public bool ViewportEdgeScroll = true;
		public bool UseAlternateScrollButton;
		public bool LockMouseWindow;
		public StatusBarsType StatusBars = StatusBarsType.Standard;
		public TargetLinesType TargetLines = TargetLinesType.Manual;
		public bool UsePlayerStanceColors;
		public string VoiceLanguage;
	}

	public sealed class RTSAIModePreferences : IModSettingsLifecycle
	{
		readonly string mod;
		public RTSAIModePreferences(MiniYaml yaml)
		{
			mod = yaml.NodeWithKey("Mod").Value.Value;
		}

		public void Activate(Settings settings)
		{
			var mode = settings.GetOrCreate<RTSAIModeSettings>(null, mod);
			if (!mode.Initialized)
			{
				Capture(settings);
				return;
			}
			var game = settings.Game;
			game.MouseControlStyle = mode.MouseControlStyle;
			game.MouseScroll = mode.MouseScroll;
			game.UIScrollSpeed = mode.UIScrollSpeed;
			game.ZoomSpeed = mode.ZoomSpeed;
			settings.Graphics.ViewportDistance = mode.BattlefieldCamera;
			game.ViewportEdgeScroll = mode.ViewportEdgeScroll;
			game.UseAlternateScrollButton = mode.UseAlternateScrollButton;
			game.LockMouseWindow = mode.LockMouseWindow;
			game.StatusBars = mode.StatusBars;
			game.TargetLines = mode.TargetLines;
			game.UsePlayerStanceColors = mode.UsePlayerStanceColors;
		}

		public void Capture(Settings settings)
		{
			var mode = settings.GetOrCreate<RTSAIModeSettings>(null, mod);
			var game = settings.Game;
			mode.Initialized = true;
			mode.MouseControlStyle = game.MouseControlStyle;
			mode.MouseScroll = game.MouseScroll;
			mode.UIScrollSpeed = game.UIScrollSpeed;
			mode.ZoomSpeed = game.ZoomSpeed;
			mode.BattlefieldCamera = settings.Graphics.ViewportDistance;
			mode.ViewportEdgeScroll = game.ViewportEdgeScroll;
			mode.UseAlternateScrollButton = game.UseAlternateScrollButton;
			mode.LockMouseWindow = game.LockMouseWindow;
			mode.StatusBars = game.StatusBars;
			mode.TargetLines = game.TargetLines;
			mode.UsePlayerStanceColors = game.UsePlayerStanceColors;
		}

		public static string CurrentVoiceLanguage() => Game.ModData.GetSettings<RTSAIModeSettings>().VoiceLanguage
			?? Game.Settings.GetOrCreate<RTSAISettings>(null).VoiceLanguage;
	}
}
