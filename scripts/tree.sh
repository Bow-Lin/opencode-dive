#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-workspace/source}"
DEPTH="${2:-3}"

if [[ ! -d "$ROOT" ]]; then
  echo "error: directory not found: $ROOT" >&2
  exit 1
fi

if command -v tree >/dev/null 2>&1; then
  exec tree -a -L "$DEPTH" "$ROOT"
fi

find "$ROOT" -maxdepth "$DEPTH" | sort
