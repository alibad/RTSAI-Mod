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

using System.Linq;
using System.Reflection;
using System.IO;
using System.Text.Json;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	/// <summary>
	/// The main menu's version line. A packaged build shows the manifest version (`make version` writes it). A
	/// development build, whose manifest still says {DEV_VERSION}, shows the git commit it was compiled from
	/// (OpenRA.Mods.RTSAI.csproj stamps it into the assembly as the RTSAIBuild metadata).
	/// </summary>
	public class RTSAIVersionLabelLogic : ChromeLogic
	{
		[FluentReference("build")]
		const string DevBuild = "label-rtsai-dev-build";

		[ObjectCreator.UseCtor]
		public RTSAIVersionLabelLogic(LabelWidget widget, ModData modData)
		{
			var text = VersionText(modData.Manifest.Metadata.Version);
			widget.GetText = () => text;
		}

		public static string BuildStamp()
		{
			return typeof(RTSAIVersionLabelLogic).Assembly.GetCustomAttributes<AssemblyMetadataAttribute>()
				.FirstOrDefault(a => a.Key == "RTSAIBuild")?.Value;
		}

		public static string VersionText(string manifestVersion)
		{
			var content = ContentText();
			if (content != null)
				return content;
			if (!string.IsNullOrEmpty(manifestVersion) && manifestVersion != "{DEV_VERSION}")
				return manifestVersion;

			var stamp = BuildStamp();
			return FluentProvider.GetMessage(DevBuild, "build", string.IsNullOrEmpty(stamp) ? "?" : stamp);
		}

		public static string ContentText()
		{
			var file = Path.Combine(Platform.EngineDir, "content-build.json");
			if (!File.Exists(file)) return null;
			try
			{
				using var doc = JsonDocument.Parse(File.ReadAllText(file));
				var revision = doc.RootElement.GetProperty("revision").GetString();
				var verified = doc.RootElement.GetProperty("verified").GetBoolean();
				return $"Content {revision[..10]} · {(verified ? "Verified" : "Built")} · Local";
			}
			catch (JsonException) { return "Local content identity unavailable"; }
		}
	}
}
