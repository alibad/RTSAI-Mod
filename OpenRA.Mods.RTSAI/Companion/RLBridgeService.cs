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
using System.Linq;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;
using Grpc.Core;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using RLProto = OpenRA.Mods.RTSAI.RL;

namespace OpenRA.Mods.RTSAI.Traits
{
	/// <summary>
	/// gRPC service implementation for the RL Bridge.
	/// Routes RPCs to the correct RTSAIExternalBotBridge session via session_id.
	/// In single-session (legacy) mode, session_id can be empty.
	/// </summary>
	public sealed class RLBridgeService : RLProto.RLBridge.RLBridgeBase
	{
		/// <summary>
		/// Wait for a bridge to become available and activated.
		/// In multi-session mode with session_id, looks up immediately.
		/// In single-session mode, polls until the bridge activates (up to 60s).
		/// </summary>
		static async Task<RTSAIExternalBotBridge> WaitForBridge(string sessionId, CancellationToken ct)
		{
			// In multi-session mode with a specific session_id, look up directly
			if (!string.IsNullOrEmpty(sessionId))
			{
				// Session should already exist (created by CreateSession RPC)
				// CreateSession now blocks until ready, but keep a generous timeout
				for (var i = 0; i < 3000; i++)
				{
					var b = RTSAIExternalBotBridge.LookupSession(sessionId);
					if (b != null && b.IsEnabled)
						return b;

					await Task.Delay(100, ct);
				}

				return null;
			}

			// Legacy single-session mode: wait for any bridge to activate
			for (var i = 0; i < 600; i++)
			{
				var bridge = RTSAIExternalBotBridge.LookupSession("");
				if (bridge != null && bridge.IsEnabled)
					return bridge;

				await Task.Delay(100, ct);
			}

			return null;
		}

		/// <summary>
		/// Bidirectional streaming: game sends observations, agent sends actions.
		/// </summary>
		public override async Task GameSession(
			IAsyncStreamReader<RLProto.AgentAction> requestStream,
			IServerStreamWriter<RLProto.GameObservation> responseStream,
			ServerCallContext context)
		{
			// For streaming, we don't have session_id upfront — use legacy lookup
			var bridge = await WaitForBridge("", context.CancellationToken);

			if (bridge == null)
			{
				Log.Write("rl-bridge", "GameSession rejected: bridge not activated within 60s timeout");
				return;
			}

			bridge.OnAgentConnected();
			Log.Write("rl-bridge", $"GameSession started for session {bridge.SessionId}");

			var ct = context.CancellationToken;

			try
			{
				// Observation sender: game → agent (runs independently)
				var obsTask = Task.Run(async () =>
				{
					try
					{
						while (!ct.IsCancellationRequested)
						{
							var obs = await bridge.ObservationReader.ReadAsync(ct);
							await responseStream.WriteAsync(obs, ct);
							if (obs.Done)
							{
								Log.Write("rl-bridge", $"Game over: {obs.Result}");
								break;
							}
						}
					}
					catch (OperationCanceledException) { }
					catch (ChannelClosedException) { }
				}, ct);

				// Action receiver: agent → game (runs independently)
				var actionTask = Task.Run(async () =>
				{
					try
					{
						while (await requestStream.MoveNext(ct))
							await bridge.ActionWriter.WriteAsync(requestStream.Current, ct);
					}
					catch (OperationCanceledException) { }
					catch (ChannelClosedException) { }
				}, ct);

				// Exit when either loop ends (game over, disconnect, or cancel)
				await Task.WhenAny(obsTask, actionTask);
			}
			finally
			{
				bridge.OnAgentDisconnected();
				Log.Write("rl-bridge", "GameSession ended");
			}
		}

		/// <summary>
		/// Unary RPC: advance N ticks with optional commands, return observation.
		/// Routes to the correct session via request.SessionId.
		/// </summary>
		public override async Task<RLProto.GameObservation> FastAdvance(
			RLProto.FastAdvanceRequest request,
			ServerCallContext context)
		{
			try
			{
				var bridge = await WaitForBridge(request.SessionId, context.CancellationToken);

				if (bridge == null)
					throw new RpcException(new Status(StatusCode.Unavailable,
						$"Bridge not activated within 300s (session_id={request.SessionId})"));

				return await bridge.RequestFastAdvance(
					request.Ticks, request.Commands, context.CancellationToken,
					request.CheckEventsEvery,
					request.EnabledInterrupts.Count > 0 ? request.EnabledInterrupts : null);
			}
			catch (RpcException)
			{
				throw;
			}
			catch (Exception e)
			{
				Log.Write("rl-bridge", $"FastAdvance error for session {request.SessionId}: {e}");
				throw;
			}
		}

		/// <summary>
		/// Unary RPC: query current game state on demand.
		/// </summary>
		public override Task<RLProto.GameState> GetState(
			RLProto.StateRequest request,
			ServerCallContext context)
		{
			if (string.IsNullOrEmpty(request.SessionId) && RTSAICompanionBridge.TryGetState(out var companionState))
				return Task.FromResult(companionState);

			var bridge = RTSAIExternalBotBridge.LookupSession(request.SessionId);
			if (bridge == null)
			{
				return Task.FromResult(new RLProto.GameState
				{
					Phase = "no_bridge"
				});
			}

			return Task.FromResult(bridge.GetCurrentState());
		}

		/// <summary>
		/// Read the latest companion observation without changing game speed,
		/// issuing an order, or revealing information hidden by fog of war.
		/// </summary>
		public override Task<RLProto.GameObservation> Observe(
			RLProto.StateRequest request,
			ServerCallContext context)
		{
			if (!string.IsNullOrEmpty(request.SessionId))
			{
				var bridge = RTSAIExternalBotBridge.LookupSession(request.SessionId);
				if (bridge == null || !RLSessionManager.SessionStates.TryGetValue(request.SessionId, out var state))
					throw new RpcException(new Status(StatusCode.NotFound,
						$"Session {request.SessionId} is not available."));

				state.TickLock.Wait(context.CancellationToken);
				try
				{
					return Task.FromResult(bridge.GetCurrentObservation());
				}
				finally
				{
					state.TickLock.Release();
				}
			}

			if (RTSAICompanionBridge.TryGetObservation(out var observation))
				return Task.FromResult(observation);

			throw new RpcException(new Status(StatusCode.Unavailable,
				"No local companion observation is available. Start OpenRA with OPENRA_AI_COMPANION=1."));
		}

		/// <summary>
		/// Publish the companion lifecycle state for the unobtrusive in-game HUD.
		/// </summary>
		public override Task<RLProto.CompanionStatusAck> UpdateCompanionStatus(
			RLProto.CompanionStatus request,
			ServerCallContext context)
		{
			return Task.FromResult(new RLProto.CompanionStatusAck
			{
				Accepted = RTSAICompanionBridge.UpdateStatus(request)
			});
		}

		/// <summary>
		/// Publish the latest fog-respecting threat assessment without refreshing HUD text.
		/// </summary>
		public override Task<RLProto.CompanionStatusAck> UpdateCompanionThreat(
			RLProto.CompanionThreat request,
			ServerCallContext context)
		{
			return Task.FromResult(new RLProto.CompanionStatusAck
			{
				Accepted = RTSAICompanionBridge.UpdateThreat(request)
			});
		}

		/// <summary>
		/// Capture the player's current rendered viewport for an on-demand vision request.
		/// </summary>
		public override async Task<RLProto.CompanionFrame> CaptureCompanionFrame(
			RLProto.StateRequest request,
			ServerCallContext context)
		{
			try
			{
				return await RTSAICompanionBridge.CaptureFrame(context.CancellationToken);
			}
			catch (InvalidOperationException e)
			{
				Log.Write("rl-bridge", $"CaptureCompanionFrame failed: {e}");
				throw new RpcException(new Status(StatusCode.FailedPrecondition, e.Message));
			}
			catch (Exception e) when (e is not RpcException and not OperationCanceledException)
			{
				Log.Write("rl-bridge", $"CaptureCompanionFrame failed: {e}");
				throw new RpcException(new Status(StatusCode.Internal, e.Message));
			}
		}

		/// <summary>
		/// Queue an explicitly confirmed, allowlisted action for validation and
		/// execution on the game thread.
		/// </summary>
		public override async Task<RLProto.CompanionActionReceipt> ExecuteCompanionActions(
			RLProto.CompanionActionRequest request,
			ServerCallContext context)
		{
			return await RTSAICompanionBridge.ExecuteActions(request).WaitAsync(context.CancellationToken);
		}

		/// <summary>
		/// Create a new game session. Only available in multi-session mode.
		/// </summary>
		public override Task<RLProto.CreateSessionResponse> CreateSession(
			RLProto.CreateSessionRequest request,
			ServerCallContext context)
		{
			if (!RTSAIExternalBotBridge.MultiSessionMode)
				throw new RpcException(new Status(StatusCode.Unimplemented,
					"CreateSession is only available in multi-session mode"));

			var sessionId = RLSessionManager.CreateSession(
				request.MapName, request.Bots, request.Seed);

			return Task.FromResult(new RLProto.CreateSessionResponse
			{
				SessionId = sessionId
			});
		}

		/// <summary>
		/// Destroy a game session. Only available in multi-session mode.
		/// </summary>
		public override Task<RLProto.DestroySessionResponse> DestroySession(
			RLProto.DestroySessionRequest request,
			ServerCallContext context)
		{
			if (!RTSAIExternalBotBridge.MultiSessionMode)
				throw new RpcException(new Status(StatusCode.Unimplemented,
					"DestroySession is only available in multi-session mode"));

			// Destroy is best-effort — never fail the RPC
			try { RLSessionManager.DestroySession(request.SessionId); }
			catch (Exception e) { Log.Write("rl-bridge", $"DestroySession error: {e}"); }

			return Task.FromResult(new RLProto.DestroySessionResponse());
		}
	}
}
