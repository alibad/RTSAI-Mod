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
using System.Threading.Tasks;
using Grpc.Core;
using RLProto = OpenRA.Mods.RTSAI.RL;

namespace OpenRA.Mods.RTSAI.Traits
{
	/// <summary>
	/// gRPC service for the in-game AI companion. It implements only the companion RPCs that
	/// the product's Python client (OpenRA-AI services/companion bridge.py) uses during a match:
	/// Observe, GetState, UpdateCompanionStatus, UpdateCompanionThreat, CaptureCompanionFrame
	/// and ExecuteCompanionActions.
	///
	/// RL seam: the shared rl_bridge.proto also declares the RL/evaluation RPCs (GameSession,
	/// FastAdvance, CreateSession, DestroySession). They depend on engine fast-forward and
	/// multi-session hosting, which the slim RTS AI engine does not carry, so they are deliberately
	/// not overridden here and answer UNIMPLEMENTED. An RL host can subclass this service (or
	/// register a second service) and override them without touching the companion path.
	/// </summary>
	public class CompanionService : RLProto.RLBridge.RLBridgeBase
	{
		public override Task<RLProto.GameState> GetState(RLProto.StateRequest request, ServerCallContext context)
		{
			if (!string.IsNullOrEmpty(request.SessionId))
				throw new RpcException(new Status(StatusCode.Unimplemented, "Session-scoped state is an RL-host feature."));

			if (CompanionBridge.TryGetState(out var state))
				return Task.FromResult(state);

			return Task.FromResult(new RLProto.GameState { Phase = "no_match" });
		}

		/// <summary>
		/// Read the latest companion observation without changing game speed,
		/// issuing an order, or revealing information hidden by fog of war.
		/// </summary>
		public override Task<RLProto.GameObservation> Observe(RLProto.StateRequest request, ServerCallContext context)
		{
			if (!string.IsNullOrEmpty(request.SessionId))
				throw new RpcException(new Status(StatusCode.Unimplemented, "Session-scoped observation is an RL-host feature."));

			if (CompanionBridge.TryGetObservation(out var observation))
				return Task.FromResult(observation);

			if (CompanionBridge.IsDisabledForMatch)
				throw new RpcException(new Status(StatusCode.FailedPrecondition, CompanionBridge.DisabledForMatchMessage + "."));

			throw new RpcException(new Status(StatusCode.Unavailable,
				"No local companion observation is available. Start a match with OPENRA_AI_COMPANION=1."));
		}

		public override Task<RLProto.CompanionStatusAck> UpdateCompanionStatus(RLProto.CompanionStatus request, ServerCallContext context)
		{
			return Task.FromResult(new RLProto.CompanionStatusAck { Accepted = CompanionBridge.UpdateStatus(request) });
		}

		public override Task<RLProto.CompanionStatusAck> UpdateCompanionThreat(RLProto.CompanionThreat request, ServerCallContext context)
		{
			return Task.FromResult(new RLProto.CompanionStatusAck { Accepted = CompanionBridge.UpdateThreat(request) });
		}

		/// <summary>Capture the player's current rendered viewport for an on-demand vision request.</summary>
		public override async Task<RLProto.CompanionFrame> CaptureCompanionFrame(RLProto.StateRequest request, ServerCallContext context)
		{
			try
			{
				return await CompanionBridge.CaptureFrame(context.CancellationToken);
			}
			catch (InvalidOperationException e)
			{
				Log.Write(CompanionLog.Channel, $"CaptureCompanionFrame failed: {e}");
				throw new RpcException(new Status(StatusCode.FailedPrecondition, e.Message));
			}
			catch (Exception e) when (e is not RpcException and not OperationCanceledException)
			{
				Log.Write(CompanionLog.Channel, $"CaptureCompanionFrame failed: {e}");
				throw new RpcException(new Status(StatusCode.Internal, e.Message));
			}
		}

		/// <summary>Queue an explicitly confirmed, allowlisted action for validation on the game thread.</summary>
		public override async Task<RLProto.CompanionActionReceipt> ExecuteCompanionActions(RLProto.CompanionActionRequest request, ServerCallContext context)
		{
			return await CompanionBridge.ExecuteActions(request).WaitAsync(context.CancellationToken);
		}
	}
}
