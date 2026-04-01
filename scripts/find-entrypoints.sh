#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-workspace/source}"

if [[ ! -d "$ROOT" ]]; then
  echo "error: directory not found: $ROOT" >&2
  exit 1
fi

found=0

run_rg() {
  if rg -n \
    -g '!node_modules' \
    -g '!dist' \
    -g '!build' \
    "$@" \
    "$ROOT"; then
    found=1
  fi
}

echo "## Package metadata candidates"
run_rg -g 'package.json' -e '"(bin|main|module|exports)"\s*:'
echo

echo "## Shebang entry files"
run_rg -e '^#!.*\b(node|bun|deno|python|bash|sh)\b'
echo

echo "## Entrypoint file/path hints"
run_rg \
  -e '(^|/)(bin|cli|cmd|app|main|index)\.' \
  -e '(^|/)(bootstrap|startup|entry|register|runtime)/'
echo

echo "## Symbol and bootstrap hints"
run_rg \
  -e '\bmain\s*\(' \
  -e '\bif\s+__name__\s*==\s*["'\'']__main__["'\'']' \
  -e '\b(cli|bootstrap|init|start|run|register|createApp|render)\b'

if [[ "$found" -eq 0 ]]; then
  echo
  echo "No entrypoint candidates found under $ROOT."
fi
