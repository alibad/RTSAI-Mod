#!/bin/bash
# Smoke-test a macOS release disk image from packaging/macos/build-release.sh on a macOS host (CI or a Mac).
#
#  1. the .sha256 matches; the image mounts; the app copies out the way a player installs it
#  2. the bundle: strict code signature check, Info.plist version and ModId (the Library), universal launchers,
#     Resources/VERSION is an engine commit
#  3. the payload: the engine's common files and the mods in PACKAGING_STANDALONE_MODS, the content installer chrome
#     and the MIX filename database exactly when a shipped mod uses them, no Westwood archives or videos
#  4. the native Utility wrapper loads every shipped mod (--check-yaml), the RA2 and RTS games and the top-down mode
#     load nothing from Red Alert 2 (--check-standalone --strict), and the RTS voices resolve (--check-voice-language)
#  5. headless (Game.Platform=Null): the Library opens and stays up, and each game boots into a bot skirmish on a
#     shipped map for --seconds, writes a replay and logs no exception, like packaging/windows/test-installed-release.ps1.
#     Classic needs the freeware Red Alert content: RTSAI_MAC_CLASSIC_CONTENT=<a Content folder holding ra/v2, as
#     Classic installs it> runs its skirmish; without it the skirmish is reported as not run.
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
LAUNCHER_MOD="${PACKAGING_LAUNCHER_MOD_ID:-${MOD_ID}}"
APP_NAME="${PACKAGING_DISPLAY_NAME}.app"
CLASSIC_CONTENT="${RTSAI_MAC_CLASSIC_CONTENT:-}"
if [ -n "${CLASSIC_CONTENT}" ] && [ ! -d "${CLASSIC_CONTENT}/ra/v2" ]; then
	echo "RTSAI_MAC_CLASSIC_CONTENT must be a Content folder holding ra/v2: ${CLASSIC_CONTENT}" >&2
	exit 1
fi

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
[ "$(plutil -extract ModId raw "${CONTENTS}/Info.plist")" = "${LAUNCHER_MOD}" ] || fail "Info.plist ModId is not ${LAUNCHER_MOD}"
[ "$(plutil -extract CFBundleExecutable raw "${CONTENTS}/Info.plist")" = "Launcher" ] || fail "Info.plist executable"
for binary in Launcher Utility; do
	archs="$(lipo -archs "${CONTENTS}/MacOS/${binary}")"
	[[ "${archs}" == *x86_64* && "${archs}" == *arm64* ]] || fail "${binary} is not universal (${archs})"
done
[ -f "${RESOURCES}/${MOD_ID}.icns" ] || fail "no icon"
grep -q "Version: ${VERSION}" "${RESOURCES}/mods/${LAUNCHER_MOD}/mod.yaml" || fail "mod.yaml version"
grep -Eq '^[0-9a-f]{40}$' "${RESOURCES}/VERSION" || fail "Resources/VERSION is not an engine commit"
echo "engine: $(cat "${RESOURCES}/VERSION")"

echo "== Payload"
mods="$(cd "${RESOURCES}/mods" && ls | LC_ALL=C sort | tr '\n' ' ')"
echo "mods: ${mods}"
if [ "${STANDALONE}" = "True" ]; then
	manifests=("${RESOURCES}/mods/"*/mod.yaml)
	expected="common ${PACKAGING_STANDALONE_MODS:-${MOD_ID}}"
	# Classic's content installer (rtsai-classic-content) uses the engine's chrome in mods/common-content.
	if grep -Eq '^[[:space:]]*ContentInstallerMod:' "${manifests[@]}"; then
		for extra in ${PACKAGING_COPY_ENGINE_FILES}; do
			extra="${extra#./}"
			[ -e "${RESOURCES}/${extra}" ] || fail "no ${extra} for the content installer"
			if [[ "${extra}" == mods/* ]]; then
				expected="${expected} ${extra#mods/}"
			fi
		done
	fi
	expected="$(printf '%s\n' ${expected} | LC_ALL=C sort | tr '\n' ' ')"
	[ "${mods}" = "${expected}" ] || fail "the standalone build must ship ${expected}"
	if grep -Eq '^PackageFormats:(.*[[:space:],])?Mix([[:space:],]|$)' "${manifests[@]}"; then
		[ -f "${RESOURCES}/global mix database.dat" ] || fail "no MIX filename database for the freeware Red Alert content"
	else
		[ ! -e "${RESOURCES}/global mix database.dat" ] || fail "MIX filename database without a game that reads MIX archives"
	fi
fi
archives="$(find "${APP}" -type f \( -iname '*.mix' -o -iname '*.bag' -o -iname '*.idx' -o -iname '*.vqa' -o -iname '*.big' -o -iname '*.wsa' -o -iname '*.bik' \) | head -5)"
[ -z "${archives}" ] || fail "Westwood archives or videos in the app: ${archives}"
du -sh "${APP}"

utility() {
	local arch="$1" mode="$2" prefix=()
	shift 2
	[ "${arch}" = "x86_64" ] && prefix=(arch -x86_64)
	echo "== Utility (${arch}): ${mode} $*"
	ENGINE_DIR="${WORK}/utility-engine" "${prefix[@]}" "${CONTENTS}/MacOS/apphost-${arch}" "${CONTENTS}/MacOS/${arch}/libhostfxr.dylib" \
		"${CONTENTS}/MacOS/${arch}/OpenRA.Utility.dll" "${mode}" "$@" | tee "${WORK}/utility-${arch}-${mode}${1}.log"
}

# What Contents/MacOS/Launcher runs, with the no-op platform instead of a window. Fails if the game exits within
# <seconds> or logs an exception.
run_game() {
	local arch="$1" mode="$2" support="$3" seconds="$4" log="$5"
	shift 5
	(cd "${RESOURCES}" && exec "${CONTENTS}/MacOS/apphost-${arch}" "${CONTENTS}/MacOS/${arch}/libhostfxr.dylib" \
		"${CONTENTS}/MacOS/${arch}/OpenRA.dll" "Engine.LaunchPath=${CONTENTS}/MacOS/Launcher" \
		"Engine.EngineDir=${RESOURCES}" "Game.Mod=${mode}" "Engine.SupportDir=${support}" \
		Game.Platform=Null Game.FetchNews=false Sound.Mute=true "$@") > "${log}" 2>&1 &
	local pid=$!
	local waited=0
	while kill -0 "${pid}" 2>/dev/null && [ "${waited}" -lt "${seconds}" ]; do
		sleep 1
		waited=$((waited + 1))
	done
	if kill -0 "${pid}" 2>/dev/null; then
		kill "${pid}"
		wait "${pid}" 2>/dev/null || true
	else
		wait "${pid}" || true
		tail -n 20 "${log}"
		fail "${mode} (${arch}) exited after ${waited}s"
	fi
	head -n 6 "${log}"
	ls "${support}/Logs" || fail "no logs: ${mode} (${arch})"
	if [ -s "${support}/Logs/exception.log" ]; then
		tail -n 30 "${support}/Logs/exception.log"
		fail "exception.log: ${mode} (${arch})"
	fi
	if grep -l "Exception" "${support}/Logs/"*.log 2>/dev/null; then
		grep -h "Exception" "${support}/Logs/"*.log | head -n 10
		fail "exceptions in the logs: ${mode} (${arch})"
	fi
}

skirmish() {
	local arch="$1" mode="$2" map="$3" bots="$4"
	local support="${WORK}/support-${arch}-${mode}"
	[ -d "${RESOURCES}/mods/${mode}" ] || fail "${mode} is not in the app"
	if [ "${mode}" = "rtsai-classic-core" ] && [ -z "${CLASSIC_CONTENT}" ]; then
		echo "== Headless skirmish (${arch}): ${mode} NOT RUN (set RTSAI_MAC_CLASSIC_CONTENT to the freeware Red Alert content)"
		return
	fi
	echo "== Headless skirmish (${arch}): ${mode} on ${map}, ${SECONDS_TO_RUN}s"
	rm -rf "${support}"
	mkdir -p "${support}"
	if [ "${mode}" = "rtsai-classic-core" ]; then
		ditto "${CLASSIC_CONTENT}" "${support}/Content"
	fi
	run_game "${arch}" "${mode}" "${support}" "${SECONDS_TO_RUN}" "${WORK}/game-${arch}-${mode}.log" \
		"Launch.Map=${map}" "Launch.Bots=${bots}"
	grep -h "AI choice\|mode off" "${support}/Logs/companion.log" 2>/dev/null || true
	local replay
	replay="$(find "${support}/Replays" -name '*.orarep' -size +1k 2>/dev/null | head -n 1)"
	[ -n "${replay}" ] || fail "no replay: the ${mode} skirmish did not start (${arch})"
	echo "${mode} skirmish ran (${arch}), replay $(basename "${replay}") $(stat -f %z "${replay}") bytes"
}

run_checks() {
	local arch="$1" mode
	for mode in $(cd "${RESOURCES}/mods" && ls); do
		[ "${mode}" != "common" ] && [ "${mode}" != "common-content" ] || continue
		utility "${arch}" "${mode}" --check-yaml
	done
	if [ "${STANDALONE}" = "True" ]; then
		for mode in rtsai-ra2 rtsai rtsai-topdown; do
			utility "${arch}" "${mode}" --check-standalone --strict
		done
	fi
	for mode in rtsai rtsai-topdown; do
		utility "${arch}" "${mode}" --check-voice-language
	done

	echo "== Headless Library (${arch}): ${LAUNCHER_MOD} stays open 20s"
	local support="${WORK}/support-${arch}-${LAUNCHER_MOD}"
	rm -rf "${support}"
	mkdir -p "${support}"
	run_game "${arch}" "${LAUNCHER_MOD}" "${support}" 20 "${WORK}/game-${arch}-${LAUNCHER_MOD}.log"

	# The maps and factions packaging/windows/test-installed-release.ps1 plays, and the top-down mode's own map.
	skirmish "${arch}" rtsai-classic-core a-nuclear-winter Multi0:normal:england,Multi1:normal:russia
	skirmish "${arch}" rtsai-ra2 ra2-defcon-6 Multi0:normal:america,Multi1:normal:russia
	skirmish "${arch}" rtsai ra2-defcon-6 Multi0:normal:china,Multi1:normal:iran
	skirmish "${arch}" rtsai-topdown classic-frontier Multi0:normal:china,Multi1:normal:iran
}

ditto "${RESOURCES}" "${WORK}/utility-engine"
mkdir -p "${WORK}/utility-engine/Support"
native="$(uname -m)"
run_checks "${native}"
if [ "${native}" = "arm64" ]; then
	if arch -x86_64 /usr/bin/true 2>/dev/null; then
		run_checks x86_64
	else
		echo "== Rosetta 2 is not installed on this host: the Intel slice was built but not run here"
	fi
fi

echo "SMOKE PASS: ${DMG}"
