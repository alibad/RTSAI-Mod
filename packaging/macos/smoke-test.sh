#!/bin/bash
# Smoke-test a macOS release disk image from packaging/macos/build-release.sh on a macOS host (CI or a Mac).
#
#  1. the .sha256 matches; the image mounts; the app copies out the way a player installs it
#  2. the bundle: strict code signature check, Info.plist version and mod id, universal launchers
#  3. the payload: only the engine's common files and the shipped mods, no Westwood archives or videos
#  4. the native Utility wrapper loads the mod: --check-yaml, and --check-standalone --strict for the standalone game
#  5. the game itself boots headless (Game.Platform=Null) into a bot skirmish on a shipped map for --seconds,
#     writes a replay and logs no exception
#
# Steps 4-5 run natively, and again for the Intel slice when Rosetta 2 is available (otherwise it says so).
#
# usage: packaging/macos/smoke-test.sh <dmg> <version> [seconds]
set -o errexit -o pipefail

DMG="$1"
VERSION="$2"
SECONDS_TO_RUN="${3:-90}"
[ -f "${DMG}" ] && [ -n "${VERSION}" ] || { echo "usage: $(basename "$0") <dmg> <version> [seconds]"; exit 1; }

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=mod.config
. "${ROOT}/mod.config"
STANDALONE="${PACKAGING_STANDALONE:-False}"
APP_NAME="${PACKAGING_DISPLAY_NAME}.app"

WORK="${RTSAI_MAC_SMOKE_ROOT:-$(mktemp -d)}"
mkdir -p "${WORK}"
MOUNT="${WORK}/mount"
cleanup() {
	hdiutil detach "${MOUNT}" -quiet 2>/dev/null || true
}
trap cleanup EXIT

fail() {
	echo "SMOKE FAIL: $*" >&2
	exit 1
}

echo "== Checksum"
(cd "$(dirname "${DMG}")" && shasum -a 256 -c "$(basename "${DMG}").sha256")

echo "== Mount and install"
mkdir -p "${MOUNT}" "${WORK}/Applications"
hdiutil attach "${DMG}" -readonly -nobrowse -noautoopen -mountpoint "${MOUNT}" -quiet
[ -L "${MOUNT}/Applications" ] || fail "no Applications link in the image"
ditto "${MOUNT}/${APP_NAME}" "${WORK}/Applications/${APP_NAME}"
APP="${WORK}/Applications/${APP_NAME}"
CONTENTS="${APP}/Contents"
RESOURCES="${CONTENTS}/Resources"

echo "== Bundle"
codesign --verify --deep --strict --verbose=2 "${APP}"
codesign --display --verbose=2 "${APP}" 2>&1 | grep -E "^(Identifier|Format|Signature|TeamIdentifier)" || true
plutil -lint "${CONTENTS}/Info.plist"
[ "$(plutil -extract CFBundleShortVersionString raw "${CONTENTS}/Info.plist")" = "${VERSION}" ] || fail "Info.plist version"
[ "$(plutil -extract ModId raw "${CONTENTS}/Info.plist")" = "${MOD_ID}" ] || fail "Info.plist ModId"
[ "$(plutil -extract CFBundleExecutable raw "${CONTENTS}/Info.plist")" = "Launcher" ] || fail "Info.plist executable"
for binary in Launcher Utility; do
	archs="$(lipo -archs "${CONTENTS}/MacOS/${binary}")"
	[[ "${archs}" == *x86_64* && "${archs}" == *arm64* ]] || fail "${binary} is not universal (${archs})"
done
[ -f "${RESOURCES}/${MOD_ID}.icns" ] || fail "no icon"
grep -q "Version: ${VERSION}" "${RESOURCES}/mods/${MOD_ID}/mod.yaml" || fail "mod.yaml version"

echo "== Payload"
mods="$(cd "${RESOURCES}/mods" && ls | tr '\n' ' ')"
echo "mods: ${mods}"
if [ "${STANDALONE}" = "True" ]; then
	[ "${mods}" = "common rtsai rtsai-topdown " ] || fail "the standalone build must ship common and both product modes"
	[ ! -e "${RESOURCES}/global mix database.dat" ] || fail "MIX filename database in the standalone build"
fi
archives="$(find "${APP}" -type f \( -iname '*.mix' -o -iname '*.bag' -o -iname '*.idx' -o -iname '*.vqa' -o -iname '*.big' -o -iname '*.wsa' -o -iname '*.bik' \) | head -5)"
[ -z "${archives}" ] || fail "Westwood archives or videos in the app: ${archives}"
du -sh "${APP}"

run_checks() {
	local arch="$1" mode="$2" prefix=()
	[ "${arch}" = "x86_64" ] && prefix=(arch -x86_64)
	echo "== Utility (${arch}): --check-yaml"
	ENGINE_DIR="${WORK}/utility-engine" "${prefix[@]}" "${CONTENTS}/MacOS/apphost-${arch}" "${CONTENTS}/MacOS/${arch}/libhostfxr.dylib" "${CONTENTS}/MacOS/${arch}/OpenRA.Utility.dll" "${mode}" --check-yaml | tee "${WORK}/yaml-${arch}-${mode}.log"
	if [ "${STANDALONE}" = "True" ]; then
		echo "== Utility (${arch}): --check-standalone --strict"
		ENGINE_DIR="${WORK}/utility-engine" "${prefix[@]}" "${CONTENTS}/MacOS/apphost-${arch}" "${CONTENTS}/MacOS/${arch}/libhostfxr.dylib" "${CONTENTS}/MacOS/${arch}/OpenRA.Utility.dll" "${mode}" --check-standalone --strict | tee "${WORK}/standalone-${arch}-${mode}.log"
	fi

	ENGINE_DIR="${WORK}/utility-engine" "${prefix[@]}" "${CONTENTS}/MacOS/apphost-${arch}" "${CONTENTS}/MacOS/${arch}/libhostfxr.dylib" "${CONTENTS}/MacOS/${arch}/OpenRA.Utility.dll" "${mode}" --check-voice-language | tee "${WORK}/voice-${arch}-${mode}.log"

	echo "== Headless skirmish (${arch}), ${SECONDS_TO_RUN}s"
	local map=twin-fords
	[ "${mode}" != "rtsai-topdown" ] || map=classic-frontier
	local support="${WORK}/support-${arch}-${mode}"
	rm -rf "${support}"
	mkdir -p "${support}"
	# What Contents/MacOS/Launcher runs, with the no-op platform instead of a window.
	(cd "${RESOURCES}" && exec "${CONTENTS}/MacOS/apphost-${arch}" "${CONTENTS}/MacOS/${arch}/libhostfxr.dylib" \
		"${CONTENTS}/MacOS/${arch}/OpenRA.dll" "Engine.LaunchPath=${CONTENTS}/MacOS/Launcher" \
		"Engine.EngineDir=${RESOURCES}" "Game.Mod=${mode}" "Engine.SupportDir=${support}" \
		Game.Platform=Null Game.FetchNews=false Sound.Mute=true \
		Launch.Map="${map}" Launch.Bots=Multi0:normal:china,Multi1:normal:iran) > "${WORK}/game-${arch}-${mode}.log" 2>&1 &
	local pid=$!
	local waited=0
	while kill -0 "${pid}" 2>/dev/null && [ "${waited}" -lt "${SECONDS_TO_RUN}" ]; do
		sleep 1
		waited=$((waited + 1))
	done
	if kill -0 "${pid}" 2>/dev/null; then
		kill "${pid}"
		wait "${pid}" 2>/dev/null || true
	else
		wait "${pid}" || true
		tail -n 20 "${WORK}/game-${arch}-${mode}.log"
		fail "the game (${arch}) exited after ${waited}s"
	fi
	head -n 6 "${WORK}/game-${arch}-${mode}.log"
	ls "${support}/Logs" || fail "no logs (${arch})"
	if [ -s "${support}/Logs/exception.log" ]; then
		tail -n 30 "${support}/Logs/exception.log"
		fail "exception.log (${arch})"
	fi
	if grep -l "Exception" "${support}/Logs/"*.log 2>/dev/null; then
		grep -h "Exception" "${support}/Logs/"*.log | head -n 10
		fail "exceptions in the logs (${arch})"
	fi
	grep -h "AI choice\|mode off" "${support}/Logs/companion.log" 2>/dev/null || true
	local replay
	replay="$(find "${support}/Replays" -name '*.orarep' -size +1k 2>/dev/null | head -n 1)"
	[ -n "${replay}" ] || fail "no replay: the skirmish did not start (${arch})"
	echo "skirmish ran ${waited}s (${arch}), replay $(basename "${replay}") $(stat -f %z "${replay}") bytes"
}

ditto "${RESOURCES}" "${WORK}/utility-engine"
mkdir -p "${WORK}/utility-engine/Support"
native="$(uname -m)"
for mode in rtsai rtsai-topdown; do run_checks "${native}" "${mode}"; done
if [ "${native}" = "arm64" ]; then
	if arch -x86_64 /usr/bin/true 2>/dev/null; then
		for mode in rtsai rtsai-topdown; do run_checks x86_64 "${mode}"; done
	else
		echo "== Rosetta 2 is not installed on this host: the Intel slice was built but not run here"
	fi
fi

echo "SMOKE PASS: ${DMG}"
