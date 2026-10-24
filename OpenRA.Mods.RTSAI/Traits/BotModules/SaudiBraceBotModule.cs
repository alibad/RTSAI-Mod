using System.Linq;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("Saudi bots brace stationary Guards that are aiming at a target, using the ordinary deploy order.")]
	public class SaudiBraceBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int ScanInterval = 50;
		public override object Create(ActorInitializer init) => new SaudiBraceBotModule(init.Self, this);
	}

	public class SaudiBraceBotModule : ConditionalTrait<SaudiBraceBotModuleInfo>, IBotTick
	{
		readonly Actor self;
		int scan;
		public int OrdersIssued { get; private set; }

		public SaudiBraceBotModule(Actor self, SaudiBraceBotModuleInfo info) : base(info) { this.self = self; }

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || self.Owner.Faction.InternalName != "saudi" || --scan > 0)
				return;
			scan = Info.ScanInterval;
			foreach (var guard in self.World.Actors.Where(a => a.Owner == self.Owner && a.Info.Name == "r2sang" && a.IsInWorld && !a.IsDead))
			{
				var deploy = guard.TraitOrDefault<GrantConditionOnDeploy>();
				var move = guard.TraitOrDefault<Mobile>();
				if (deploy == null || deploy.DeployState != DeployState.Undeployed || move == null ||
					move.CurrentMovementTypes != MovementType.None || !guard.TraitsImplementing<AttackBase>().Any(a => a.IsAiming))
					continue;
				var issue = (IIssueDeployOrder)deploy;
				if (!issue.CanIssueDeployOrder(guard, false))
					continue;
				bot.QueueOrder(issue.IssueDeployOrder(guard, false));
				OrdersIssued++;
				DoctrineLog.Write(self.Owner, $"brace {guard.ActorID}");
			}
		}
	}
}
