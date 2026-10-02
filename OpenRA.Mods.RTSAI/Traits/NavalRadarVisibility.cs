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

using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	// Moved from the alibad/OpenRA fork's Mods.Common (Traits/NavalSystems.cs) with the Saudi Arabia and
	// Yemen fleets: radar-emitting ships and missile boats stay visible in explored enemy fog.
	[Desc("Uses normal fog visibility while passive, but reveals an emitting actor in explored enemy fog.")]
	public class NavalRadarVisibilityInfo : ConditionalTraitInfo, IDefaultVisibilityInfo
	{
		[Desc("Relationships that always see the actor.")]
		public readonly PlayerRelationship AlwaysVisibleRelationships = PlayerRelationship.Ally;

		public override object Create(ActorInitializer init) { return new NavalRadarVisibility(this); }
	}

	public class NavalRadarVisibility : ConditionalTrait<NavalRadarVisibilityInfo>, IDefaultVisibility
	{
		public NavalRadarVisibility(NavalRadarVisibilityInfo info)
			: base(info) { }

		bool IDefaultVisibility.IsVisible(Actor self, Player viewer)
		{
			if (viewer == null)
				return true;

			var relationship = self.Owner.RelationshipWith(viewer);
			if (Info.AlwaysVisibleRelationships.HasRelationship(relationship))
				return true;

			if (!viewer.Shroud.IsExplored(self.CenterPosition))
				return false;

			return !IsTraitDisabled || viewer.Shroud.IsVisible(self.CenterPosition);
		}
	}
}
