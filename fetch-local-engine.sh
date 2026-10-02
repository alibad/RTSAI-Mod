#!/bin/sh
# Local stand-in for the SDK's AUTOMATIC_ENGINE_MANAGEMENT download step.
#
# The SDK normally downloads ${AUTOMATIC_ENGINE_SOURCE} (a GitHub archive of
# ENGINE_VERSION), extracts it to ENGINE_DIRECTORY and runs `make version`.
# This script does the same from a local checkout of the engine fork, using
# `git archive` (no worktree, no checkout, read-only on the source repo), so
# the spike can run offline against the exact pinned commit.
#
# Usage: ./fetch-local-engine.sh [path-to-engine-repo]
#        (default: ../OpenRA, override with LOCAL_ENGINE_REPO in user.config)
set -e
cd "$(dirname "$0")"

# shellcheck source=mod.config
. ./mod.config
if [ -f user.config ]; then
	# shellcheck source=user.config
	. ./user.config
fi

REPO="${1:-${LOCAL_ENGINE_REPO:-../OpenRA}}"
DEST="${ENGINE_DIRECTORY:-./engine}"

echo "Exporting engine ${ENGINE_VERSION} from ${REPO} to ${DEST}"
rm -rf "${DEST}"
mkdir -p "${DEST}"
git -C "${REPO}" archive "${ENGINE_VERSION}" | tar -x -C "${DEST}"

# OpenRA.Mods.RA2 is owned by this mod (./OpenRA.Mods.RA2). The slim engine
# (rtsai/engine) does not ship it; older fork pins did, so drop any engine copy
# so only one OpenRA.Mods.RA2.dll is ever written into engine/bin.
if [ -d "${DEST}/OpenRA.Mods.RA2" ]; then
	rm -rf "${DEST}/OpenRA.Mods.RA2"
	sed -i '/OpenRA.Mods.RA2/d' "${DEST}"/OpenRA.sln*
fi

# The engine's `make all` downloads the GeoIP database when it is missing or
# older than 30 days. Reuse the local copy so the build needs no extra network.
if [ -f "${REPO}/IP2LOCATION-LITE-DB1.IPV6.BIN.ZIP" ]; then
	cp "${REPO}/IP2LOCATION-LITE-DB1.IPV6.BIN.ZIP" "${DEST}/"
fi

# Same as the SDK's post-download step: stamp VERSION and the engine mods.
printf '%s\n' "${ENGINE_VERSION}" > "${DEST}/VERSION"
for MOD in "${DEST}"/mods/*/mod.yaml; do
	sed -i "s|Version: .*|Version: ${ENGINE_VERSION}|" "${MOD}"
done

echo "Engine ready. Run ./make.cmd all (Windows) or make (Unix)."
