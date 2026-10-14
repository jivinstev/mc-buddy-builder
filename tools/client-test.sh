#!/usr/bin/env bash
# Gate C: start a REAL Minecraft client with the mod, let the client test drive it, and
# report its verdict.
#
#   ./tools/client-test.sh            # the target from .env.local (MC_TARGET), else 26.2
#   MC=1.21.1 ./tools/client-test.sh  # a specific target
#
# Works on macOS (a normal window opens; caffeinate keeps the display awake), on Windows in Git
# Bash (a normal window opens) and on headless Linux (Xvfb + software OpenGL, which is enough for
# Minecraft). Exit codes:
#   0 PASS · 1 FAIL · 2 cannot run here (named) · 3 no verdict (the client never reported)
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$REPO"
MODID="$(sed -n 's/^mod_id=//p' gradle.properties)"
# Inside the project (build/ is git-ignored): Claude looks at the photo, and anything outside the
# project folder would stop the child's session for permission.
SIG="${SIG:-$REPO/build/client-test}"; TIMEOUT="${TIMEOUT:-900}"
rm -rf "$SIG"; mkdir -p "$SIG"; touch "$SIG/.started"
MCARG=(); [ -n "${MC:-}" ] && MCARG=("-Pmc=$MC")
bash cloud/ensure.sh || exit 2   # cloud only: xvfb + Java 25 on first use; no-op elsewhere

RUN=(); WIN=; GRADLE_ARGS=()
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    WIN=1
    # Its own Gradle process (no daemon), so the game is in the tree a timeout kills: with the
    # shared daemon the game would be the daemon's child, and outlive the kill.
    GRADLE_ARGS=(--no-daemon) ;;
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

# Java on Windows needs C:/... not Git Bash's /c/...: unconverted, the verdict lands in \c\... and the
# gate sees NO VERDICT.
SIGARG="$SIG"; [ -n "$WIN" ] && SIGARG="$(cygpath -m "$SIG")"
echo "client-test: logging to $SIG/run.log (timeout ${TIMEOUT}s)"
${RUN[@]+"${RUN[@]}"} ./gradlew runClient ${MCARG[@]+"${MCARG[@]}"} ${GRADLE_ARGS[@]+"${GRADLE_ARGS[@]}"} \
  -Pboottest -Ptestmode=buddy -Psigdir="$SIGARG" --console=plain >"$SIG/run.log" 2>&1 &
PID=$!
stop_client() {
  if [ -n "$WIN" ]; then
    # `kill` reaches only Git Bash's stand-in for gradlew; taskkill /T takes the real process and
    # everything it started, the game included. (// stops Git Bash rewriting /T as a path.)
    [ -r "/proc/$PID/winpid" ] && taskkill //F //T //PID "$(cat "/proc/$PID/winpid")" >/dev/null 2>&1
    # And any game of this project's left over (its command line names this folder and clientRun).
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='java.exe' or Name='javaw.exe'\" | Where-Object { \$_.CommandLine -like '*$(cygpath -m "$REPO")*' -and \$_.CommandLine -like '*clientRun*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }" >/dev/null 2>&1
  else
    kill "$PID" 2>/dev/null
  fi
}
waited=0
while kill -0 "$PID" 2>/dev/null && [ ! -f "$SIG/result" ] && [ "$waited" -lt "$TIMEOUT" ]; do
  sleep 5; waited=$((waited + 5))
done
if [ ! -f "$SIG/result" ]; then
  stop_client
  echo "client-test: NO VERDICT after ${waited}s. Last lines of the log:"
  tail -30 "$SIG/run.log"
  exit 3
fi
wait "$PID" 2>/dev/null
grep -aE "Minecraft [0-9.]+ \(NeoForge" "$SIG/run.log" | head -1
cat "$SIG/result"
# Every photo this run took, not only the starter block's: a new block's test names its own.
shots=0
while IFS= read -r shot; do
  cp "$shot" "$SIG/" && echo "photo: $SIG/$(basename "$shot")" && shots=$((shots + 1))
done < <(find run -path '*screenshots*' -name '*.png' -newer "$SIG/.started" 2>/dev/null | sort)
[ "$shots" -gt 0 ] || echo "client-test: no photo was saved (look for screenshots under run/)"
grep -q '^PASS' "$SIG/result"
