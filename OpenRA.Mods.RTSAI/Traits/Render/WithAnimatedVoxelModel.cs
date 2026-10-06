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
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Mods.Cnc.Traits.Render;
using OpenRA.Mods.Common.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits.Render
{
	// Art-preview branch (RTSAI vehicle animation pass): WithVoxelTurret and WithVoxelBody always draw HVA frame 0,
	// so a radar dish modelled as its own voxel section with N rotation frames (tools/glb_voxel.py "spin" parts)
	// cannot turn. This draws such a model attached to the body or to a turret and cycles its HVA frames.
	// While the trait is disabled by its condition (for example a radar that only sweeps when deployed) the model
	// stays visible on its current frame instead of disappearing.
	[Desc("Renders a voxel model attached to the body or a turret and cycles its HVA frames (a spinning radar).")]
	public class WithAnimatedVoxelModelInfo : ConditionalTraitInfo, IRenderActorPreviewVoxelsInfo, Requires<RenderVoxelsInfo>
	{
		[Desc("Voxel sequence name to use.")]
		public readonly string Sequence = "radar";

		[Desc("Turreted 'Turret' key to attach to. Empty attaches the model to the body.")]
		public readonly string Turret = "";

		[Desc("Ticks per HVA frame.")]
		public readonly int TickRate = 2;

		[Desc("Defines if the voxel should have a shadow.")]
		public readonly bool ShowShadow = true;

		public override object Create(ActorInitializer init) { return new WithAnimatedVoxelModel(init.Self, this); }

		public IEnumerable<ModelAnimation> RenderPreviewVoxels(IModelCache cache,
			ActorPreviewInitializer init, RenderVoxelsInfo rv, string image, Func<WRot> orientation, int facings, PaletteReference p)
		{
			var model = cache.GetModelSequence(image, Sequence);
			if (string.IsNullOrEmpty(Turret))
			{
				var body = init.Actor.TraitInfo<BodyOrientationInfo>();
				yield return new ModelAnimation(model, () => WVec.Zero,
					() => body.QuantizeOrientation(orientation(), facings), () => false, () => 0, ShowShadow);
				yield break;
			}

			var t = init.Actor.TraitInfos<TurretedInfo>().First(tt => tt.Turret == Turret);
			yield return new ModelAnimation(model, t.PreviewPosition(init, orientation),
				t.PreviewOrientation(init, orientation, facings), () => false, () => 0, ShowShadow);
		}
	}

	public class WithAnimatedVoxelModel : ConditionalTrait<WithAnimatedVoxelModelInfo>, ITick
	{
		readonly uint frames;
		uint tick, frame;

		public WithAnimatedVoxelModel(Actor self, WithAnimatedVoxelModelInfo info)
			: base(info)
		{
			var rv = self.Trait<RenderVoxels>();
			var model = rv.Renderer.ModelCache.GetModelSequence(rv.Image, info.Sequence);
			frames = model.Frames;

			Func<WVec> offset;
			Func<WRot> orientation;
			if (string.IsNullOrEmpty(info.Turret))
			{
				var body = self.Trait<BodyOrientation>();
				offset = () => WVec.Zero;
				orientation = () => body.QuantizeOrientation(self.Orientation);
			}
			else
			{
				var turreted = self.TraitsImplementing<Turreted>().First(tt => tt.Name == info.Turret);
				offset = () => turreted.Position(self);
				orientation = () => turreted.WorldOrientation;
			}

			rv.Add(new ModelAnimation(model, offset, orientation, () => false, () => frame, info.ShowShadow));
		}

		void ITick.Tick(Actor self)
		{
			if (IsTraitDisabled || frames < 2)
				return;

			if (++tick < Info.TickRate)
				return;

			tick = 0;
			if (++frame >= frames)
				frame = 0;
		}
	}
}
