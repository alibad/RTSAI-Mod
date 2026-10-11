#!/bin/sh
# Freeze fixed source, then make a new private native build copy (with SDK VERSION stamps).
# Usage: ./fetch-local-engine.sh [source-repo] [new-build-destination]
# Never deletes an existing engine or changes a branch/worktree. See docs/build-inputs.md.
set -eu
cd "$(dirname "$0")"
. ./mod.config
if [ -f user.config ]; then . ./user.config; fi
REPO="${1:-${LOCAL_ENGINE_REPO:-../OpenRA}}"
DEST="${2:-${ENGINE_DIRECTORY:-./engine}}"
INPUT=".inputs/engine-${ENGINE_VERSION}"
if [ -e "$DEST" ]; then echo >&2 "Refusing to replace existing build dependency: $DEST"; exit 1; fi
if [ -d "$INPUT" ]; then
    "${PYTHON:-python3}" tools/build-inputs.py verify "$INPUT"
else
    "${PYTHON:-python3}" tools/build-inputs.py engine --repo "$REPO" --out "$INPUT"
fi
"${PYTHON:-python3}" tools/build-inputs.py copy --input "$INPUT" --out "$DEST"
