#region Copyright & License Information
/*
 * Copyright (c) The OpenRA Developers and Contributors
 * This file is part of OpenRA, which is free software. It is made
 * available to you under the terms of the GNU General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version. For more
 * information, see COPYING.
 */
#endregion

using System;
using System.Collections.Generic;
using OpenRA.Mods.Common.Experience;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RA2.Traits
{
	[Desc("This actor can mind control other actors.")]
	public class MindControllerInfo : PausableConditionalTraitInfo, Requires<ArmamentInfo>, Requires<HealthInfo>
	{
		[Desc("Name of the armaments that grant this condition.")]
		public readonly HashSet<string> ArmamentNames = new() { "primary" };

		[Desc("Up to how many units can this unit control?",
			"Use 0 or negative numbers for infinite.")]
		public readonly int Capacity = 1;

		[Desc("If the capacity is reached, discard the oldest mind controlled unit and control the new one",
			"If false, controlling new units is forbidden after capacity is reached.")]
		public readonly bool DiscardOldest = true;

		[Desc("Condition to grant to self when controlling actors. Can stack up by the number of enslaved actors. You can use this to forbid firing of the dummy MC weapon.")]
		[GrantedConditionReference]
		[FieldLoader.Require]
		public readonly string ControllingCondition = null;

		[Desc("The sound played when the unit is mindcontrolled.")]
		public readonly string[] Sounds = Array.Empty<string>();

		public override object Create(ActorInitializer init) { return new MindController(this); }
	}

	public class MindController : PausableConditionalTrait<MindControllerInfo>, INotifyAttack, INotifyKilled, INotifyActorDisposing
	{
		readonly List<Actor> slaves = new();

		readonly Stack<int> controllingTokens = new();

		public IEnumerable<Actor> Slaves => slaves;

		// FORK: capacity follows the mind-control-and-disguise experience component when the
		// player has tuned it, and falls back to the actor's own yaml value otherwise. Without
		// this the component's Control capacity slider would silently stop governing anything
		// once real RA2 mind control replaced the placeholder MindControlCapacity ledger.
		readonly int capacity;

		public MindController(MindControllerInfo info)
			: base(info)
		{
			var catalog = Game.ModData.GetOrNull<ExperienceCatalog>();
			capacity = catalog?.GetIntegerParameter("mind-control-and-disguise", "capacity", info.Capacity) ?? info.Capacity;
		}

		void StackControllingCondition(Actor self, string condition)
		{
			if (string.IsNullOrEmpty(condition))
				return;

			controllingTokens.Push(self.GrantCondition(condition));
		}

		void UnstackControllingCondition(Actor self, string condition)
		{
			if (string.IsNullOrEmpty(condition))
				return;

			self.RevokeCondition(controllingTokens.Pop());
		}

		public void UnlinkSlave(Actor self, Actor slave)
		{
			if (slaves.Contains(slave))
			{
				slaves.Remove(slave);
				UnstackControllingCondition(self, Info.ControllingCondition);
			}
		}

		void INotifyAttack.PreparingAttack(Actor self, in Target target, Armament a, Barrel barrel) { }

		void INotifyAttack.Attacking(Actor self, in Target target, Armament a, Barrel barrel)
		{
			if (IsTraitDisabled || IsTraitPaused)
				return;

			if (!Info.ArmamentNames.Contains(a.Info.Name))
				return;

			if (target.Actor == null || !target.IsValidFor(self))
				return;

			if (self.Owner.RelationshipWith(target.Actor.Owner) == PlayerRelationship.Ally)
				return;

			var mindControllable = target.Actor.TraitOrDefault<MindControllable>();

			// FORK: upstream throws here. This mod fuses mind control into rosters that the
			// upstream ra2 mod never saw, so a controller can legitimately be pointed at an actor
			// that was never given MindControllable. Log it and decline the shot rather than
			// killing the game: a missing trait is a rules bug, not a reason to crash a match.
			if (mindControllable == null)
			{
				Log.Write("debug",
					$"`{self.Info.Name}` tried to mindcontrol `{target.Actor.Info.Name}`, which has no MindControllable trait.");
				return;
			}

			if (mindControllable.IsTraitDisabled || mindControllable.IsTraitPaused)
				return;

			if (capacity > 0 && !Info.DiscardOldest && slaves.Count >= capacity)
				return;

			slaves.Add(target.Actor);
			StackControllingCondition(self, Info.ControllingCondition);
			mindControllable.LinkMaster(target.Actor, self);

			if (Info.Sounds.Length != 0)
				Game.Sound.Play(SoundType.World, Info.Sounds.Random(self.World.SharedRandom), self.CenterPosition);

			if (capacity > 0 && Info.DiscardOldest && slaves.Count > capacity)
				slaves[0].Trait<MindControllable>().RevokeMindControl(slaves[0]);
		}

		void ReleaseSlaves(Actor self)
		{
			foreach (var s in slaves)
			{
				if (s.IsDead || s.Disposed)
					continue;

				s.Trait<MindControllable>().RevokeMindControl(s);
			}

			slaves.Clear();
			while (controllingTokens.Count != 0)
				UnstackControllingCondition(self, Info.ControllingCondition);
		}

		void INotifyKilled.Killed(Actor self, AttackInfo e)
		{
			ReleaseSlaves(self);
		}

		void INotifyActorDisposing.Disposing(Actor self)
		{
			ReleaseSlaves(self);
		}

		protected override void TraitDisabled(Actor self)
		{
			ReleaseSlaves(self);
		}
	}
}
