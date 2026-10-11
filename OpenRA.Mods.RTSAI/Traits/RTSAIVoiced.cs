using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	[SettingsModule.YamlNode("RTSAI", shared: true)]
	public sealed class RTSAISettings : SettingsModule
	{
		public string VoiceLanguage = "faction";
		public static string Normalize(string value) => value == "en" ? "en" : "faction";
	}

	public class RTSAIVoicedInfo : VoicedInfo
	{
		public override object Create(ActorInitializer init) => new RTSAIVoiced(this);
	}

	public sealed class RTSAIVoiced : Voiced, IVoiced
	{
		readonly RTSAIVoicedInfo voiceInfo;
		public RTSAIVoiced(RTSAIVoicedInfo info) : base(info) { voiceInfo = info; }
		public static string Resolve(string voiceSet, Ruleset rules, string preference)
		{
			if (string.IsNullOrEmpty(voiceSet))
				return voiceSet;
			var original = voiceSet.ToLowerInvariant();
			var selected = original + "__" + RTSAISettings.Normalize(preference);
			return rules.Voices.ContainsKey(selected) ? selected : original;
		}
		string Selected(Ruleset rules) => Resolve(voiceInfo.VoiceSet, rules,
			Game.Settings.GetOrCreate<RTSAISettings>(null).VoiceLanguage);
		string IVoiced.VoiceSet => Selected(Game.ModData.DefaultRules);
		bool IVoiced.PlayVoice(Actor self, string phrase, string variant)
		{
			if (IsTraitDisabled || phrase == null || string.IsNullOrEmpty(voiceInfo.VoiceSet))
				return false;
			return Game.Sound.PlayPredefined(SoundType.World, self.World.Map.Rules, null, self,
				Selected(self.World.Map.Rules), phrase, variant, true, WPos.Zero, voiceInfo.Volume, true);
		}
		bool IVoiced.PlayVoiceLocal(Actor self, string phrase, string variant, float volume)
		{
			if (IsTraitDisabled || phrase == null || string.IsNullOrEmpty(voiceInfo.VoiceSet))
				return false;
			return Game.Sound.PlayPredefined(SoundType.World, self.World.Map.Rules, null, self,
				Selected(self.World.Map.Rules), phrase, variant, false, self.CenterPosition, volume, true);
		}
		bool IVoiced.HasVoice(Actor self, string voice)
		{
			if (IsTraitDisabled || string.IsNullOrEmpty(voiceInfo.VoiceSet))
				return false;
			return self.World.Map.Rules.Voices[Selected(self.World.Map.Rules)].Voices.ContainsKey(voice);
		}
	}
}
