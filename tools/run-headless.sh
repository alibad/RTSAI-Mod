#!/bin/sh
# Run a headless (Game.Platform=Null) RTS AI skirmish against the local engine build.
# Usage: tools/run-headless.sh <support-dir> <seconds> <map> <bots> [faction] [extra args...]
#   bots: Launch.Bots value, e.g. Multi1:normal:china  or  Multi0:normal:iran,Multi1:rush:turkey (spectate)
#   faction: Launch.Faction for the local player ("-" for none)
# Env: OPENRA_AI_COMPANION=1 to enable the companion bridge. Output: <support-dir>/headless.out
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SUP="$1"; SECS="$2"; MAP="$3"; BOTS="$4"; FACTION="${5:--}"
shift 5 2>/dev/null || shift $#
EXTRA=""
[ "${FACTION}" != "-" ] && EXTRA="Launch.Faction=${FACTION}"
cd "${ROOT}/engine"
set +e
timeout "${SECS}" ./bin/OpenRA.exe Game.Mod=rtsai Engine.EngineDir=.. "Engine.ModSearchPaths=${ROOT}/mods,./mods" \
	"Engine.SupportDir=${SUP}" Game.Platform=Null "Launch.Map=${MAP}" "Launch.Bots=${BOTS}" ${EXTRA} "$@" > "${SUP}/headless.out" 2>&1
RC=$?
set -e
echo "exit=${RC} (124 = still running when the ${SECS}s timeout stopped it)"
grep -n "Exception\|Game started\|Loading mod" "${SUP}/headless.out" | head -5
exit 0
