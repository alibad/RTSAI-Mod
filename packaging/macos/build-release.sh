#!/bin/bash
# Build the RTS AI macOS release on a macOS host: one universal (Apple silicon + Intel) app in a disk image.
#
# The Mod SDK's buildpackage.sh in this folder predates the .NET engine (it compiles the Mono launchers, which the
# engine no longer has). This script follows the engine's own packaging/macos/buildpackage.sh instead: it
# publishes the engine and the mod self-contained for osx-arm64 and osx-x64, compiles the launcher, the
# apphosts and the Utility wrapper with clang and writes
#
#     <outputdir>/RTSAI-<version>-macos.dmg          "RTS AI.app" next to an Applications link
#     <outputdir>/RTSAI-<version>-macos.dmg.sha256
#     <outputdir>/BUILD-INPUTS-macos.json            the mod and engine commits, the shipped mods
#
# The payload matches the Windows build (packaging/windows/build-release.ps1): PACKAGING_STANDALONE="True" ships only
# the mods named in PACKAGING_STANDALONE_MODS (the desktop Library, its three games, Classic's content installer and
# the RTS game's top-down mode; never the owned-RA2 add-ons) and the app opens PACKAGING_LAUNCHER_MOD_ID (the Library).
# The engine's content installer chrome and MIX filename database ship only when a shipped mod uses them (Classic
# downloads the freeware Red Alert content on first start); no Westwood archives ship. An optional frozen companion
# is local by default.
#
# The engine is the canonical sibling checkout ../OpenRA (or RTSAI_MAC_ENGINE), like tools/build-desktop-recovery.ps1:
# both repositories are fast-forwarded to their owner main (github.com/alibad) and must be clean, so the release is
# built from committed main only. Resources/VERSION is the engine commit; the ENGINE_VERSION pin is not used here.
#
# Signing: with MACOS_DEVELOPER_IDENTITY (a Developer ID Application identity in the keychain) the app is signed
# with the hardened runtime; otherwise it is ad-hoc signed (codesign -s -), which Gatekeeper treats as an
# unidentified developer: the player approves it once. Notarization is not done here.
#
# Requirements: macOS, git, .NET 10 SDK, Xcode command line tools (clang, lipo, codesign, iconutil, hdiutil).
#
# usage: packaging/macos/build-release.sh <version> <outputdir>
set -o errexit -o pipefail

if [[ "${OSTYPE}" != "darwin"* ]]; then
	echo >&2 "macOS packaging requires a macOS host"
	exit 1
fi

for tool in git clang lipo codesign iconutil hdiutil dotnet shasum perl; do
	command -v "${tool}" >/dev/null 2>&1 || { echo >&2 "macOS packaging requires ${tool}."; exit 1; }
done

if [ $# -ne 2 ]; then
	echo "usage: $(basename "$0") <version> <outputdir>"
	exit 1
fi

VERSION="$1"
mkdir -p "$2"
OUTPUTDIR="$(cd "$2" && pwd)"
PACKAGING_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${PACKAGING_DIR}/../.." && pwd)"
ARTWORK_DIR="${ROOT}/packaging/artwork"

# shellcheck source=mod.config
. "${ROOT}/mod.config"
if [ -f "${ROOT}/user.config" ]; then
	# shellcheck source=user.config
	. "${ROOT}/user.config"
fi

# mod.config's ENGINE_DIRECTORY (./engine) is an old engine copy, and RTSAI.sln names its projects.
ENGINE="${RTSAI_MAC_ENGINE:-$(cd "${ROOT}/.." && pwd)/OpenRA}"
ENGINE_MACOS="${ENGINE}/packaging/macos"
if [ ! -f "${ENGINE}/OpenRA.Game/OpenRA.Game.csproj" ] || [ ! -f "${ENGINE_MACOS}/launcher.m" ]; then
	echo >&2 "No engine checkout in ${ENGINE} (the canonical OpenRA checkout next to this one, or set RTSAI_MAC_ENGINE)."
	exit 1
fi
ENGINE="$(cd "${ENGINE}" && pwd)"
ENGINE_MACOS="${ENGINE}/packaging/macos"

# Committed main only. The owner's remote is found by its URL: a Mac checkout may not call it origin or fork.
update_to_main() {
	local remote
	remote="$(git -C "$1" remote -v | awk -v repo="$2" '$3 == "(fetch)" && $2 ~ ("github[.]com[:/]alibad/" repo "([.]git)?$") { print $1; exit }')"
	[ -n "${remote}" ] || { echo >&2 "$1 has no remote for github.com/alibad/$2."; exit 1; }
	[ "$(git -C "$1" rev-parse --abbrev-ref HEAD)" = "main" ] || { echo >&2 "$1 is not on main."; exit 1; }
	git -C "$1" fetch "${remote}" main
	git -C "$1" merge --ff-only "${remote}/main" || { echo >&2 "$1 cannot fast-forward to ${remote}/main."; exit 1; }
	[ -z "$(git -C "$1" status --porcelain)" ] || { echo >&2 "Commit source changes before building: $1"; exit 1; }
}
update_to_main "${ROOT}" RTSAI-Mod
update_to_main "${ENGINE}" OpenRA
MOD_COMMIT="$(git -C "${ROOT}" rev-parse HEAD)"
ENGINE_COMMIT="$(git -C "${ENGINE}" rev-parse HEAD)"

STANDALONE="${PACKAGING_STANDALONE:-False}"
LAUNCHER_MOD="${PACKAGING_LAUNCHER_MOD_ID:-${MOD_ID}}"
if [ "${STANDALONE}" = "True" ]; then
	# The desktop Library and its games, sharing authored content; never the owned-RA2 add-ons.
	MODS="${PACKAGING_STANDALONE_MODS:-${MOD_ID}}"
	for mod in ${MODS}; do
		[ -d "${ROOT}/mods/${mod}" ] || { echo >&2 "PACKAGING_STANDALONE_MODS names a mod that does not exist: ${mod}"; exit 1; }
	done
else
	MODS=""
	for mod in "${ROOT}/mods/"*/; do
		MODS="${MODS} $(basename "${mod}")"
	done
fi
case " ${MODS} " in
	*" ${LAUNCHER_MOD} "*) [ -f "${ROOT}/mods/${LAUNCHER_MOD}/mod.yaml" ] ;;
	*) false ;;
esac || { echo >&2 "No mods/${LAUNCHER_MOD} to package."; exit 1; }
MANIFESTS=()
for mod in ${MODS}; do
	if [ -f "${ROOT}/mods/${mod}/mod.yaml" ]; then
		MANIFESTS+=("${ROOT}/mods/${mod}/mod.yaml")
	fi
done
# Classic mounts the freeware Red Alert archives its content installer downloads on first start.
CONTENT_INSTALLER="True"
MIX_ARCHIVES="True"
if [ "${STANDALONE}" = "True" ]; then
	grep -Eq '^[[:space:]]*ContentInstallerMod:' "${MANIFESTS[@]}" || CONTENT_INSTALLER="False"
	grep -Eq '^PackageFormats:(.*[[:space:],])?Mix([[:space:],]|$)' "${MANIFESTS[@]}" || MIX_ARCHIVES="False"
fi

APP_NAME="${PACKAGING_DISPLAY_NAME}.app"
DMG="${OUTPUTDIR}/${PACKAGING_INSTALLER_NAME}-${VERSION}-macos.dmg"
# Outside the repository, which must stay clean between builds.
BUILT="${RTSAI_MAC_BUILD_ROOT:-${TMPDIR:-/tmp}/rtsai-macos-build}"
APP="${BUILT}/${APP_NAME}"
CONTENTS="${APP}/Contents"
RESOURCES="${CONTENTS}/Resources"

rm -rf "${BUILT}"
mkdir -p "${CONTENTS}/MacOS/x86_64" "${CONTENTS}/MacOS/arm64" "${RESOURCES}/mods"

modify_plist() {
	sed "s|${1}|${2}|g" "${3}" > "${3}.tmp" && mv "${3}.tmp" "${3}"
}

echo "== Launchers"
echo "APPL????" > "${CONTENTS}/PkgInfo"
PLIST="${CONTENTS}/Info.plist"
cp "${ENGINE_MACOS}/Info.plist.in" "${PLIST}"
modify_plist "{DEV_VERSION}" "${VERSION}" "${PLIST}"
modify_plist "{FAQ_URL}" "${PACKAGING_FAQ_URL}" "${PLIST}"
# .NET 10 requires macOS 15 and later.
modify_plist "{MINIMUM_SYSTEM_VERSION}" "15.0" "${PLIST}"
# The Launcher opens ModId (the Library); the bundle id, icon and URL scheme keep MOD_ID, as RTSAI.exe keeps its
# registry key.
LAUNCHER_MOD="${LAUNCHER_MOD}" perl -0pi -e 's|(<key>ModId</key>\s*<string>)\{MOD_ID\}|$1$ENV{LAUNCHER_MOD}|' "${PLIST}"
modify_plist "{MOD_ID}" "${MOD_ID}" "${PLIST}"
modify_plist "{MOD_NAME}" "${PACKAGING_DISPLAY_NAME}" "${PLIST}"
modify_plist "{JOIN_SERVER_URL_SCHEME}" "openra-${MOD_ID}-${VERSION}" "${PLIST}"
if [ -n "${PACKAGING_DISCORD_APPID}" ]; then
	modify_plist "{DISCORD_URL_SCHEME}" "discord-${PACKAGING_DISCORD_APPID}" "${PLIST}"
else
	modify_plist "<string>{DISCORD_URL_SCHEME}</string>" "" "${PLIST}"
fi
plutil -lint "${PLIST}"
[ "$(plutil -extract ModId raw "${PLIST}")" = "${LAUNCHER_MOD}" ] || { echo >&2 "Info.plist ModId is not ${LAUNCHER_MOD}"; exit 1; }

clang "${ENGINE_MACOS}/apphost.c" -o "${CONTENTS}/MacOS/apphost-x86_64" -framework AppKit -target x86_64-apple-macos10.15
clang "${ENGINE_MACOS}/apphost.c" -o "${CONTENTS}/MacOS/apphost-arm64" -framework AppKit -target arm64-apple-macos10.15
clang "${ENGINE_MACOS}/launcher.m" -o "${CONTENTS}/MacOS/Launcher" -framework AppKit -arch x86_64 -arch arm64 -mmacosx-version-min=10.15
clang "${ENGINE_MACOS}/utility.m" -o "${CONTENTS}/MacOS/Utility" -framework AppKit -arch x86_64 -arch arm64 -mmacosx-version-min=10.15

for target in x86_64:osx-x64 arm64:osx-arm64; do
	ARCH="${target%%:*}"
	RID="${target##*:}"
	echo "== Engine and mod assemblies (${RID}, self-contained)"
	(cd "${ENGINE}" && dotnet publish -c Release -p:TargetPlatform="${RID}" -p:CopyGenericLauncher=True \
		-p:CopyCncDll="${PACKAGING_COPY_CNC_DLL}" -p:CopyD2kDll="${PACKAGING_COPY_D2K_DLL}" -r "${RID}" \
		-p:PublishDir="${CONTENTS}/MacOS/${ARCH}/" -p:Deterministic=true --self-contained true --nologo -v q)
	ENGINE_SUMS="$(cd "${CONTENTS}/MacOS/${ARCH}" && shasum -a 256 OpenRA.Game.dll OpenRA.Mods.Common.dll OpenRA.Mods.Cnc.dll)"
	# The mod projects alone: RTSAI.sln names the old ./engine projects, and publishing it overwrote the engine's
	# assemblies with that copy's. The engine references are Private=False, so only the mod assemblies are added.
	for project in OpenRA.Mods.RA2 OpenRA.Mods.RTSAI; do
		(cd "${ROOT}" && dotnet publish "${project}/${project}.csproj" -p:EngineRootPath="${ENGINE}/" -c Release -p:TargetPlatform="${RID}" -r "${RID}" \
			-p:PublishDir="${CONTENTS}/MacOS/${ARCH}/" --self-contained true --nologo -v q)
	done
	(cd "${CONTENTS}/MacOS/${ARCH}" && printf '%s\n' "${ENGINE_SUMS}" | shasum -a 256 -s -c) || {
		echo >&2 "The mod publish replaced an engine assembly (${ARCH})."
		exit 1
	}
	for required in OpenRA.dll OpenRA.Utility.dll libhostfxr.dylib OpenRA.Mods.RTSAI.dll; do
		[ -f "${CONTENTS}/MacOS/${ARCH}/${required}" ] || { echo >&2 "Missing ${ARCH}/${required}"; exit 1; }
	done
done

echo "== Engine data"
# The engine archive has no GeoIP database; the engine's install_data fetches it the same way.
bash "${ENGINE}/fetch-geoip.sh"
for file in AUTHORS COPYING IP2LOCATION-LITE-DB1.IPV6.BIN.ZIP; do
	cp "${ENGINE}/${file}" "${RESOURCES}/"
done
if [ "${MIX_ARCHIVES}" = "True" ]; then
	# The MIX filename database only serves Westwood archives.
	cp "${ENGINE}/global mix database.dat" "${RESOURCES}/"
fi
cp -R "${ENGINE}/glsl" "${RESOURCES}/"
cp -R "${ENGINE}/mods/common" "${RESOURCES}/mods/"
if [ "${CONTENT_INSTALLER}" = "True" ]; then
	# mods/common-content is the content installer's chrome.
	for extra in ${PACKAGING_COPY_ENGINE_FILES}; do
		extra="${extra#./}"
		mkdir -p "${RESOURCES}/$(dirname "${extra}")"
		cp -R "${ENGINE}/${extra}" "${RESOURCES}/${extra}"
	done
fi
echo "${ENGINE_COMMIT}" > "${RESOURCES}/VERSION"

echo "== Mod content: ${MODS}"
for mod in ${MODS}; do
	cp -LR "${ROOT}/mods/${mod}" "${RESOURCES}/mods/"
	if [ -f "${RESOURCES}/mods/${mod}/mod.yaml" ]; then
		# The SDK's set_mod_version: the release tag replaces the development placeholder.
		VERSION="${VERSION}" perl -pi -e 's/\{DEV_VERSION\}/$ENV{VERSION}/g' "${RESOURCES}/mods/${mod}/mod.yaml"
	fi
done
[ -f "${RESOURCES}/mods/${LAUNCHER_MOD}/mod.yaml" ] || { echo >&2 "No mods/${LAUNCHER_MOD} to package."; exit 1; }

AI_MODE="none"
if [ -n "${RTSAI_MAC_COMPANION}" ]; then
	[ -x "${RTSAI_MAC_COMPANION}/rtsai-companion" ] || { echo >&2 "Missing frozen companion executable"; exit 1; }
	cp -R "${RTSAI_MAC_COMPANION}" "${RESOURCES}/companion"
	AI_MODE="local"
fi
printf '{"ai_mode": "%s", "version": "%s", "stamp": "macos-%s", "hosted_enabled": false, "companion_arch": "%s"}\n' "${AI_MODE}" "${VERSION}" "${VERSION}" "${RTSAI_MAC_COMPANION_ARCH:-none}" > "${RESOURCES}/rtsai-install.json"

echo "== Icon"
ICONSET="${BUILT}/${MOD_ID}.iconset"
mkdir "${ICONSET}"
cp "${ARTWORK_DIR}/icon_16x16.png" "${ICONSET}/icon_16x16.png"
cp "${ARTWORK_DIR}/icon_32x32.png" "${ICONSET}/icon_16x16@2x.png"
cp "${ARTWORK_DIR}/icon_32x32.png" "${ICONSET}/icon_32x32.png"
cp "${ARTWORK_DIR}/icon_64x64.png" "${ICONSET}/icon_32x32@2x.png"
cp "${ARTWORK_DIR}/icon_128x128.png" "${ICONSET}/icon_128x128.png"
cp "${ARTWORK_DIR}/icon_256x256.png" "${ICONSET}/icon_128x128@2x.png"
cp "${ARTWORK_DIR}/icon_256x256.png" "${ICONSET}/icon_256x256.png"
cp "${ARTWORK_DIR}/icon_512x512.png" "${ICONSET}/icon_256x256@2x.png"
cp "${ARTWORK_DIR}/icon_512x512.png" "${ICONSET}/icon_512x512.png"
cp "${ARTWORK_DIR}/icon_1024x1024.png" "${ICONSET}/icon_512x512@2x.png"
iconutil --convert icns "${ICONSET}" -o "${RESOURCES}/${MOD_ID}.icns"
rm -rf "${ICONSET}"

echo "== Deduplicating runtime files between architectures"
for f in "${CONTENTS}/MacOS/x86_64"/*; do
	g="${CONTENTS}/MacOS/arm64/$(basename "${f}")"
	if [ -f "${f}" ] && [ -f "${g}" ] && cmp -s "${f}" "${g}"; then
		rm "${f}"
		ln "${g}" "${f}"
	fi
done

echo "== Signing"
if [ -n "${MACOS_DEVELOPER_IDENTITY}" ]; then
	codesign --sign "${MACOS_DEVELOPER_IDENTITY}" --timestamp --options runtime --force \
		--entitlements "${ENGINE_MACOS}/entitlements.plist" --deep "${APP}"
	SIGNING="Developer ID"
else
	codesign --sign - --force --deep "${APP}"
	SIGNING="ad-hoc"
fi
codesign --verify --deep --strict --verbose=2 "${APP}"

echo "== Disk image"
ln -s /Applications "${BUILT}/Applications"
rm -f "${DMG}"
hdiutil create "${DMG}" -volname "${PACKAGING_DISPLAY_NAME}" -fs HFS+ -format UDZO -imagekey zlib-level=9 -srcfolder "${BUILT}"
(cd "${OUTPUTDIR}" && shasum -a 256 "$(basename "${DMG}")" > "$(basename "${DMG}").sha256")
MODS_JSON="$(printf '"%s", ' ${MODS})"
printf '{"version": "%s", "modCommit": "%s", "engineCommit": "%s", "launcherMod": "%s", "mods": [%s], "companion": %s, "signing": "%s", "artifacts": ["%s"]}\n' \
	"${VERSION}" "${MOD_COMMIT}" "${ENGINE_COMMIT}" "${LAUNCHER_MOD}" "${MODS_JSON%, }" "$([ "${AI_MODE}" = "local" ] && echo true || echo false)" \
	"${SIGNING}" "$(cat "${DMG}.sha256")" > "${OUTPUTDIR}/BUILD-INPUTS-macos.json"
if [ "${RTSAI_MAC_KEEP_BUILD:-0}" = "1" ]; then
	echo "Kept the build in ${BUILT}"
else
	rm -rf "${BUILT}"
fi

echo "Built ${DMG} ($(stat -f %z "${DMG}") bytes, ${SIGNING} signature; mod ${MOD_COMMIT:0:7}, engine ${ENGINE_COMMIT:0:7})"
