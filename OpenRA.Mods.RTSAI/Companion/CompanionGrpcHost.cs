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
using System.IO;
using System.Runtime.CompilerServices;
using System.Threading;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace OpenRA.Mods.RTSAI.Traits
{
	/// <summary>
	/// Hosts the companion gRPC service on loopback, once per process. The server outlives
	/// individual matches and serves whichever CompanionBridge is current.
	///
	/// Startup is guarded: Kestrel lives in the Microsoft.AspNetCore.App shared framework, which only
	/// the host process can provide (the engine launchers reference it). If it is missing - an older
	/// engine, a trimmed package - the bridge is disabled with a log line instead of the JIT failure
	/// escaping a background thread and terminating the game.
	/// </summary>
	public static class CompanionGrpcHost
	{
		static readonly object StateLock = new();
		static bool started;

		/// <summary>Null until startup completes or fails; then whether the server is running.</summary>
		public static bool? Available { get; private set; }

		public static string UnavailableReason { get; private set; } = "";

		public static void Start(int port)
		{
			lock (StateLock)
			{
				if (started)
					return;

				started = true;
			}

			var thread = new Thread(() => Run(port))
			{
				IsBackground = true,
				Name = "RTSAI-Companion-gRPC"
			};
			thread.Start();
		}

		static void Run(int port)
		{
			try
			{
				// Everything that touches ASP.NET Core types is in RunServer, which is never inlined,
				// so a missing framework surfaces as a catchable exception at this call site.
				RunServer(port);
			}
			catch (Exception e) when (e is FileNotFoundException or FileLoadException or TypeLoadException or BadImageFormatException)
			{
				Disable($"ASP.NET Core is not available to this process ({e.GetType().Name}: {e.Message}). " +
					"The engine launcher must reference Microsoft.AspNetCore.App.");
			}
			catch (Exception e)
			{
				Disable($"gRPC server failed: {e}");
			}
		}

		static void Disable(string reason)
		{
			UnavailableReason = reason;
			Available = false;
			Log.Write(CompanionLog.Channel, "Companion bridge disabled: " + reason);
			lock (StateLock)
				started = false;
		}

		[MethodImpl(MethodImplOptions.NoInlining)]
		static void RunServer(int port)
		{
			var builder = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
			builder.WebHost.ConfigureKestrel(options =>
			{
				// Local companion endpoint, not a LAN service; loopback also avoids firewall prompts.
				options.ListenLocalhost(port, listen => listen.Protocols = HttpProtocols.Http2);
			});

			builder.Services.AddGrpc();
			builder.Logging.ClearProviders();

			var app = builder.Build();
			app.MapGrpcService<CompanionService>();

			Log.Write(CompanionLog.Channel, $"gRPC server starting on 127.0.0.1:{port}");
			Log.Write(CompanionLog.Channel, $"Kestrel: {typeof(WebApplication).Assembly.Location}");
			Log.Write(CompanionLog.Channel, $"Grpc.AspNetCore.Server: {typeof(Grpc.AspNetCore.Server.GrpcServiceOptions).Assembly.Location}");
			Available = true;
			app.Run();
		}
	}

	public static class CompanionLog
	{
		public const string Channel = "companion";

		/// <summary>Idempotent; the engine does not register a companion channel.</summary>
		public static void Ensure()
		{
			Log.AddChannel(Channel, "companion.log");
		}
	}
}
