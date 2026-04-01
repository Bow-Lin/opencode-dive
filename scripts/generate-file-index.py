#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

IGNORED_DIRS = {".git", "node_modules", "dist", "build", "__pycache__"}
IGNORED_FILES = {".DS_Store"}
SOURCE_EXTENSIONS = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".py",
    ".go",
    ".rs",
    ".java",
}


def iter_files(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS)
        visible_files = sorted(f for f in files if f not in IGNORED_FILES)
        yield Path(current), visible_files


def top_level_summary(root: Path) -> list[tuple[str, int, int, str]]:
    summaries = []
    for path in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in IGNORED_DIRS):
        file_count = 0
        source_count = 0
        extensions: Counter[str] = Counter()
        for _, files in iter_files(path):
            for name in files:
                file_count += 1
                suffix = Path(name).suffix
                if suffix in SOURCE_EXTENSIONS:
                    source_count += 1
                if suffix:
                    extensions[suffix] += 1
        dominant = ", ".join(f"{ext}:{count}" for ext, count in extensions.most_common(3)) or "n/a"
        summaries.append((path.name, file_count, source_count, dominant))
    return summaries


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "workspace/source")
    if not root.is_dir():
        print(f"error: directory not found: {root}", file=sys.stderr)
        return 1

    print(f"# File Index: {root}")
    print()
    root_files = sorted(
        p.name for p in root.iterdir() if p.is_file() and p.name not in IGNORED_FILES
    )
    print("## Root Files")
    if root_files:
        for name in root_files:
            print(f"- `{name}`")
    else:
        print("- none")
    print()

    print("## Top-Level Directory Summary")
    print()
    print("| Directory | Total files | Source-like files | Dominant extensions |")
    print("| --- | ---: | ---: | --- |")
    summaries = top_level_summary(root)
    if summaries:
        for name, total, source_like, dominant in summaries:
            print(f"| `{name}` | {total} | {source_like} | {dominant} |")
    else:
        print("| `n/a` | 0 | 0 | n/a |")
    print()

    print("## Candidate Module Roots")
    candidates = [item for item in summaries if item[2] > 0]
    if candidates:
        for name, _, source_like, dominant in candidates:
            print(f"- `{name}`: {source_like} source-like files, dominant extensions `{dominant}`")
    else:
        print("- none yet")
    print()

    print("## Tree")
    print()
    for current, files in iter_files(root):
        rel_dir = Path(current).relative_to(root)
        depth = 0 if rel_dir == Path(".") else len(rel_dir.parts)
        heading = "/" if rel_dir == Path(".") else rel_dir.as_posix()
        print(f'{"  " * depth}- `{heading}`')
        for name in files:
            print(f'{"  " * (depth + 1)}- `{name}`')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
