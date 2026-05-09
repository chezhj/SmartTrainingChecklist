#!/usr/bin/env python
"""
Bump the xFlow plugin version.

Usage:
    python scripts/bump_plugin.py 1.1.0

What it does:
  1. Updates PLUGIN_VERSION in xplane_plugin/xFlow/PI_xFlow.py
  2. Prepends a new section header to xplane_plugin/CHANGELOG.md
  3. Creates a git commit: "chore(plugin): bump version to X.Y.Z"
  4. Creates a git tag: plugin-vX.Y.Z

Run from the repo root.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_FILE = REPO_ROOT / "xplane_plugin" / "xFlow" / "PI_xFlow.py"
PLUGIN_CHANGELOG = REPO_ROOT / "xplane_plugin" / "CHANGELOG.md"


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, cwd=REPO_ROOT)


def _current_version() -> str:
    text = PLUGIN_FILE.read_text(encoding="utf-8")
    m = re.search(r'^PLUGIN_VERSION\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if not m:
        sys.exit(f"ERROR: PLUGIN_VERSION not found in {PLUGIN_FILE}")
    return m.group(1)


def _set_version(new_ver: str) -> None:
    text = PLUGIN_FILE.read_text(encoding="utf-8")
    new_text = re.sub(
        r'^(PLUGIN_VERSION\s*=\s*["\'])[^"\']+(["\'])',
        rf"\g<1>{new_ver}\g<2>",
        text,
        flags=re.MULTILINE,
    )
    if new_text == text:
        sys.exit("ERROR: PLUGIN_VERSION replacement had no effect — check the file.")
    PLUGIN_FILE.write_text(new_text, encoding="utf-8")


def _prepend_changelog(new_ver: str) -> None:
    today = __import__("datetime").date.today().isoformat()
    header = f"\n## [{new_ver}] — {today}\n\n### Changed\n- (fill in release notes)\n"
    text = PLUGIN_CHANGELOG.read_text(encoding="utf-8")
    # Insert after the first H1 line
    lines = text.splitlines(keepends=True)
    insert_at = next(
        (i + 1 for i, line in enumerate(lines) if line.startswith("# ")),
        0,
    )
    lines.insert(insert_at, header)
    PLUGIN_CHANGELOG.write_text("".join(lines), encoding="utf-8")
    print(f"  → Remember to fill in the release notes in {PLUGIN_CHANGELOG.relative_to(REPO_ROOT)}")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {Path(__file__).name} <new-version>  (e.g. 1.1.0)")

    new_ver = sys.argv[1].lstrip("v")
    old_ver = _current_version()

    print(f"Bumping plugin version: {old_ver} → {new_ver}")

    _set_version(new_ver)
    _prepend_changelog(new_ver)

    print("Staging files …")
    _run(["git", "add",
          str(PLUGIN_FILE.relative_to(REPO_ROOT)),
          str(PLUGIN_CHANGELOG.relative_to(REPO_ROOT))])

    print("Committing …")
    _run(["git", "commit", "-m", f"chore(plugin): bump version to {new_ver}"])

    tag = f"plugin-v{new_ver}"
    print(f"Tagging {tag} …")
    _run(["git", "tag", tag])

    print(f"\nDone. Push with:\n  git push && git push origin {tag}")


if __name__ == "__main__":
    main()
