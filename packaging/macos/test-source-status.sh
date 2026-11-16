#!/bin/bash
set -o errexit -o pipefail
. "$(cd "$(dirname "$0")" && pwd)/source-status.sh"
rtsai_source_status_allowed ""
rtsai_source_status_allowed $' D .github/workflows/ci.yml\n D .github/workflows/documentation.yaml'
for status in $' M .github/workflows/ci.yml' $'D  .github/workflows/ci.yml' $' D OpenRA.Game/Game.cs' $' M OpenRA.Game/Game.cs' $'?? source.cs' $' D .github/workflows/ci.yml\n M OpenRA.Game/Game.cs'; do
	if rtsai_source_status_allowed "${status}"; then
		echo "Rejected-status fixture was accepted: ${status}" >&2
		exit 1
	fi
done
echo 'PASS source-status: clean and preserved workflow removals accepted; source changes and other dirty states rejected'
