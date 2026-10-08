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
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using OpenRA.Mods.RTSAI.Traits;
using OpenRA.Support;

namespace OpenRA.Mods.RTSAI.Companion
{
	public enum CompanionHostState
	{
		/// <summary>The host has not been initialized (utility commands, the content installer).</summary>
		NotStarted,

		/// <summary>A launcher or test tool runs the companion itself (OPENRA_AI_COMPANION=1).</summary>
		External,

		/// <summary>The player chose "Off", or this is a headless run.</summary>
		Off,

		/// <summary>The companion files are not installed next to the game.</summary>
		Missing,
		Starting,
		Running,
		Restarting,

		/// <summary>The sidecar exited repeatedly; the game keeps running without it.</summary>
		Failed
	}

	/// <summary>Settings for the External mode, passed once to the companion's DPAPI-protected provider config.</summary>
	public sealed class ExternalAISettings
	{
		public string Endpoint = "";
		public string Model = "";
		public string ApiKey = "";
	}

	/// <summary>
	/// Starts the AI companion sidecar when the game starts and stops it when the game exits.
	///
	/// The sidecar is the frozen companion from OpenRA-AI (companion/rtsai-companion.exe). It runs
	/// without a console window, logs to {SupportDir}/Logs and keeps its settings, provider config
	/// and hosted-AI install token in {SupportDir}/ai-companion. Loopback ports are chosen per launch.
	/// If the files are missing or the process keeps crashing, the game carries on and the HUD says so.
	/// </summary>
	public static class CompanionHost
	{
		public const string ModeHosted = "hosted";
		public const string ModeLocal = "local";
		public const string ModeExternal = "external";
		public const string ModeOff = "off";
		public static readonly IReadOnlyList<string> Modes = [ModeHosted, ModeLocal, ModeExternal, ModeOff];

		const int MaxRestarts = 3;
		const string ExecutableName = "rtsai-companion.exe";
		const string InstallChoiceFile = "rtsai-install.json";
		const string HostSettingsFile = "host.json";
		const string NotIncluded = "This build does not include the AI co-commander.";
		const string NotIncludedHud = "AI CO-COMMANDER NOT INCLUDED IN THIS BUILD  •  GAME UNAFFECTED";

		static readonly object Sync = new();
		static readonly Lazy<bool> Bundled = new(() =>
			ResolveSidecar() != null || Directory.Exists(Path.Combine(Platform.EngineDir, "companion")));
		static Process process;
		static CompanionProcessJob job;
		static StreamWriter outputLog;
		static StreamWriter errorLog;
		static bool stopping;
		static bool exitHandlerRegistered;
		static int restarts;
		static int generation;
		static string modVersion = "dev";
		static Sidecar sidecar;
		static Ports ports;

		public static CompanionHostState State { get; private set; } = CompanionHostState.NotStarted;
		public static string Mode { get; private set; } = ModeHosted;
		public static string Detail { get; private set; } = "";

		/// <summary>Percent of the voice pack downloaded so far, or -1 when no download is running.</summary>
		public static int VoicePackProgress { get; private set; } = -1;
		public static bool VoiceReady { get; private set; }

		/// <summary>True when the game owns the companion lifecycle (any state except off, external or not started).</summary>
		public static bool Managed => State is CompanionHostState.Missing or CompanionHostState.Starting
			or CompanionHostState.Running or CompanionHostState.Restarting or CompanionHostState.Failed;

		public static string DataDirectory => Path.Combine(Platform.SupportDir, "ai-companion");
		public static string LogDirectory => Path.Combine(Platform.SupportDir, "Logs");

		/// <summary>
		/// The sidecar's TEMP. The speech stack copies espeak-ng.dll into a fresh temp folder per
		/// process and cannot delete it while loaded, so the host gives it a private folder and
		/// empties it before each start and after shutdown.
		/// </summary>
		static string TempDirectory => Path.Combine(DataDirectory, "tmp");

		sealed class Sidecar
		{
			public string Program;
			public string[] Prefix = [];
			public string Root;
			public bool Python;
			public string PythonPath = "";
		}

		sealed class Ports
		{
			public int Bridge, Console, WorldStudio, Gateway, Chat, Transcribe;
		}

		/// <summary>Called once per mod launch, before the first world (RTSAILoadScreen.StartGame).</summary>
		public static void Initialize(ModData modData)
		{
			lock (Sync)
			{
				if (State != CompanionHostState.NotStarted)
					return;

				CompanionLog.Ensure();
				modVersion = modData.Manifest.Metadata.Version;
				if (Environment.GetEnvironmentVariable("OPENRA_AI_COMPANION") == "1")
				{
					// launch-game.ps1, tools/run-headless.sh and probe scripts run their own companion.
					State = CompanionHostState.External;
					Log.Write(CompanionLog.Channel, "Companion host: externally managed (OPENRA_AI_COMPANION=1).");
					return;
				}

				if (Game.IsHeadless || Environment.GetEnvironmentVariable("OPENRA_AI_HOST") == "0")
				{
					State = CompanionHostState.Off;
					Detail = "Headless or disabled by OPENRA_AI_HOST=0.";
					return;
				}

				if (!exitHandlerRegistered)
				{
					exitHandlerRegistered = true;
					AppDomain.CurrentDomain.ProcessExit += (_, _) => Shutdown();
				}
				LoadMode();
				if (Mode == ModeOff)
				{
					State = CompanionHostState.Off;
					Detail = "AI co-commander is off (Settings > AI).";
					Log.Write(CompanionLog.Channel, "Companion host: mode off.");
					return;
				}

				StartLocked();
			}
		}

		/// <summary>Called when the mod is disposed (exit or mod switch). Ends the sidecar and every process it started.</summary>
		public static void Shutdown()
		{
			lock (Sync)
			{
				StopLocked();
				if (State != CompanionHostState.External)
					State = CompanionHostState.NotStarted;
			}
		}

		/// <summary>
		/// False for a build that ships without the companion (no companion folder next to the game and no
		/// development override), so the HUD and settings do not suggest a reinstall or a mode that cannot start.
		/// </summary>
		static bool Included() => Bundled.Value;

		/// <summary>One line for the AI settings panel.</summary>
		public static string StatusLine()
		{
			return State switch
			{
				CompanionHostState.External => "Co-commander started by an external launcher.",
				CompanionHostState.Off => Included() ? "Co-commander is off. Choose a mode to start it." : NotIncluded,
				CompanionHostState.Missing => Included() ? "Companion files are missing. Reinstall RTS AI to restore them." : NotIncluded,
				CompanionHostState.Starting => "Starting the co-commander…",
				CompanionHostState.Restarting => "The co-commander stopped unexpectedly; restarting…",
				CompanionHostState.Failed => "The co-commander keeps stopping. Details: Logs/ai-companion.err.log.",
				CompanionHostState.Running => VoicePackProgress >= 0
					? $"Co-commander running ({ModeLabel(Mode)}). Downloading local voice: {VoicePackProgress}%."
					: $"Co-commander running ({ModeLabel(Mode)}).",
				_ => ""
			};
		}

		public static string ModeLabel(string mode)
		{
			return mode switch
			{
				ModeHosted => "hosted AI + local voice",
				ModeLocal => "full local AI",
				ModeExternal => "external endpoint",
				_ => "off"
			};
		}

		/// <summary>
		/// HUD text while the sidecar is not (yet) able to speak for itself. Returns false when the
		/// companion's own status should be shown.
		/// </summary>
		public static bool TryGetHudOverride(bool acknowledged, out string state, out string message)
		{
			switch (State)
			{
				case CompanionHostState.Missing:
					state = "error";
					message = Included() ? "AI CO-COMMANDER UNAVAILABLE  •  COMPANION FILES MISSING  •  GAME UNAFFECTED" : NotIncludedHud;
					return true;
				case CompanionHostState.Failed:
					state = "error";
					message = "AI CO-COMMANDER STOPPED  •  SEE LOGS/AI-COMPANION.ERR.LOG  •  GAME UNAFFECTED";
					return true;
				case CompanionHostState.Restarting:
					state = "thinking";
					message = "AI CO-COMMANDER RESTARTING…  •  GAME UNAFFECTED";
					return true;
				case CompanionHostState.Off:
					state = "disabled";
					message = Included() ? "AI CO-COMMANDER OFF  •  TURN IT ON IN SETTINGS > AI" : NotIncludedHud;
					return true;
				case CompanionHostState.Starting when !acknowledged:
					state = "thinking";
					message = "AI CO-COMMANDER STARTING…";
					return true;
				default:
					state = null;
					message = null;
					return false;
			}
		}

		/// <summary>Switch modes from the settings panel: saves the choice, reconfigures and restarts the sidecar.</summary>
		public static void ApplyMode(string mode, ExternalAISettings external, Action<bool, string> done)
		{
			if (!Modes.Contains(mode))
			{
				done?.Invoke(false, "Unknown AI mode.");
				return;
			}

			new Thread(() =>
			{
				bool ok;
				string message;
				try
				{
					lock (Sync)
					{
						if (State is CompanionHostState.External or CompanionHostState.NotStarted)
						{
							done?.Invoke(false, "The co-commander is managed by an external launcher.");
							return;
						}

						StopLocked();
						Mode = mode;
						var settings = ReadHostSettings();
						settings["mode"] = mode;
						if (mode == ModeExternal && external != null)
							settings["configured_mode"] = "";
						WriteHostSettings(settings);
						if (mode == ModeOff)
						{
							State = CompanionHostState.Off;
							Detail = "AI co-commander is off (Settings > AI).";
							ok = true;
							message = "The co-commander is off.";
						}
						else
						{
							restarts = 0;
							StartLocked(external);
							ok = State is CompanionHostState.Starting or CompanionHostState.Running;
							message = ok ? $"Starting the co-commander ({ModeLabel(mode)})…" : StatusLine();
						}
					}
				}
				catch (Exception e)
				{
					Log.Write(CompanionLog.Channel, $"Companion host: mode change failed: {e}");
					ok = false;
					message = "The AI mode could not be changed. See Logs/companion.log.";
				}

				done?.Invoke(ok, message);
			})
			{ IsBackground = true, Name = "RTSAI-Companion-Mode" }.Start();
		}

		static void LoadMode()
		{
			var settings = ReadHostSettings();
			var mode = settings["mode"]?.GetValue<string>() ?? ModeHosted;

			// The installer records the player's AI choice next to the game. Apply it once per install.
			var choicePath = Path.Combine(Platform.EngineDir, InstallChoiceFile);
			if (File.Exists(choicePath))
			{
				try
				{
					var choice = JsonNode.Parse(File.ReadAllText(choicePath));
					var stamp = choice?["stamp"]?.GetValue<string>() ?? "";
					var installMode = choice?["ai_mode"]?.GetValue<string>() ?? "";
					if (installMode == "none")
						installMode = ModeOff;

					if (Modes.Contains(installMode) && stamp != (settings["installer_stamp"]?.GetValue<string>() ?? ""))
					{
						mode = installMode;
						settings["installer_stamp"] = stamp;
						settings["mode"] = mode;
						WriteHostSettings(settings);
						Log.Write(CompanionLog.Channel, $"Companion host: applied the installer's AI choice '{mode}'.");
					}
				}
				catch (Exception e) when (e is IOException or JsonException or InvalidOperationException or UnauthorizedAccessException)
				{
					Log.Write(CompanionLog.Channel, $"Companion host: ignoring an unreadable {InstallChoiceFile}: {e.Message}");
				}
			}

			Mode = Modes.Contains(mode) ? mode : ModeHosted;
		}

		static JsonObject ReadHostSettings()
		{
			try
			{
				var path = Path.Combine(DataDirectory, HostSettingsFile);
				if (File.Exists(path) && JsonNode.Parse(File.ReadAllText(path)) is JsonObject value)
					return value;
			}
			catch (Exception e) when (e is IOException or JsonException or UnauthorizedAccessException)
			{
				Log.Write(CompanionLog.Channel, $"Companion host: resetting unreadable {HostSettingsFile}: {e.Message}");
			}

			return [];
		}

		static void WriteHostSettings(JsonObject settings)
		{
			Directory.CreateDirectory(DataDirectory);
			var path = Path.Combine(DataDirectory, HostSettingsFile);
			File.WriteAllText(path + ".tmp", settings.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
			File.Move(path + ".tmp", path, true);
		}

		static Sidecar ResolveSidecar()
		{
			var directories = new List<string>();
			var configured = Environment.GetEnvironmentVariable("OPENRA_AI_COMPANION_DIR");
			if (!string.IsNullOrWhiteSpace(configured))
				directories.Add(configured);
			directories.Add(Path.Combine(Platform.EngineDir, "companion"));
			foreach (var directory in directories)
			{
				var program = Path.Combine(directory, ExecutableName);
				if (File.Exists(program))
					return new Sidecar { Program = program, Root = Path.GetFullPath(directory) };
			}

			// Development: an OpenRA-AI checkout with its virtual environment.
			var root = Environment.GetEnvironmentVariable("OPENRA_AI_ROOT");
			if (!string.IsNullOrWhiteSpace(root))
			{
				var python = Path.Combine(root, ".venv", "Scripts", "python.exe");
				var entry = Path.Combine(root, "apps", "launcher", "companion_entry.py");
				if (File.Exists(python) && File.Exists(entry))
					return new Sidecar
					{
						Program = python,
						Prefix = ["-u", entry],
						Root = Path.GetFullPath(root),
						Python = true,
						PythonPath = string.Join(Path.PathSeparator,
							Path.Combine(root, "services", "companion", "src"), Path.Combine(root, "services", "worldgen", "src"))
					};
			}

			return null;
		}

		static int FreePort(HashSet<int> taken)
		{
			for (var attempt = 0; attempt < 20; attempt++)
			{
				var listener = new TcpListener(IPAddress.Loopback, 0);
				listener.Start();
				var port = ((IPEndPoint)listener.LocalEndpoint).Port;
				listener.Stop();

				// 4000 is the companion's legacy default; never collide with whatever else listens there.
				if (port != 4000 && taken.Add(port))
					return port;
			}

			throw new InvalidOperationException("No free loopback port for the AI companion.");
		}

		static void StartLocked(ExternalAISettings external = null)
		{
			stopping = false;
			sidecar ??= ResolveSidecar();
			if (ports == null)
			{
				var taken = new HashSet<int>();
				ports = new Ports
				{
					Bridge = FreePort(taken),
					Console = FreePort(taken),
					WorldStudio = FreePort(taken),
					Gateway = FreePort(taken),
					Chat = FreePort(taken),
					Transcribe = FreePort(taken),
				};

				// The bridge (gRPC host) and the HUD read these from the game process.
				Environment.SetEnvironmentVariable("OPENRA_AI_GRPC_PORT", ports.Bridge.ToString(NumberFormatInfo()));
				Environment.SetEnvironmentVariable("OPENRA_AI_CONSOLE_URL", $"http://127.0.0.1:{ports.Console}/");
				Environment.SetEnvironmentVariable("OPENRA_AI_WORLD_STUDIO_URL", $"http://127.0.0.1:{ports.WorldStudio}/");
			}

			if (sidecar == null)
			{
				State = CompanionHostState.Missing;
				Detail = $"{ExecutableName} was not found in {Path.Combine(Platform.EngineDir, "companion")}.";
				Log.Write(CompanionLog.Channel, "Companion host: " + Detail);
				return;
			}

			State = CompanionHostState.Starting;
			var launch = ++generation;
			new Thread(() => Launch(launch, external)) { IsBackground = true, Name = "RTSAI-Companion-Host" }.Start();
		}

		static IFormatProvider NumberFormatInfo() => System.Globalization.CultureInfo.InvariantCulture;

		static void StopLocked()
		{
			stopping = true;
			generation++;
			try
			{
				job?.Terminate();
				if (process != null && !process.HasExited)
					process.Kill(true);
			}
			catch (Exception e) when (e is InvalidOperationException or System.ComponentModel.Win32Exception)
			{
				// Already gone.
			}

			job?.Dispose();
			job = null;
			process?.Dispose();
			process = null;
			outputLog?.Dispose();
			errorLog?.Dispose();
			outputLog = errorLog = null;
			VoicePackProgress = -1;
			VoiceReady = false;
			ClearTempDirectory(true);
		}

		static void ClearTempDirectory(bool waitForRelease)
		{
			if (sidecar == null)
				return;

			// Killed processes release their DLL handles a moment after TerminateJobObject returns.
			for (var attempt = 0; attempt < (waitForRelease ? 10 : 1); attempt++)
			{
				try
				{
					if (Directory.Exists(TempDirectory))
						Directory.Delete(TempDirectory, true);
					return;
				}
				catch (Exception e) when (e is IOException or UnauthorizedAccessException)
				{
					Thread.Sleep(100);
				}
			}
		}

		static Dictionary<string, string> ChildEnvironment()
		{
			var gateway = $"http://127.0.0.1:{ports.Gateway}";
			var root = sidecar.Root;
			var environment = new Dictionary<string, string>
			{
				["OPENRA_AI_DATA_DIR"] = DataDirectory,
				["OPENRA_AI_LOG_DIR"] = LogDirectory,
				["OPENRA_AI_SUPPORT_DIR"] = Platform.SupportDir,
				["OPENRA_AI_ENGINE_DIR"] = Platform.EngineDir,
				["OPENRA_AI_CATALOG"] = Path.Combine(root, "catalog", "factions.json"),
				["OPENRA_AI_VERSION"] = modVersion,
				["OPENRA_AI_MODEL_ROOT"] = root,
				["OPENRA_AI_PACK_LOCK"] = Path.Combine(root, "packaging", "ai-pack.lock.json"),
				["OPENRA_AI_BUNDLED_RUNTIME"] = Path.Combine(root, "ai", "runtime"),
				["OPENRA_AI_RUNTIME_EXECUTABLE"] = sidecar.Program,
				["OPENRA_AI_LOCAL_ROUTER_URL"] = gateway,
				["OPENRA_AI_ROUTER_URL"] = gateway,
				["OPENRA_AI_AGENT_ROUTER_URL"] = gateway,
				["OPENRA_AI_LOCAL_CHAT_PORT"] = ports.Chat.ToString(NumberFormatInfo()),
				["OPENRA_AI_LOCAL_TRANSCRIBE_PORT"] = ports.Transcribe.ToString(NumberFormatInfo()),
				["OPENRA_AI_AUTO_INSTALL_VOICE"] = Mode == ModeHosted ? "1" : "0",
				["OPENRA_AI_DISABLE_AUTOSTART"] = "1",
				["PYTHONUNBUFFERED"] = "1",
				["PYTHONUTF8"] = "1",
				["PYTHONIOENCODING"] = "utf-8",
				["TEMP"] = TempDirectory,
				["TMP"] = TempDirectory,
			};

			if (sidecar.Python)
			{
				environment["OPENRA_AI_RUNTIME_PYTHON"] = "1";
				environment["PYTHONPATH"] = sidecar.PythonPath;
			}
			else
				environment["OPENRA_AI_RUNTIME_SUBCOMMAND"] = "runtime";

			if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("OPENRA_AI_APP_LANGUAGE")))
				environment["OPENRA_AI_APP_LANGUAGE"] = "en";

			return environment;
		}

		static ProcessStartInfo StartInfo(IEnumerable<string> arguments)
		{
			var info = new ProcessStartInfo(sidecar.Program)
			{
				UseShellExecute = false,
				CreateNoWindow = true,
				RedirectStandardOutput = true,
				RedirectStandardError = true,
				StandardOutputEncoding = Encoding.UTF8,
				StandardErrorEncoding = Encoding.UTF8,
				WorkingDirectory = sidecar.Python ? sidecar.Root : Path.GetDirectoryName(sidecar.Program),
			};

			foreach (var argument in sidecar.Prefix.Concat(arguments))
				info.ArgumentList.Add(argument);

			foreach (var (key, value) in ChildEnvironment())
				info.Environment[key] = value;

			// The companion must not think a launcher already manages it.
			info.Environment.Remove("OPENRA_AI_COMPANION");
			return info;
		}

		static readonly HashSet<string> LogsOpenedThisSession = [];

		static StreamWriter OpenLog(string name)
		{
			Directory.CreateDirectory(LogDirectory);

			// Like OpenRA's own logs: start fresh each game session, append across restarts within it.
			var first = LogsOpenedThisSession.Add(name);
			var mode = first ? FileMode.Create : FileMode.Append;
			if (first && name == "ai-companion.out.log")
			{
				// The gateway appends to its own logs; trim them once per session as well.
				foreach (var runtimeLog in new[] { "ai-runtime.out.log", "ai-runtime.err.log" })
				{
					try
					{
						File.Delete(Path.Combine(LogDirectory, runtimeLog));
					}
					catch (Exception e) when (e is IOException or UnauthorizedAccessException)
					{
						// Still open by a sidecar from a previous mod session; it is trimmed next time.
					}
				}
			}

			var stream = new FileStream(Path.Combine(LogDirectory, name), mode, FileAccess.Write, FileShare.ReadWrite | FileShare.Delete);
			return new StreamWriter(stream, new UTF8Encoding(false)) { AutoFlush = true };
		}

		/// <summary>Write provider.json/settings.json for the chosen mode (the companion's own configure command).</summary>
		static bool Configure(ExternalAISettings external)
		{
			var settings = ReadHostSettings();
			var configured = settings["configured_mode"]?.GetValue<string>() ?? "";
			var providerExists = File.Exists(Path.Combine(DataDirectory, "provider.json"));
			if (configured == Mode && providerExists && external == null)
				return true;

			if (Mode == ModeExternal && external == null && providerExists)
				return true;

			Directory.CreateDirectory(DataDirectory);
			var arguments = new List<string> { "runtime", "configure" };
			string ini = null;
			if (Mode == ModeExternal)
			{
				if (external == null || string.IsNullOrWhiteSpace(external.Endpoint) || string.IsNullOrWhiteSpace(external.Model))
				{
					Detail = "External mode needs an endpoint and a model (Settings > AI).";
					return false;
				}

				// The companion reads and deletes this file; the key is then stored with Windows DPAPI.
				ini = Path.Combine(DataDirectory, $"external-{Guid.NewGuid():N}.ini");
				File.WriteAllText(ini, "[provider]\n" +
					"mode = external\n" +
					$"endpoint = {external.Endpoint.Trim()}\n" +
					$"api_key = {external.ApiKey?.Trim() ?? ""}\n" +
					$"text_model = {external.Model.Trim()}\n" +
					$"vision_model = {external.Model.Trim()}\n" +
					"transcribe_model = local-whisper\n" +
					"speech_model = local-kokoro\n" +
					"speech_voice = alloy\n");
				arguments.AddRange(["--input-ini", ini]);
			}
			else
				arguments.AddRange(["--mode", Mode]);

			try
			{
				using var configure = Process.Start(StartInfo(arguments));
				var output = configure.StandardOutput.ReadToEndAsync();
				var error = configure.StandardError.ReadToEndAsync();
				if (!configure.WaitForExit(60000))
				{
					configure.Kill(true);
					Detail = "The AI configuration step timed out.";
					return false;
				}

				outputLog?.WriteLine(output.Result.TrimEnd());
				if (!string.IsNullOrWhiteSpace(error.Result))
					errorLog?.WriteLine(error.Result.TrimEnd());

				if (configure.ExitCode != 0)
				{
					Detail = $"The AI configuration step failed (exit {configure.ExitCode}).";
					return false;
				}
			}
			finally
			{
				if (ini != null && File.Exists(ini))
					File.Delete(ini);
			}

			settings["configured_mode"] = Mode;
			settings["mode"] = Mode;
			WriteHostSettings(settings);
			Log.Write(CompanionLog.Channel, $"Companion host: configured {Mode} mode.");
			return true;
		}

		static void Launch(int launch, ExternalAISettings external)
		{
			try
			{
				lock (Sync)
				{
					if (launch != generation || stopping)
						return;

					outputLog ??= OpenLog("ai-companion.out.log");
					errorLog ??= OpenLog("ai-companion.err.log");
					outputLog.WriteLine($"--- {DateTime.Now:yyyy-MM-dd HH:mm:ss} starting the co-commander ({Mode}) from {sidecar.Program}");
					ClearTempDirectory(true);
					Directory.CreateDirectory(TempDirectory);
				}

				// A few seconds at most; never hold the lock across it (Shutdown must stay instant).
				var configured = Configure(external);
				lock (Sync)
				{
					if (launch != generation || stopping)
						return;

					if (!configured)
					{
						State = CompanionHostState.Failed;
						Log.Write(CompanionLog.Channel, "Companion host: " + Detail);
						return;
					}

					var version = modVersion;
					var arguments = new List<string>
					{
						"watch",
						"--bridge", $"127.0.0.1:{ports.Bridge}",
						"--parent-pid", Environment.ProcessId.ToString(NumberFormatInfo()),
						"--control-port", ports.Console.ToString(NumberFormatInfo()),
						"--worldgen-port", ports.WorldStudio.ToString(NumberFormatInfo()),
						"--mission-output", Path.Combine(Platform.SupportDir, "GeneratedMissions"),
						"--mission-install", Path.Combine(Platform.SupportDir, "maps", "rtsai", version),
						"--speak",
						"--voice-hotkeys"
					};

					var child = new Process { StartInfo = StartInfo(arguments), EnableRaisingEvents = true };
					var stdout = outputLog;
					var stderr = errorLog;
					child.OutputDataReceived += (_, e) => { if (e.Data != null) WriteLine(stdout, e.Data); };
					child.ErrorDataReceived += (_, e) => { if (e.Data != null) WriteLine(stderr, e.Data); };
					child.Start();
					child.BeginOutputReadLine();
					child.BeginErrorReadLine();
					job = CompanionProcessJob.TryCreate();
					if (job != null && !job.Assign(child))
					{
						job.Dispose();
						job = null;
					}

					process = child;
					Log.Write(CompanionLog.Channel, $"Companion host: started PID {child.Id} ({Mode}); bridge {ports.Bridge}, " +
						$"console {ports.Console}, gateway {ports.Gateway}, job {(job != null ? "on" : "off")}.");
				}

				Monitor(launch);
			}
			catch (Exception e)
			{
				lock (Sync)
				{
					State = CompanionHostState.Failed;
					Detail = e.Message;
				}

				Log.Write(CompanionLog.Channel, $"Companion host: could not start the sidecar: {e}");
			}
		}

		static void WriteLine(StreamWriter writer, string line)
		{
			try
			{
				lock (writer)
					writer.WriteLine(line);
			}
			catch (ObjectDisposedException)
			{
				// The log was closed while the process was being stopped.
			}
		}

		static void Monitor(int launch)
		{
			Process child;
			lock (Sync)
				child = process;

			using var client = HttpClientFactory.Create();
			client.Timeout = TimeSpan.FromSeconds(2);
			var console = new Uri($"http://127.0.0.1:{ports.Console}/");
			var deadline = DateTime.UtcNow.AddSeconds(90);
			var nextPoll = DateTime.MinValue;
			var announcedVoice = false;
			while (true)
			{
				if (child.WaitForExit(250))
					break;

				lock (Sync)
					if (launch != generation || stopping)
						return;

				if (DateTime.UtcNow < nextPoll)
					continue;

				// Fast while starting or downloading the voice pack; then a slow heartbeat, so the
				// companion's request log stays small over a long session.
				nextPoll = DateTime.UtcNow.AddSeconds(State != CompanionHostState.Running ? 0.5
					: VoiceReady && VoicePackProgress < 0 ? 30 : 2);
				try
				{
					if (State != CompanionHostState.Running)
					{
						using var health = JsonDocument.Parse(client.GetStringAsync(new Uri(console, "health")).Result);
						if (health.RootElement.TryGetProperty("control_ready", out var ready) && ready.GetBoolean())
						{
							var auto = health.RootElement.TryGetProperty("auto_act_enabled", out var autoAct) && autoAct.GetBoolean();
							Environment.SetEnvironmentVariable("OPENRA_AI_COMPANION_READY", "1");
							Environment.SetEnvironmentVariable("OPENRA_AI_STARTUP_AUTO_ACT", auto ? "1" : "0");
							lock (Sync)
							{
								if (launch != generation)
									return;

								State = CompanionHostState.Running;
								Detail = "";
								restarts = 0;
							}

							Log.Write(CompanionLog.Channel, $"Companion host: co-commander ready ({Mode}).");
						}
						else if (DateTime.UtcNow > deadline)
						{
							deadline = DateTime.MaxValue;
							Log.Write(CompanionLog.Channel, "Companion host: the co-commander is slow to become ready; still waiting.");
						}

						continue;
					}

					using var setup = JsonDocument.Parse(client.GetStringAsync(new Uri(console, "v1/local-ai")).Result);
					var root = setup.RootElement;
					var setupState = root.TryGetProperty("state", out var value) ? value.GetString() : "";
					VoicePackProgress = setupState == "installing" && root.TryGetProperty("progress_percent", out var progress)
						? progress.GetInt32() : -1;
					VoiceReady = root.TryGetProperty("capabilities", out var capabilities)
						&& capabilities.TryGetProperty("voice_input", out var voice) && voice.GetString() == "ready";
					if (VoiceReady && !announcedVoice)
					{
						announcedVoice = true;
						Log.Write(CompanionLog.Channel, "Companion host: local voice ready.");
					}
				}
				catch (Exception e) when (e is AggregateException or System.Net.Http.HttpRequestException
					or System.Threading.Tasks.TaskCanceledException or JsonException or InvalidOperationException or KeyNotFoundException)
				{
					// Not up yet, or busy; keep polling.
				}
			}

			int exitCode;
			try
			{
				exitCode = child.ExitCode;
			}
			catch (InvalidOperationException)
			{
				exitCode = -1;
			}

			lock (Sync)
			{
				if (launch != generation || stopping)
					return;

				restarts++;
				Log.Write(CompanionLog.Channel, $"Companion host: the co-commander exited with code {exitCode} (restart {restarts}/{MaxRestarts}).");
				job?.Dispose();
				job = null;
				process?.Dispose();
				process = null;
				if (restarts > MaxRestarts)
				{
					State = CompanionHostState.Failed;
					Detail = $"The co-commander exited {restarts} times (last exit code {exitCode}).";
					return;
				}

				State = CompanionHostState.Restarting;
			}

			Thread.Sleep(TimeSpan.FromSeconds(2 * restarts));
			lock (Sync)
			{
				if (launch != generation || stopping)
					return;

				var next = ++generation;
				new Thread(() => Launch(next, null)) { IsBackground = true, Name = "RTSAI-Companion-Host" }.Start();
			}
		}
	}
}
