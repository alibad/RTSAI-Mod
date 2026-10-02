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
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace OpenRA.Mods.RTSAI.Companion
{
	/// <summary>
	/// A Windows job object with KILL_ON_JOB_CLOSE. The companion sidecar and every process it
	/// starts (the AI gateway, whisper-server, llama-server) are assigned to it, so they all end
	/// when the game ends - also when the game crashes or is killed, because Windows closes the
	/// job handle with the process. On other platforms this is a no-op and the sidecar's
	/// --parent-pid watch stops it instead.
	/// </summary>
	sealed class CompanionProcessJob : IDisposable
	{
		const int JobObjectExtendedLimitInformation = 9;
		const uint LimitKillOnJobClose = 0x2000;

		[StructLayout(LayoutKind.Sequential)]
		struct BasicLimitInformation
		{
			public long PerProcessUserTimeLimit;
			public long PerJobUserTimeLimit;
			public uint LimitFlags;
			public UIntPtr MinimumWorkingSetSize;
			public UIntPtr MaximumWorkingSetSize;
			public uint ActiveProcessLimit;
			public UIntPtr Affinity;
			public uint PriorityClass;
			public uint SchedulingClass;
		}

		[StructLayout(LayoutKind.Sequential)]
		struct IoCounters
		{
			public ulong ReadOperationCount;
			public ulong WriteOperationCount;
			public ulong OtherOperationCount;
			public ulong ReadTransferCount;
			public ulong WriteTransferCount;
			public ulong OtherTransferCount;
		}

		[StructLayout(LayoutKind.Sequential)]
		struct ExtendedLimitInformation
		{
			public BasicLimitInformation BasicLimitInformation;
			public IoCounters IoInfo;
			public UIntPtr ProcessMemoryLimit;
			public UIntPtr JobMemoryLimit;
			public UIntPtr PeakProcessMemoryUsed;
			public UIntPtr PeakJobMemoryUsed;
		}

		[DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
		static extern IntPtr CreateJobObject(IntPtr attributes, string name);

		[DllImport("kernel32.dll", SetLastError = true)]
		static extern bool SetInformationJobObject(IntPtr job, int infoClass, ref ExtendedLimitInformation info, uint length);

		[DllImport("kernel32.dll", SetLastError = true)]
		static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);

		[DllImport("kernel32.dll", SetLastError = true)]
		static extern bool TerminateJobObject(IntPtr job, uint exitCode);

		[DllImport("kernel32.dll", SetLastError = true)]
		static extern bool CloseHandle(IntPtr handle);

		IntPtr handle;

		public static CompanionProcessJob TryCreate()
		{
			if (!OperatingSystem.IsWindows())
				return null;

			try
			{
				var job = CreateJobObject(IntPtr.Zero, null);
				if (job == IntPtr.Zero)
					return null;

				var info = new ExtendedLimitInformation
				{
					BasicLimitInformation = new BasicLimitInformation { LimitFlags = LimitKillOnJobClose }
				};

				if (!SetInformationJobObject(job, JobObjectExtendedLimitInformation, ref info, (uint)Marshal.SizeOf<ExtendedLimitInformation>()))
				{
					CloseHandle(job);
					return null;
				}

				return new CompanionProcessJob { handle = job };
			}
			catch (Exception e) when (e is DllNotFoundException or EntryPointNotFoundException)
			{
				return null;
			}
		}

		public bool Assign(Process process)
		{
			return handle != IntPtr.Zero && AssignProcessToJobObject(handle, process.Handle);
		}

		/// <summary>Ends every process in the job (the sidecar and its children).</summary>
		public void Terminate()
		{
			if (handle != IntPtr.Zero)
				TerminateJobObject(handle, 0);
		}

		public void Dispose()
		{
			if (handle == IntPtr.Zero)
				return;

			CloseHandle(handle);
			handle = IntPtr.Zero;
		}
	}
}
