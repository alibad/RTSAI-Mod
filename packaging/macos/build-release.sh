#!/bin/bash
# Build the RTS AI macOS release on a macOS host: one universal (Apple silicon + Intel) app in a disk image.
#
# The Mod SDK's buildpackage.sh in this folder predates the .NET engine (it compiles the Mono launchers, which the
# pinned engine no longer has). This script follows the engine's own packaging/macos/buildpackage.sh instead: it
# publishes the pinned engine and the mod self-contained for osx-arm64 and osx-x64, compiles the launcher, the
# apphosts and the Utility wrapper with clang and writes
#
#     <outputdir>/RTSAI-<version>-macos.dmg          "RTS AI.app" next to an Applications link
#     <outputdir>/RTSAI-<version>-macos.dmg.sha256
#
# The payload matches the Windows build (packaging/windows/build-release.ps1): with PACKAGING_STANDALONE="True"
# only mods/<MOD_ID> ships, without the MIX filename database or the content installer's chrome. The AI companion
# is Windows-only today, so the co-commander starts off (rtsai-install.json "none").
#
# Signing: with MACOS_DEVELOPER_IDENTITY (a Developer ID Application identity in the keychain) the app is signed
# with the hardened runtime; otherwise it is ad-hoc signed (codesign -s -), which Gatekeeper treats as an
# unidentified developer: the player approves it once. Notarization is not done here.
#
# Requirements: macOS, .NET 10 SDK, Xcode command line tools (clang, lipo, codesign, iconutil, hdiutil).
# Run ./fetch-engine.sh first so ./engine exists.
#
# usage: packaging/macos/build-release.sh <version> <outputdir>
set -o errexit -o pipefail

if [[ "${OSTYPE}" != "darwin"* ]]; then
	echo >&2 "macOS packaging requires a macOS host"
	exit 1
fi

for tool in clang lipo codesign iconutil hdiutil dotnet shasum perl; do
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

ENGINE="${ROOT}/${ENGINE_DIRECTORY#./}"
ENGINE_MACOS="${ENGINE}/packaging/macos"
if [ ! -f "${ENGINE}/OpenRA.Game/OpenRA.Game.csproj" ] || [ ! -f "${ENGINE_MACOS}/launcher.m" ]; then
	echo >&2 "The pinned engine is missing in ${ENGINE}. Run ./fetch-engine.sh first."
	exit 1
fi

STANDALONE="${PACKAGING_STANDALONE:-False}"
APP_NAME="${PACKAGING_DISPLAY_NAME}.app"
DMG="${OUTPUTDIR}/${PACKAGING_INSTALLER_NAME}-${VERSION}-macos.dmg"
BUILT="${PACKAGING_DIR}/build"
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
# Lets older macOS try to start; Microsoft supports .NET 10 on macOS 15 and later.
modify_plist "{MINIMUM_SYSTEM_VERSION}" "12.0" "${PLIST}"
modify_plist "{MOD_ID}" "${MOD_ID}" "${PLIST}"
modify_plist "{MOD_NAME}" "${PACKAGING_DISPLAY_NAME}" "${PLIST}"
modify_plist "{JOIN_SERVER_URL_SCHEME}" "openra-${MOD_ID}-${VERSION}" "${PLIST}"
if [ -n "${PACKAGING_DISCORD_APPID}" ]; then
	modify_plist "{DISCORD_URL_SCHEME}" "discord-${PACKAGING_DISCORD_APPID}" "${PLIST}"
else
	modify_plist "<string>{DISCORD_URL_SCHEME}</string>" "" "${PLIST}"
fi
plutil -lint "${PLIST}"

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
	(cd "${ROOT}" && dotnet publish RTSAI.sln -c Release -p:TargetPlatform="${RID}" -r "${RID}" \
		-p:PublishDir="${CONTENTS}/MacOS/${ARCH}/" --self-contained true --nologo -v q)
	for required in OpenRA.dll OpenRA.Utility.dll libhostfxr.dylib OpenRA.Mods.RTSAI.dll; do
		[ -f "${CONTENTS}/MacOS/${ARCH}/${required}" ] || { echo >&2 "Missing ${ARCH}/${required}"; exit 1; }
	done
done

echo "== Engine data"
for file in VERSION AUTHORS COPYING IP2LOCATION-LITE-DB1.IPV6.BIN.ZIP; do
	cp "${ENGINE}/${file}" "${RESOURCES}/"
done
cp -R "${ENGINE}/glsl" "${RESOURCES}/"
cp -R "${ENGINE}/mods/common" "${RESOURCES}/mods/"
if [ "${STANDALONE}" != "True" ]; then
	# The MIX filename database and the content installer's chrome only serve the RA2-based mod.
	cp "${ENGINE}/global mix database.dat" "${RESOURCES}/"
	for extra in ${PACKAGING_COPY_ENGINE_FILES}; do
		extra="${extra#./}"
		mkdir -p "${RESOURCES}/$(dirname "${extra}")"
		cp -R "${ENGINE}/${extra}" "${RESOURCES}/${extra}"
	done
fi
echo "${ENGINE_VERSION}" > "${RESOURCES}/VERSION"

echo "== Mod content"
for mod in "${ROOT}/mods/"*/; do
	mod="$(basename "${mod}")"
	if [ "${STANDALONE}" = "True" ] && [ "${mod}" != "${MOD_ID}" ]; then
		continue
	fi
	cp -LR "${ROOT}/mods/${mod}" "${RESOURCES}/mods/"
	if [ -f "${RESOURCES}/mods/${mod}/mod.yaml" ]; then
		# The SDK's set_mod_version: the release tag replaces the development placeholder.
		VERSION="${VERSION}" perl -pi -e 's/\{DEV_VERSION\}/$ENV{VERSION}/g' "${RESOURCES}/mods/${mod}/mod.yaml"
	fi
done
[ -f "${RESOURCES}/mods/${MOD_ID}/mod.yaml" ] || { echo >&2 "No mods/${MOD_ID} to package."; exit 1; }

# No AI companion on macOS yet: the co-commander starts off (CompanionHost applies this once) and the game says the
# build does not include it, instead of reporting missing files.
printf '{"ai_mode": "none", "version": "%s", "stamp": "macos-%s"}\n' "${VERSION}" "${VERSION}" > "${RESOURCES}/rtsai-install.json"

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
rm -rf "${BUILT}"

echo "Built ${DMG} ($(stat -f %z "${DMG}") bytes, ${SIGNING} signature)"
