#!/usr/bin/env python
"""
Bump the content version of a SOP in the database.

Usage:
    python scripts/bump_content_version.py B738 1.1.0

What it does:
  1. Finds the SOP with the given ICAO code in the database.
  2. Drafts release notes from git log (commits touching migrations/ and fixtures/)
     since the previous sop-{icao}-v* tag.
  3. Opens the draft in $EDITOR (falls back to printing it) for you to edit.
  4. Updates SOP.content_version and SOP.release_notes in the database.
  5. Creates a git commit: "chore(sop): bump B738 content to X.Y.Z"
  6. Creates a git tag: sop-B738-vX.Y.Z

Run from the repo root with the Django dev settings active (uses manage.py shell).

Note: changes made via the Django admin are NOT in git history unless you export
and commit fixtures. Use the release notes to summarise admin-driven changes.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANAGE = REPO_ROOT / "manage.py"


def _run(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        check=True,
        cwd=REPO_ROOT,
        capture_output=capture,
        text=capture,
    )


def _draft_notes(icao: str, new_ver: str) -> str:
    """
    Build a draft of release notes from git log entries that touched
    checklist/migrations/ or checklist/fixtures/ since the last sop-{icao}-v* tag.
    """
    tag_prefix = f"sop-{icao}-v"
    # Find the most recent matching tag
    result = subprocess.run(
        ["git", "tag", "--list", f"{tag_prefix}*", "--sort=-version:refname"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    tags = result.stdout.strip().splitlines()
    prev_tag = tags[0] if tags else None

    range_spec = f"{prev_tag}..HEAD" if prev_tag else "HEAD"
    log_result = subprocess.run(
        [
            "git", "log", range_spec,
            "--oneline",
            "--",
            "checklist/migrations/",
            "checklist/fixtures/",
        ],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    log_lines = log_result.stdout.strip()

    since_note = f"since {prev_tag}" if prev_tag else "all history"
    draft = (
        f"# Release notes for {icao} SOP v{new_ver}\n"
        f"# Edit this file, save and close to continue.\n"
        f"# Lines starting with # are ignored.\n\n"
        f"## [{new_ver}]\n\n"
        f"### Changed\n"
        f"- (describe your checklist changes here)\n\n"
        f"### Commits ({since_note})\n"
    )
    if log_lines:
        for line in log_lines.splitlines():
            draft += f"# {line}\n"
    else:
        draft += "# (no migration/fixture commits found)\n"

    return draft


def _open_editor(draft: str) -> str:
    """Open draft in $EDITOR and return the final text."""
    editor = os.environ.get("EDITOR", "")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(draft)
        tmp_path = f.name

    if editor:
        subprocess.run([editor, tmp_path], check=True)
    else:
        print("\n--- DRAFT RELEASE NOTES (no $EDITOR set — edit the file manually) ---")
        print(f"File: {tmp_path}")
        print(draft)
        input("Press Enter when you have finished editing the file above …")

    text = Path(tmp_path).read_text(encoding="utf-8")
    Path(tmp_path).unlink(missing_ok=True)

    # Strip comment lines
    lines = [l for l in text.splitlines() if not l.startswith("#")]
    return "\n".join(lines).strip()


def _update_db(icao: str, new_ver: str, notes: str) -> None:
    """Update SOP in the database via manage.py shell."""
    script = (
        f"from checklist.models import SOP; "
        f"sop = SOP.objects.get(icao_code='{icao}'); "
        f"sop.content_version = '{new_ver}'; "
        f"sop.release_notes = {notes!r}; "
        f"sop.save(); "
        f"print(f'Updated {{sop}}')"
    )
    _run([sys.executable, str(MANAGE), "shell", "-c", script])


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(
            f"Usage: python {Path(__file__).name} <icao-code> <new-version>\n"
            "  e.g. python scripts/bump_content_version.py B738 1.1.0"
        )

    icao = sys.argv[1].upper()
    new_ver = sys.argv[2].lstrip("v")

    print(f"Bumping {icao} SOP content version to {new_ver} …")

    draft = _draft_notes(icao, new_ver)
    notes = _open_editor(draft)

    if not notes:
        sys.exit("Aborted — release notes are empty.")

    print("Updating database …")
    _update_db(icao, new_ver, notes)

    print("Committing …")
    _run(["git", "commit", "--allow-empty", "-m", f"chore(sop): bump {icao} content to {new_ver}"])

    tag = f"sop-{icao}-v{new_ver}"
    print(f"Tagging {tag} …")
    _run(["git", "tag", tag])

    print(f"\nDone. Push with:\n  git push && git push origin {tag}")


if __name__ == "__main__":
    main()
