#!/bin/bash
set -o errexit -o pipefail
[ $# -eq 5 ] || { echo 'usage: build-companion.sh <frozen-source> <wheelhouse> <python3.12> <private-work> <frozen-vocabulary>'; exit 1; }
SOURCE="$1"
WHEELS="$2"
PYTHON="$3"
WORK="$4"
VOCABULARY="$5"
mkdir -p "${WORK}/tmp" "${WORK}/cache"
export TMPDIR="${WORK}/tmp" PIP_CACHE_DIR="${WORK}/cache" PYTHONPYCACHEPREFIX="${WORK}/pycache"
"${PYTHON}" -m venv "${WORK}/venv"
"${WORK}/venv/bin/pip" install --no-index --find-links="${WHEELS}" setuptools==84.0.0 pyinstaller==6.22.3
"${WORK}/venv/bin/pip" install --no-build-isolation --no-index --find-links="${WHEELS}" "${SOURCE}/services/companion" "${SOURCE}/services/worldgen"
"${WORK}/venv/bin/pyinstaller" --noconfirm --onedir --name rtsai-companion --distpath "${WORK}/dist" --workpath "${WORK}/build" --specpath "${WORK}" --collect-all openra_ai_companion --collect-all openra_ai_worldgen --collect-data agents --hidden-import openra_ai_companion.local_runtime --hidden-import openra_ai_companion.pack_cli "${SOURCE}/apps/launcher/companion_entry.py"
cp -R "${SOURCE}/catalog" "${SOURCE}/packaging" "${WORK}/dist/rtsai-companion/"
cp -R "${VOCABULARY}" "${WORK}/dist/rtsai-companion/engine-vocabulary"
"${WORK}/dist/rtsai-companion/rtsai-companion" --help >/dev/null
