using System;
using System.IO;
using OpenRA.Mods.RTSAI.Companion;

namespace OpenRA.Mods.RTSAI.UtilityCommands
{
	public sealed class CheckCompanionHudCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--check-companion-hud";
		bool IUtilityCommand.ValidateArguments(string[] args) => args.Length == 1;
		[Desc("Check adviser availability, opt-out behavior and compact HUD bounds.")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			var cases = 0;
			foreach (var host in Enum.GetValues<CompanionHostState>())
			foreach (var acknowledged in new[] { false, true })
			foreach (var enabled in new[] { false, true })
			foreach (var allowed in new[] { false, true })
			{
				var show = CompanionHudDisplay.IsVisible(host, acknowledged, enabled, allowed);
				if (show && (!acknowledged || !enabled || !allowed))
					throw new InvalidDataException("An unready or opted-out companion occupied the battlefield.");
				if (show && host != CompanionHostState.Running && host != CompanionHostState.External)
					throw new InvalidDataException("A stopped or missing companion occupied the battlefield.");
				cases++;
			}

			foreach (var host in new[] { CompanionHostState.Running, CompanionHostState.External })
				if (!CompanionHudDisplay.IsVisible(host, true, true, true))
					throw new InvalidDataException("A working companion became inaccessible.");
			foreach (var viewport in new[] { 640, 800, 1024, 1280, 1920, 2560 })
			foreach (var pending in new[] { false, true })
			{
				var (x, width, height) = CompanionHudDisplay.Layout(viewport, pending);
				if (x < 16 || x + width > viewport - 250 - 16 || width > 540 || width < 300 || height < 60)
					throw new InvalidDataException("Adviser controls overlap the sidebar or leave the battlefield.");
				if (pending && height < 100)
					throw new InvalidDataException("Pending orders have no dedicated review row.");
			}
			const string unavailable = "AI ALERTS ONLY  •  AI GATEWAY NOT RUNNING";
			if (CompanionHudDisplay.Message("ready:normal", unavailable) != unavailable)
				throw new InvalidDataException("Model unavailability was hidden by a ready label.");
			Console.WriteLine($"COMPANION HUD PASS: {cases} availability cases; 12 viewport/action layouts; live enabled companions remain accessible; unavailable model warnings preserved.");
		}
	}
}
