#!/usr/bin/env bash
set -euo pipefail

case "$#" in
  2)
    ROOT="workspace/source"
    BASE="$1"
    TARGET="$2"
    ;;
  3)
    ROOT="$1"
    BASE="$2"
    TARGET="$3"
    ;;
  *)
    echo "usage: $0 [repo-root] <base-ref> <target-ref>" >&2
    exit 1
    ;;
esac

if [[ ! -d "$ROOT/.git" ]]; then
  echo "error: expected git repository at $ROOT" >&2
  exit 1
fi

git -C "$ROOT" diff --stat "$BASE" "$TARGET"
