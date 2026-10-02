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
using System.Threading.Tasks;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Lint;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Common.Widgets.Logic;
using OpenRA.Mods.RTSAI.Traits;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	[ChromeLogicArgsHotkeys("AskKey", "AcceptKey", "RejectKey", "ToggleAutoKey", "ToggleVoiceKey")]
	public sealed class AIHotkeyLogic : ChromeLogic
	{
		[FluentReference]
		const string VoiceSetupTitle = "dialog-ai-voice-setup-title";

		[FluentReference("size")]
		const string VoiceSetupInstall = "dialog-ai-voice-setup-install";

		[FluentReference]
		const string VoiceSetupRetry = "dialog-ai-voice-setup-retry";

		[FluentReference("progress", "shortcut")]
		const string VoiceSetupProgress = "dialog-ai-voice-setup-progress";

		[FluentReference("shortcut")]
		const string VoiceSetupStart = "dialog-ai-voice-setup-start";

		[FluentReference("shortcut")]
		const string VoiceSetupStarting = "dialog-ai-voice-setup-starting";

		[FluentReference]
		const string VoiceSetupUnsupported = "dialog-ai-voice-setup-unsupported";

		[FluentReference("shortcut")]
		const string VoiceSetupUnavailable = "dialog-ai-voice-setup-unavailable";

		[FluentReference]
		const string VoiceSetupInstallButton = "dialog-ai-voice-setup-install-button";

		[FluentReference]
		const string VoiceSetupStartButton = "dialog-ai-voice-setup-start-button";

		[FluentReference]
		const string VoiceSetupRetryButton = "dialog-ai-voice-setup-retry-button";

		[FluentReference]
		const string VoiceSetupNotNowButton = "dialog-ai-voice-setup-not-now-button";

		[FluentReference]
		const string VoiceSetupOKButton = "dialog-ai-voice-setup-ok-button";

		readonly ModData modData;
		readonly HotkeyReference askKey;
		readonly HotkeyReference acceptKey;
		readonly HotkeyReference rejectKey;
		readonly HotkeyReference toggleAutoKey;
		readonly HotkeyReference toggleVoiceKey;
		volatile bool askHeld;
		volatile bool voiceCaptureStarted;
		volatile bool voiceReadinessPending;
		bool voiceSetupPromptOpen;
		volatile bool operationBusy;

		[ObjectCreator.UseCtor]
		public AIHotkeyLogic(Widget widget, ModData modData, Dictionary<string, MiniYaml> logicArgs)
		{
			this.modData = modData;
			askKey = Resolve(modData, logicArgs, "AskKey");
			acceptKey = Resolve(modData, logicArgs, "AcceptKey");
			rejectKey = Resolve(modData, logicArgs, "RejectKey");
			toggleAutoKey = Resolve(modData, logicArgs, "ToggleAutoKey");
			toggleVoiceKey = Resolve(modData, logicArgs, "ToggleVoiceKey");

			widget.Get<LogicKeyListenerWidget>("GLOBAL_KEYHANDLER").AddHandler(HandleKeyPress);
		}

		static HotkeyReference Resolve(ModData modData, Dictionary<string, MiniYaml> logicArgs, string name)
		{
			return logicArgs.TryGetValue(name, out var yaml) ? modData.Hotkeys[yaml.Value] : new HotkeyReference();
		}

		bool HandleKeyPress(KeyInput e)
		{
			// The lobby turned the co-commander off for this match: no voice, orders or AUTO.
			if (CompanionBridge.IsDisabledForMatch)
				return false;

			var ask = askKey.GetValue();
			if (e.Event == KeyInputEvent.Down && askKey.IsActivatedBy(e))
			{
				if (!askHeld)
				{
					askHeld = true;
					if (!voiceReadinessPending)
					{
						voiceReadinessPending = true;
						_ = BeginVoiceAsync();
					}
				}

				return true;
			}

			if (e.Event == KeyInputEvent.Up && askHeld &&
				(e.Key == ask.Key || !RequiredModifiersHeld(ask.Modifiers, e.Modifiers)))
			{
				StopVoiceCapture();
				return true;
			}

			if (e.Event != KeyInputEvent.Down)
				return false;

			if (acceptKey.IsActivatedBy(e))
				return StartOperation(() => PostAsync("v1/actions/confirm"));
			if (rejectKey.IsActivatedBy(e))
				return StartOperation(() => PostAsync("v1/actions/cancel"));
			if (toggleAutoKey.IsActivatedBy(e))
				return StartOperation(() => ToggleAsync("auto_act_enabled", "auto_act"));
			if (toggleVoiceKey.IsActivatedBy(e))
				return StartOperation(() => ToggleAsync("voice_enabled", "muted", invertPostedValue: true));

			return false;
		}

		static bool RequiredModifiersHeld(Modifiers required, Modifiers current)
		{
			return (current & required) == required;
		}

		void StopVoiceCapture()
		{
			askHeld = false;
			if (!voiceCaptureStarted)
				return;

			voiceCaptureStarted = false;
			_ = PostAsync("v1/voice/stop");
		}

		public override void Tick()
		{
			if (!askHeld)
				return;

			var ask = askKey.GetValue();
			if (!Game.IsKeyDown(ask.Key) || !RequiredModifiersHeld(ask.Modifiers, Game.GetModifierKeys()))
				StopVoiceCapture();
		}

		async Task BeginVoiceAsync()
		{
			try
			{
				var baseUri = OpenRAAILocalClient.GetBaseUri("OPENRA_AI_CONSOLE_URL", "http://127.0.0.1:8787/");
				using var readiness = await OpenRAAILocalClient.GetAsync(baseUri, "v1/voice/readiness", 4);
				var root = readiness.RootElement;
				if (root.GetProperty("ready").GetBoolean())
				{
					if (!askHeld)
						return;

					using var response = await OpenRAAILocalClient.PostAsync(baseUri, "v1/voice/start", new { });
					voiceCaptureStarted = true;
					if (!askHeld)
					{
						voiceCaptureStarted = false;
						_ = PostAsync("v1/voice/stop");
					}

					return;
				}

				var action = root.TryGetProperty("action", out var actionValue) ? actionValue.GetString() : "wait";
				var progress = 0;
				long totalBytes = 0;
				if (root.TryGetProperty("local_ai", out var localAI))
				{
					if (localAI.TryGetProperty("progress_percent", out var progressValue))
						progress = progressValue.GetInt32();
					if (localAI.TryGetProperty("total_bytes", out var totalValue))
						totalBytes = totalValue.GetInt64();
				}

				Game.RunAfterTick(() => ShowVoiceSetupPrompt(action, progress, totalBytes));
			}
			catch
			{
				Game.RunAfterTick(() => ShowVoiceSetupPrompt("unavailable", 0, 0));
			}
			finally
			{
				voiceReadinessPending = false;
			}
		}

		void ShowVoiceSetupPrompt(string action, int progress, long totalBytes)
		{
			if (voiceSetupPromptOpen)
				return;

			voiceSetupPromptOpen = true;
			void ClosePrompt() => voiceSetupPromptOpen = false;
			var shortcut = askKey.GetValue().DisplayString();
			if (action == "install")
			{
				var size = totalBytes > 0 ? $"{totalBytes / 1_000_000_000d:0.0} GB" : "about 1.8 GB";
				ConfirmationDialogs.ButtonPrompt(modData,
					title: VoiceSetupTitle,
					text: VoiceSetupInstall,
					textArguments: ["size", size],
					onConfirm: () => { ClosePrompt(); _ = StartLocalAIAsync("install"); },
					confirmText: VoiceSetupInstallButton,
					onCancel: ClosePrompt,
					cancelText: VoiceSetupNotNowButton);
				return;
			}

			if (action is "retry" or "start")
			{
				ConfirmationDialogs.ButtonPrompt(modData,
					title: VoiceSetupTitle,
					text: action == "retry" ? VoiceSetupRetry : VoiceSetupStart,
					textArguments: action == "start" ? ["shortcut", shortcut] : null,
					onConfirm: () => { ClosePrompt(); _ = StartLocalAIAsync("retry"); },
					confirmText: action == "retry" ? VoiceSetupRetryButton : VoiceSetupStartButton,
					onCancel: ClosePrompt,
					cancelText: VoiceSetupNotNowButton);
				return;
			}

			var text = action switch
			{
				"view_progress" => VoiceSetupProgress,
				"choose_cloud" => VoiceSetupUnsupported,
				"unavailable" => VoiceSetupUnavailable,
				_ => VoiceSetupStarting,
			};
			object[] arguments = action == "view_progress"
				? ["progress", progress, "shortcut", shortcut]
				: action is "unavailable" or "wait" ? ["shortcut", shortcut] : null;
			ConfirmationDialogs.ButtonPrompt(modData,
				title: VoiceSetupTitle,
				text: text,
				textArguments: arguments,
				onConfirm: ClosePrompt,
				confirmText: VoiceSetupOKButton);
		}

		async Task StartLocalAIAsync(string operation)
		{
			try
			{
				var baseUri = OpenRAAILocalClient.GetBaseUri("OPENRA_AI_CONSOLE_URL", "http://127.0.0.1:8787/");
				using var response = await OpenRAAILocalClient.PostAsync(baseUri, $"v1/local-ai/{operation}", new { });
			}
			catch
			{
				Game.RunAfterTick(() => ShowVoiceSetupPrompt("unavailable", 0, 0));
			}
		}

		bool StartOperation(Func<Task> operation)
		{
			if (!operationBusy)
			{
				operationBusy = true;
				_ = RunOperationAsync(operation);
			}

			return true;
		}

		async Task RunOperationAsync(Func<Task> operation)
		{
			try
			{
				await operation();
			}
			catch { }
			finally
			{
				operationBusy = false;
			}
		}

		static async Task PostAsync(string path)
		{
			var baseUri = OpenRAAILocalClient.GetBaseUri("OPENRA_AI_CONSOLE_URL", "http://127.0.0.1:8787/");
			using var response = await OpenRAAILocalClient.PostAsync(baseUri, path, new { });
		}

		static async Task ToggleAsync(string stateField, string controlField, bool invertPostedValue = false)
		{
			var baseUri = OpenRAAILocalClient.GetBaseUri("OPENRA_AI_CONSOLE_URL", "http://127.0.0.1:8787/");
			using var state = await OpenRAAILocalClient.GetAsync(baseUri, "v1/state");
			var current = state.RootElement.GetProperty(stateField).GetBoolean();
			var next = invertPostedValue ? current : !current;
			var payload = new Dictionary<string, object> { { controlField, next } };
			using var response = await OpenRAAILocalClient.PostAsync(baseUri, "v1/control", payload);
		}
	}
}
