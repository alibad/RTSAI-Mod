using System;
using System.Threading.Tasks;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	public static class OpenRAAIProposalClient
	{
		public static async Task ApplyAsync(Uri baseUri, string proposalId, string action)
		{
			if (string.IsNullOrWhiteSpace(proposalId) || (action != "confirm" && action != "cancel"))
				throw new ArgumentException("An explicit reviewed proposal ID and confirm/cancel action are required.");
			using var response = await OpenRAAILocalClient.PostAsync(baseUri, $"v1/proposals/{action}",
				new { contract_version = 1, proposal_id = proposalId });
		}
	}
}
