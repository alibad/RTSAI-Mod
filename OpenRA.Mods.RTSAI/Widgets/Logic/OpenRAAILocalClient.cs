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
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using OpenRA.Support;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	static class OpenRAAILocalClient
	{
		public static Uri GetBaseUri(string environmentVariable, string fallback)
		{
			var configured = Environment.GetEnvironmentVariable(environmentVariable);
			var value = string.IsNullOrWhiteSpace(configured) ? fallback : configured;
			if (!Uri.TryCreate(value, UriKind.Absolute, out var uri) ||
				(uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps) || !uri.IsLoopback)
				throw new InvalidOperationException("OpenRA AI services must use a local loopback URL.");

			return uri.AbsoluteUri.EndsWith('/') ? uri : new Uri(uri.AbsoluteUri + "/");
		}

		public static async Task<JsonDocument> GetAsync(Uri baseUri, string path, int timeoutSeconds = 12)
		{
			using var client = HttpClientFactory.Create();
			using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(timeoutSeconds));
			using var response = await client.GetAsync(new Uri(baseUri, path), cancellation.Token);
			var body = await response.Content.ReadAsStringAsync(cancellation.Token);
			if (!response.IsSuccessStatusCode)
				throw new InvalidOperationException($"Local AI service returned {(int)response.StatusCode}: {body}");

			return JsonDocument.Parse(body);
		}

		public static async Task<byte[]> GetBytesAsync(Uri baseUri, string path, int timeoutSeconds = 12)
		{
			using var client = HttpClientFactory.Create();
			using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(timeoutSeconds));
			using var response = await client.GetAsync(new Uri(baseUri, path), cancellation.Token);
			if (!response.IsSuccessStatusCode)
			{
				var body = await response.Content.ReadAsStringAsync(cancellation.Token);
				throw new InvalidOperationException($"Local AI service returned {(int)response.StatusCode}: {body}");
			}

			return await response.Content.ReadAsByteArrayAsync(cancellation.Token);
		}

		public static async Task<JsonDocument> PostAsync(Uri baseUri, string path, object payload, int timeoutSeconds = 20)
		{
			using var client = HttpClientFactory.Create();
			using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(timeoutSeconds));
			using var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
			using var response = await client.PostAsync(new Uri(baseUri, path), content, cancellation.Token);
			var body = await response.Content.ReadAsStringAsync(cancellation.Token);
			if (!response.IsSuccessStatusCode)
				throw new InvalidOperationException($"Local AI service returned {(int)response.StatusCode}: {body}");

			return JsonDocument.Parse(body);
		}
	}
}
