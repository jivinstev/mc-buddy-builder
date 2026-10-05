#!/usr/bin/env bash
# Gate B: boot a real (headless) Minecraft server with the mod and run every @GameTest.
#
#   ./tools/gate-b.sh            # the target from .env.local (MC_TARGET), else 26.2
#   MC=1.21.1 ./tools/gate-b.sh  # a specific target
#
# The verdict comes from the LOG, not from Gradle's exit code: runGameTestServer can exit 0
# without running a single test (a mod that fails to load, a locked world). No
# "N required tests passed" line is a FAIL here, never a pass.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCARG=(); [ -n "${MC:-}" ] && MCARG=("-Pmc=$MC")
bash cloud/ensure.sh java25 || exit 2   # cloud only: Java 25 on first use; no-op elsewhere
LOG="$(mktemp -t gate-b.XXXXXX.log)"
echo "gate-b: running GameTests ${MC:+for $MC }(log: $LOG)"
./gradlew runGameTestServer ${MCARG[@]+"${MCARG[@]}"} --console=plain >"$LOG" 2>&1
grep -aE "Minecraft [0-9.]+ \(NeoForge" "$LOG" | head -1
# No 'All' in the pattern: Minecraft says "All 3 required tests passed" but "1 required tests failed".
line="$(grep -aoE '[0-9]+ required tests? (passed|failed)' "$LOG" | tail -1)"
if [ -z "$line" ]; then
  echo "gate-b: FAIL - no test result in the log. The server probably never ran the tests:"
  grep -aE "ERROR|Exception|Missing or unsupported|requires" "$LOG" | head -15
  exit 1
fi
echo "gate-b: $line"
case "$line" in *passed) exit 0 ;; *) grep -aE "failed|::" "$LOG" | grep -av "^$" | tail -20; exit 1 ;; esac
