#!/usr/bin/env bash
# Run checkouts/main.py with the .venv Python (no need to activate the venv).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "Could not find $PY" >&2
  echo "Create the environment and install dependencies, for example:" >&2
  echo "  cd \"$ROOT\" && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi
exec env PYTHONPATH="$ROOT:$ROOT/checkouts:$ROOT/fetch" "$PY" "$ROOT/checkouts/main.py" "$@"
