#!/usr/bin/env bash
# Gate C: start a REAL Minecraft client with the mod, let the client test drive it, and
# report its verdict.
#
#   ./tools/client-test.sh            # the target from .env.local (MC_TARGET), else 26.2
#   MC=1.21.1 ./tools/client-test.sh  # a specific target
#
# Works on macOS (a normal window opens; caffeinate keeps the display awake) and on headless
# Linux (Xvfb + software OpenGL, which is enough for Minecraft). Exit codes:
#   0 PASS · 1 FAIL · 2 cannot run here (named) · 3 no verdict (the client never reported)
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$REPO"
MODID="$(sed -n 's/^mod_id=//p' gradle.properties)"
SIG="${SIG:-${TMPDIR:-/tmp}/${MODID}-client}"; TIMEOUT="${TIMEOUT:-900}"
rm -rf "$SIG"; mkdir -p "$SIG"; touch "$SIG/.started"
MCARG=(); [ -n "${MC:-}" ] && MCARG=("-Pmc=$MC")
bash cloud/ensure.sh || exit 2   # cloud only: xvfb + Java 25 on first use; no-op elsewhere

RUN=()
case "$(uname -s)" in
  Darwin) command -v caffeinate >/dev/null && RUN=(caffeinate -dimsu) ;;
  Linux)
    if [ -z "${DISPLAY:-}" ]; then
      if ! command -v xvfb-run >/dev/null; then
        echo "Gate C needs a display. On headless Linux:" >&2
        echo "  sudo apt-get update && sudo apt-get install -y xvfb mesa-utils libgl1-mesa-dri" >&2
        exit 2
      fi
      export LIBGL_ALWAYS_SOFTWARE=1
      RUN=(xvfb-run -a -s "-screen 0 1280x720x24")
    fi ;;
esac

echo "client-test: logging to $SIG/run.log (timeout ${TIMEOUT}s)"
${RUN[@]+"${RUN[@]}"} ./gradlew runClient ${MCARG[@]+"${MCARG[@]}"} -Pboottest -Ptestmode=buddy \
  -Psigdir="$SIG" --console=plain >"$SIG/run.log" 2>&1 &
PID=$!
waited=0
while kill -0 "$PID" 2>/dev/null && [ ! -f "$SIG/result" ] && [ "$waited" -lt "$TIMEOUT" ]; do
  sleep 5; waited=$((waited + 5))
done
if [ ! -f "$SIG/result" ]; then
  kill "$PID" 2>/dev/null
  echo "client-test: NO VERDICT after ${waited}s. Last lines of the log:"
  tail -30 "$SIG/run.log"
  exit 3
fi
wait "$PID" 2>/dev/null
grep -aE "Minecraft [0-9.]+ \(NeoForge" "$SIG/run.log" | head -1
cat "$SIG/result"
shot="$(find run -path '*screenshots*' -name 'bounce_block*.png' -newer "$SIG/.started" 2>/dev/null | head -1)"
if [ -n "$shot" ]; then cp "$shot" "$SIG/" && echo "photo: $SIG/$(basename "$shot")"; else echo "client-test: no photo was saved (look for screenshots under run/)"; fi
grep -q '^PASS' "$SIG/result"
