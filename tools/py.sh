#!/usr/bin/env bash
# Runs a Python 3 script on every OS:  bash tools/py.sh <script.py> [args]
#
# For the git hooks and Claude Code's hooks, which must not depend on `python3` being on PATH: on
# Windows the python.org install has `python` and `py` but no `python3` (Windows' own python3.exe only
# opens the Microsoft Store), and a hook's shell may not have setup's ~/bin shim on its PATH. Elsewhere
# it is plain python3, as before.
case "${OSTYPE:-}" in
  msys*|cygwin*) . "$(dirname "${BASH_SOURCE[0]}")/python.sh" || exit 1; exec "$PYTHON" "$@" ;;
  *) exec python3 "$@" ;;
esac
