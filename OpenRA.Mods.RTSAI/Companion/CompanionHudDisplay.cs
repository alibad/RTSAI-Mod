using System;

namespace OpenRA.Mods.RTSAI.Companion
{
	public static class CompanionHudDisplay
	{
		public static bool IsVisible(CompanionHostState host, bool acknowledged, bool enabled, bool allowed)
		{
			return acknowledged && enabled && allowed &&
				host is CompanionHostState.Running or CompanionHostState.External;
		}

		public static (int X, int Width, int Height) Layout(int viewportWidth, bool pending)
		{
			var battlefield = Math.Max(1, viewportWidth - 250);
			var width = Math.Min(540, Math.Max(1, battlefield - 32));
			return (Math.Max(16, (battlefield - width) / 2), width, pending ? 100 : 64);
		}

		public static string Message(string state, string message)
		{
			if (message != null && message.StartsWith("AI ALERTS ONLY", StringComparison.Ordinal))
				return message;
			if (state == "muted")
				return "Spoken replies are off. Battlefield alerts remain available.";
			if (state != null && (state == "ready" || state.StartsWith("ready:", StringComparison.Ordinal)))
				return "Adviser connected. Open Details for activity and controls.";
			return state == "error" ? "Advice paused. Check AI settings for details." : message;
		}
	}
}
