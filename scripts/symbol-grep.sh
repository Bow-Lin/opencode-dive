#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <symbol-pattern> [root]" >&2
  exit 1
fi

PATTERN="$1"
ROOT="${2:-workspace/source}"

if [[ ! -d "$ROOT" ]]; then
  echo "error: directory not found: $ROOT" >&2
  exit 1
fi

rg -n -g '!node_modules' -g '!dist' -g '!build' "$PATTERN" "$ROOT"
