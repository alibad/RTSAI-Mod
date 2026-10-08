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
			if (!string.IsNullOrEmpty(manifestVersion) && manifestVersion != "{DEV_VERSION}")
				return manifestVersion;

			var stamp = BuildStamp();
			return FluentProvider.GetMessage(DevBuild, "build", string.IsNullOrEmpty(stamp) ? "?" : stamp);
		}
	}
}
