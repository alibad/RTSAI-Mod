using System.Linq;
using OpenRA.Mods.RTSAI.Library;

namespace OpenRA.Mods.RTSAI.UtilityCommands
{
	public sealed class CommunityLaunchCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--community-launch";
		bool IUtilityCommand.ValidateArguments(string[] args) => args.Length == 2;
		[Desc("ID", "Open an installed community game with its own compatible runtime and local settings.")]
		void IUtilityCommand.Run(Utility utility, string[] args) =>
			CommunityInstall.Launch(CommunityInstall.Releases.Single(r => r.Id == args[1]));
	}
}
