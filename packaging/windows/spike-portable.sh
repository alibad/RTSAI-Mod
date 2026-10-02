#!/bin/bash
# Spike: reproduce the dotnet half of packaging/windows/buildpackage.sh natively on
# Windows (Git Bash) without wine, makensis, ImageMagick or rcedit, producing an
# unzipped "winportable" directory that can be launched and inspected.
#
# Usage: packaging/windows/spike-portable.sh <output-dir>
set -e
PACKAGING_DIR=$(cd "$(dirname "$0")" && pwd)
TEMPLATE_ROOT=$(cd "${PACKAGING_DIR}/../.." && pwd)
. "${TEMPLATE_ROOT}/mod.config"
[ -f "${TEMPLATE_ROOT}/user.config" ] && . "${TEMPLATE_ROOT}/user.config"

BUILTDIR=$(mkdir -p "$1" && cd "$1" && pwd -W)
ENGINE="${TEMPLATE_ROOT}/${ENGINE_DIRECTORY}"
TAG="spike-$(git -C "${TEMPLATE_ROOT}" rev-parse --short HEAD)"

echo "== Building core files (install_assemblies, self-contained win-x64)"
(cd "${ENGINE}" && dotnet publish -c Release -p:TargetPlatform=win-x64 -p:CopyGenericLauncher=False \
	-p:CopyCncDll="${PACKAGING_COPY_CNC_DLL}" -p:CopyD2kDll="${PACKAGING_COPY_D2K_DLL}" -r win-x64 \
	-p:PublishDir="${BUILTDIR}" --self-contained true --nologo -v q)

echo "== Installing engine data (install_data, minus fetch-geoip.sh)"
for FILE in VERSION AUTHORS COPYING IP2LOCATION-LITE-DB1.IPV6.BIN.ZIP "global mix database.dat"; do
	cp "${ENGINE}/${FILE}" "${BUILTDIR}/"
done
cp -r "${ENGINE}/glsl" "${BUILTDIR}/"
mkdir -p "${BUILTDIR}/mods"
cp -r "${ENGINE}/mods/common" "${BUILTDIR}/mods/"
for f in ${PACKAGING_COPY_ENGINE_FILES}; do
	mkdir -p "${BUILTDIR}/$(dirname "${f}")"
	cp -r "${ENGINE}/${f}" "${BUILTDIR}/${f}"
done

echo "== Building mod files (install_mod_assemblies)"
(cd "${TEMPLATE_ROOT}" && find . -maxdepth 1 -name '*.sln' -exec dotnet publish {} -c Release -p:TargetPlatform=win-x64 \
	-r win-x64 -p:PublishDir="${BUILTDIR}" --self-contained true --nologo -v q \;)
cp -Lr "${TEMPLATE_ROOT}/mods/"* "${BUILTDIR}/mods"
printf '%s\n' "${ENGINE_VERSION}" > "${BUILTDIR}/VERSION"

echo "== Compiling Windows launcher (install_windows_launcher, minus fixlauncher.py/rcedit)"
rm -rf "${ENGINE}/OpenRA.WindowsLauncher/obj"
dotnet publish "${ENGINE}/OpenRA.WindowsLauncher/OpenRA.WindowsLauncher.csproj" -c Release -r win-x64 \
	-p:LauncherName="${PACKAGING_WINDOWS_LAUNCHER_NAME}",TargetPlatform=win-x64,ModID="${MOD_ID}",PublishDir="${BUILTDIR}",FaqUrl="${PACKAGING_FAQ_URL}",InformationalVersion="${TAG}" \
	--self-contained true --nologo -v q

echo "Portable build: ${BUILTDIR}"
