using System;
using System.Linq;
using OpenRA.Mods.RTSAI.Library;

namespace OpenRA.Mods.RTSAI.UtilityCommands
{
	public sealed class CommunityInstallCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--community-install";
		bool IUtilityCommand.ValidateArguments(string[] args) => args.Length is 2 or 3;
		[Desc("ID [ZIP]", "Install a pinned official community game into isolated local storage.")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			var release = CommunityInstall.Releases.Single(r => r.Id == args[1]);
			var install = new CommunityInstall();
			install.InstallAsync(release, args.Length == 3 ? args[2] : null).GetAwaiter().GetResult();
			Console.WriteLine(install.Status);
			if (CommunityInstall.InstalledExecutable(release) == null) Environment.Exit(1);
		}
	}
}
