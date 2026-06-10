#!/usr/bin/env bash
# Run the checkouts pipeline (requires: pip install -e . in .venv).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "Could not find $PY" >&2
  echo "Create the environment and install the project, for example:" >&2
  echo "  cd \"$ROOT\" && python3 -m venv .venv && .venv/bin/pip install -e ." >&2
  exit 1
fi
exec "$PY" -m checkouts.main "$@"
