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
using OpenRA.Mods.Common.Pathfinder;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;
using RLProto = OpenRA.Mods.RTSAI.RL;

namespace OpenRA.Mods.RTSAI.Traits
{
	/// <summary>
	/// Converts protobuf AgentAction commands into OpenRA Orders and queues them via IBot.
	/// </summary>
	public sealed class ActionHandler
	{
		readonly World world;
		readonly Player player;

		public ActionHandler(World world, Player player)
		{
			this.world = world;
			this.player = player;
		}

		public void ProcessAction(RLProto.AgentAction agentAction, IBot bot)
		{
			foreach (var command in agentAction.Commands)
			{
				var order = ConvertCommand(command);
				if (order != null)
					bot.QueueOrder(order);
			}
		}

		/// <summary>
		/// Convert a validated command into the same synchronized order used by
		/// bots and the normal player UI. Callers remain responsible for policy.
		/// </summary>
		public Order ConvertCommand(RLProto.Command cmd)
		{
			switch (cmd.Action)
			{
				case RLProto.ActionType.NoOp:
					return null;

				case RLProto.ActionType.Move:
					return CreateMoveOrder(cmd);

				case RLProto.ActionType.AttackMove:
					return CreateAttackMoveOrder(cmd);

				case RLProto.ActionType.Attack:
					return CreateAttackOrder(cmd);

				case RLProto.ActionType.Stop:
					return CreateStopOrder(cmd);

				case RLProto.ActionType.Harvest:
					return CreateHarvestOrder(cmd);

				case RLProto.ActionType.Build:
				case RLProto.ActionType.Train:
					return CreateProductionOrder(cmd);

				case RLProto.ActionType.Deploy:
					return CreateDeployOrder(cmd);

				case RLProto.ActionType.Sell:
					return CreateSellOrder(cmd);

				case RLProto.ActionType.Repair:
					return CreateRepairOrder(cmd);

				case RLProto.ActionType.PlaceBuilding:
					return CreatePlaceBuildingOrder(cmd);

				case RLProto.ActionType.CancelProduction:
					return CreateCancelProductionOrder(cmd);

				case RLProto.ActionType.SetRallyPoint:
					return CreateSetRallyPointOrder(cmd);

				case RLProto.ActionType.Guard:
					return CreateGuardOrder(cmd);

				case RLProto.ActionType.SetStance:
					return CreateSetStanceOrder(cmd);

				case RLProto.ActionType.EnterTransport:
					return CreateEnterTransportOrder(cmd);

				case RLProto.ActionType.Disguise:
					return CreateTargetedActorOrder(cmd, "Disguise");

				case RLProto.ActionType.Infiltrate:
					return CreateTargetedActorOrder(cmd, "Infiltrate");

				case RLProto.ActionType.Demolish:
					return CreateTargetedActorOrder(cmd, "C4");

				case RLProto.ActionType.Capture:
					return CreateTargetedActorOrder(cmd, "CaptureActor");

				case RLProto.ActionType.Unload:
					return CreateUnloadOrder(cmd);

				case RLProto.ActionType.PowerDown:
					return CreatePowerDownOrder(cmd);

				case RLProto.ActionType.SetPrimary:
					return CreateSetPrimaryOrder(cmd);

				case RLProto.ActionType.UseSupportPower:
					return CreateSupportPowerOrder(cmd);

				case RLProto.ActionType.Surrender:
					return new Order("Surrender", player.PlayerActor, false);

				case RLProto.ActionType.FastAdvance:
					// Handled by RTSAIExternalBotBridge directly (not an Order)
					return null;

				default:
					Log.Write(CompanionLog.Channel, $"Unknown action type: {cmd.Action}");
					return null;
			}
		}

		Order CreateMoveOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			var cell = new MPos(cmd.TargetX, cmd.TargetY).ToCPos(world.Map);
			var target = Target.FromCell(world, cell);

			return new Order("Move", subject, target, cmd.Queued);
		}

		Order CreateAttackMoveOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			var cell = new MPos(cmd.TargetX, cmd.TargetY).ToCPos(world.Map);
			var target = Target.FromCell(world, cell);

			return new Order("AttackMove", subject, target, cmd.Queued);
		}

		Order CreateAttackOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			if (cmd.TargetActorId != 0)
			{
				var targetActor = world.GetActorById(cmd.TargetActorId);
				if (targetActor == null || targetActor.IsDead || !targetActor.IsInWorld)
					return null;

				return new Order("Attack", subject, Target.FromActor(targetActor), cmd.Queued);
			}

			// Attack-ground at position
			var cell = new MPos(cmd.TargetX, cmd.TargetY).ToCPos(world.Map);
			return new Order("ForceAttack", subject, Target.FromCell(world, cell), cmd.Queued);
		}

		Order CreateStopOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			return new Order("Stop", subject, false);
		}

		Order CreateHarvestOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			if (cmd.TargetX != 0 || cmd.TargetY != 0)
			{
				var cell = new MPos(cmd.TargetX, cmd.TargetY).ToCPos(world.Map);
				return new Order("Harvest", subject, Target.FromCell(world, cell), cmd.Queued);
			}

			return new Order("Harvest", subject, cmd.Queued);
		}

		Order CreateProductionOrder(RLProto.Command cmd)
		{
			if (string.IsNullOrEmpty(cmd.ItemType))
			{
				Log.Write(CompanionLog.Channel, "Production command missing item_type");
				return null;
			}

			// Find a production structure that can build this item
			foreach (var actor in world.ActorsHavingTrait<ProductionQueue>())
			{
				if (actor.Owner != player || actor.IsDead || !actor.IsInWorld)
					continue;

				foreach (var queue in actor.TraitsImplementing<ProductionQueue>())
				{
					foreach (var buildable in queue.BuildableItems())
					{
						if (string.Equals(buildable.Name, cmd.ItemType, StringComparison.OrdinalIgnoreCase))
							return Order.StartProduction(actor, cmd.ItemType, 1, cmd.Queued);
					}
				}
			}

			Log.Write(CompanionLog.Channel, $"Cannot produce '{cmd.ItemType}': no capable production structure found");
			return null;
		}

		Order CreateDeployOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			// Deploy is a shared UI command, not a single engine order.  Aircraft
			// resolve it to ReturnToBase, transports to Unload, and transforming
			// units to DeployTransform.  Ask the actor's native traits for the same
			// order that the command bar would issue so companion actions preserve
			// those stock contracts.
			foreach (var deploy in subject.TraitsImplementing<IIssueDeployOrder>())
				if (deploy.CanIssueDeployOrder(subject, cmd.Queued))
					return deploy.IssueDeployOrder(subject, cmd.Queued);

			return null;
		}

		Order CreateSellOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			return new Order("Sell", subject, false) { IsImmediate = true };
		}

		Order CreateRepairOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			return new Order("RepairBuilding", player.PlayerActor, Target.FromActor(subject), false)
			{
				IsImmediate = true
			};
		}

		Order CreatePlaceBuildingOrder(RLProto.Command cmd)
		{
			if (string.IsNullOrEmpty(cmd.ItemType))
			{
				Log.Write(CompanionLog.Channel, "PlaceBuilding command missing item_type");
				return null;
			}

			// Find the production queue that has this building ready
			Actor producer = null;
			foreach (var actor in world.ActorsHavingTrait<ProductionQueue>())
			{
				if (actor.Owner != player || actor.IsDead || !actor.IsInWorld)
					continue;

				foreach (var queue in actor.TraitsImplementing<ProductionQueue>())
				{
					foreach (var item in queue.AllQueued())
					{
						if (item.Done && string.Equals(item.Item, cmd.ItemType, StringComparison.OrdinalIgnoreCase))
						{
							producer = actor;
							break;
						}
					}

					if (producer != null) break;
				}

				if (producer != null) break;
			}

			if (producer == null)
			{
				Log.Write(CompanionLog.Channel, $"Cannot place '{cmd.ItemType}': no completed building in any production queue");
				return null;
			}

			// Resolve building info for placement validation
			var actorInfo = world.Map.Rules.Actors[cmd.ItemType.ToLowerInvariant()];
			var bi = actorInfo.TraitInfoOrDefault<BuildingInfo>();

			// Try agent's requested position first
			var requestedCell = new MPos(cmd.TargetX, cmd.TargetY).ToCPos(world.Map);
			if (cmd.TargetX != 0 || cmd.TargetY != 0)
			{
				if (world.CanPlaceBuilding(requestedCell, actorInfo, bi, null)
					&& bi.IsCloseEnoughToBase(world, player, actorInfo, requestedCell))
				{
					Log.Write(CompanionLog.Channel, $"Placing '{cmd.ItemType}' at requested ({cmd.TargetX},{cmd.TargetY})");
					return MakePlaceOrder(cmd.ItemType, requestedCell, producer);
				}
			}

			// Auto-find: search outward from base center
			var baseCenter = GetBaseCenter();
			var foundCell = FindPlacementCell(actorInfo, bi, baseCenter);
			if (foundCell.HasValue)
			{
				Log.Write(CompanionLog.Channel, $"Auto-placed '{cmd.ItemType}' at ({foundCell.Value.X},{foundCell.Value.Y}) near base center ({baseCenter.X},{baseCenter.Y})");
				return MakePlaceOrder(cmd.ItemType, foundCell.Value, producer);
			}

			Log.Write(CompanionLog.Channel, $"Cannot place '{cmd.ItemType}': no valid cell found near base");
			return null;
		}

		Order MakePlaceOrder(string itemType, CPos cell, Actor producer)
		{
			return new Order("PlaceBuilding", player.PlayerActor,
				Target.FromCell(world, cell), false)
			{
				TargetString = itemType,
				ExtraData = producer.ActorID,
			};
		}

		CPos GetBaseCenter()
		{
			// Use Construction Yard location as base center
			foreach (var actor in world.ActorsHavingTrait<BaseProvider>())
			{
				if (actor.Owner == player && !actor.IsDead && actor.IsInWorld)
					return actor.Location;
			}

			// Fallback: first owned building
			foreach (var actor in world.ActorsHavingTrait<Building>())
			{
				if (actor.Owner == player && !actor.IsDead && actor.IsInWorld)
					return actor.Location;
			}

			return new MPos(world.Map.MapSize.Width / 2, world.Map.MapSize.Height / 2).ToCPos(world.Map);
		}

		CPos? FindPlacementCell(ActorInfo actorInfo, BuildingInfo bi, CPos center)
		{
			var resourceLayer = world.WorldActor.TraitOrDefault<IResourceLayer>();
			var resources = resourceLayer == null ? [] : world.Map.AllCells
				.Where(c => player.Shroud.IsExplored(c) && resourceLayer.GetResource(c).Type != null)
				.ToArray();
			var landLocomotors = world.WorldActor.TraitsImplementing<Locomotor>()
				.Where(l => l.Info.Name is "foot" or "wheeled" or "heavywheeled" or "lighttracked" or "tracked" or "heavytracked")
				.ToArray();
			var buildingInfluence = world.WorldActor.TraitOrDefault<BuildingInfluence>();
			var ownedBuildings = world.ActorsHavingTrait<Building>()
				.Where(a => a.Owner == player && !a.IsDead && a.IsInWorld)
				.ToArray();

			return world.Map.FindTilesInAnnulus(center, 0, 20)
				.Where(cell => world.CanPlaceBuilding(cell, actorInfo, bi, null)
					&& bi.IsCloseEnoughToBase(world, player, actorInfo, cell))
				.Select(cell => new
				{
					Cell = cell,
					Score = PlacementScore(actorInfo, bi, cell, center, resources, landLocomotors, buildingInfluence, ownedBuildings)
				})
				.OrderBy(candidate => candidate.Score)
				.ThenBy(candidate => (candidate.Cell - center).LengthSquared)
				.ThenBy(candidate => candidate.Cell.Y)
				.ThenBy(candidate => candidate.Cell.X)
				.Select(candidate => (CPos?)candidate.Cell)
				.FirstOrDefault();
		}

		long PlacementScore(
			ActorInfo actorInfo,
			BuildingInfo bi,
			CPos cell,
			CPos baseCenter,
			CPos[] resources,
			Locomotor[] landLocomotors,
			BuildingInfluence buildingInfluence,
			Actor[] ownedBuildings)
		{
			var score = (long)(cell - baseCenter).LengthSquared * 6;
			var occupied = bi.Tiles(cell).ToHashSet();

			// Keep a service lane around structures instead of packing every legal footprint together.
			for (var y = -1; y <= bi.Dimensions.Y; y++)
			{
				for (var x = -1; x <= bi.Dimensions.X; x++)
				{
					if (x >= 0 && x < bi.Dimensions.X && y >= 0 && y < bi.Dimensions.Y)
						continue;

					var border = cell + new CVec(x, y);
					score += IsOpenGround(border, occupied, landLocomotors, buildingInfluence) ? -12 : 90;
				}
			}

			// Avoid touching existing structures even when their decorative bibs make placement legal.
			foreach (var building in ownedBuildings)
			{
				var distance = (building.Location - cell).LengthSquared;
				if (distance <= 9)
					score += (10 - distance) * 180;
			}

			var exits = actorInfo.TraitInfos<ExitInfo>().OrderByDescending(exit => exit.Priority).ToArray();
			foreach (var exit in exits)
			{
				var exitCell = cell + exit.ExitCell;
				var centerX2 = bi.Dimensions.X - 1;
				var centerY2 = bi.Dimensions.Y - 1;
				var offsetX2 = exit.ExitCell.X * 2 - centerX2;
				var offsetY2 = exit.ExitCell.Y * 2 - centerY2;
				var direction = Math.Abs(offsetY2) >= Math.Abs(offsetX2)
					? new CVec(0, Math.Sign(offsetY2))
					: new CVec(Math.Sign(offsetX2), 0);
				if (direction == CVec.Zero)
					direction = new CVec(0, 1);
				var lateral = new CVec(-direction.Y, direction.X);

				// Reserve a three-cell-wide, six-cell-long lane beyond each production door.
				for (var distance = 1; distance <= 6; distance++)
				{
					for (var width = -1; width <= 1; width++)
					{
						var corridor = exitCell + distance * direction + width * lateral;
						score += IsOpenGround(corridor, occupied, landLocomotors, buildingInfluence) ? -35 : 650;
					}
				}

				// Prefer doors facing away from the Construction Yard so produced units leave the base cleanly.
				var outward = cell - baseCenter;
				var alignment = outward.X * direction.X + outward.Y * direction.Y;
				score -= alignment * 90;
			}

			if (actorInfo.HasTraitInfo<RefineryInfo>() && resources.Length > 0)
			{
				// Score from the refinery dock (bottom-center), not its top-left placement cell.
				var dock = cell + new CVec(bi.Dimensions.X / 2, bi.Dimensions.Y - 1);
				var nearest = resources
					.Select(resource => new { Cell = resource, Distance = (resource - dock).LengthSquared })
					.OrderBy(resource => resource.Distance)
					.First();
				score += (long)nearest.Distance * 160;

				// Reward dense nearby fields so harvesters spend more time carrying ore than commuting.
				var nearbyDensity = resources
					.Where(resource => (resource - dock).LengthSquared <= 144)
					.Sum(resource => world.WorldActor.Trait<IResourceLayer>().GetResource(resource).Density);
				score -= nearbyDensity * 18L;
			}

			return score;
		}

		bool IsOpenGround(CPos cell, HashSet<CPos> proposedFootprint, Locomotor[] locomotors, BuildingInfluence buildingInfluence)
		{
			if (!world.Map.Contains(cell) || proposedFootprint.Contains(cell))
				return false;

			if ((buildingInfluence != null && buildingInfluence.AnyBuildingAt(cell))
				|| world.ActorMap.GetActorsAt(cell).Any(actor => !actor.IsDead && actor.IsInWorld))
				return false;

			return locomotors.Length == 0 || locomotors.All(
				locomotor => locomotor.MovementCostForCell(cell) < PathGraph.MovementCostForUnreachableCell);
		}

		Order CreateCancelProductionOrder(RLProto.Command cmd)
		{
			if (string.IsNullOrEmpty(cmd.ItemType))
			{
				Log.Write(CompanionLog.Channel, "CancelProduction command missing item_type");
				return null;
			}

			// Find the production queue producing this item
			foreach (var actor in world.ActorsHavingTrait<ProductionQueue>())
			{
				if (actor.Owner != player || actor.IsDead || !actor.IsInWorld)
					continue;

				foreach (var queue in actor.TraitsImplementing<ProductionQueue>())
				{
					foreach (var item in queue.AllQueued())
					{
						if (string.Equals(item.Item, cmd.ItemType, StringComparison.OrdinalIgnoreCase))
							return Order.CancelProduction(actor, cmd.ItemType, 1);
					}
				}
			}

			Log.Write(CompanionLog.Channel, $"Cannot cancel '{cmd.ItemType}': not in any production queue");
			return null;
		}

		Order CreateSetRallyPointOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			var cell = new MPos(cmd.TargetX, cmd.TargetY).ToCPos(world.Map);
			return new Order("SetRallyPoint", subject, Target.FromCell(world, cell), false);
		}

		Order CreateGuardOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			var target = world.GetActorById(cmd.TargetActorId);
			if (target == null || target.IsDead || !target.IsInWorld)
				return null;

			return new Order("Guard", subject, Target.FromActor(target), cmd.Queued);
		}

		Order CreateSetStanceOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			// Stance encoded in target_x: 0=HoldFire, 1=ReturnFire, 2=Defend, 3=AttackAnything
			return new Order("SetUnitStance", subject, false)
			{
				ExtraData = (uint)Math.Clamp(cmd.TargetX, 0, 3)
			};
		}

		Order CreateEnterTransportOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			var target = world.GetActorById(cmd.TargetActorId);
			if (target == null || target.IsDead || !target.IsInWorld)
				return null;

			return new Order("EnterTransport", subject, Target.FromActor(target), cmd.Queued);
		}

		Order CreateTargetedActorOrder(RLProto.Command cmd, string orderId)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			var target = world.GetActorById(cmd.TargetActorId);
			if (target == null || target.IsDead || !target.IsInWorld)
				return null;

			return new Order(orderId, subject, Target.FromActor(target), cmd.Queued);
		}

		Order CreateUnloadOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			return new Order("Unload", subject, false);
		}

		Order CreatePowerDownOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			return new Order("PowerDown", subject, false);
		}

		Order CreateSetPrimaryOrder(RLProto.Command cmd)
		{
			var subject = world.GetActorById(cmd.ActorId);
			if (subject == null || subject.IsDead || !subject.IsInWorld)
				return null;

			return new Order("PrimaryProducer", subject, false);
		}

		Order CreateSupportPowerOrder(RLProto.Command cmd)
		{
			var manager = player.PlayerActor.TraitOrDefault<SupportPowerManager>();
			if (manager == null)
				return null;

			var power = manager.Powers.FirstOrDefault(pair =>
				pair.Key.Equals(cmd.ItemType, StringComparison.OrdinalIgnoreCase));
			if (string.IsNullOrEmpty(power.Key) || !power.Value.Ready)
				return null;

			return new Order(power.Key, player.PlayerActor,
				Target.FromCell(world, new MPos(cmd.TargetX, cmd.TargetY).ToCPos(world.Map)), false)
			{
				SuppressVisualFeedback = true,
				ExtraData = uint.MaxValue
			};
		}
	}
}
