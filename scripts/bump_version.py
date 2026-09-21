#!/usr/bin/env python3
"""Script to increment the patch version (v0.X.Y) and update release date.

Can be run standalone or invoked by a git pre-push hook / release workflow.
"""

import datetime
import re
import sys
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent.parent / "src" / "version.py"


def bump_version(part: str = "patch") -> str:
    if not VERSION_FILE.exists():
        print(f"Error: {VERSION_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    content = VERSION_FILE.read_text(encoding="utf-8")

    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not m:
        print("Error: Could not find __version__ in src/version.py", file=sys.stderr)
        sys.exit(1)

    old_version = m.group(1)
    parts = old_version.split(".")
    if len(parts) != 3:
        print(f"Error: Version '{old_version}' is not semantic (major.minor.patch)", file=sys.stderr)
        sys.exit(1)

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if part == "patch":
        patch += 1
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        print(f"Unknown part: {part}. Choose 'patch', 'minor', or 'major'.", file=sys.stderr)
        sys.exit(1)

    new_version = f"{major}.{minor}.{patch}"
    today = datetime.date.today().isoformat()

    new_content = re.sub(
        r'__version__\s*=\s*["\'][^"\']+["\']',
        f'__version__ = "{new_version}"',
        content,
    )
    new_content = re.sub(
        r'__release_date__\s*=\s*["\'][^"\']+["\']',
        f'__release_date__ = "{today}"',
        new_content,
    )

    VERSION_FILE.write_text(new_content, encoding="utf-8")
    print(f"Bumped version: {old_version} -> {new_version} ({today})")
    return new_version


if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "patch"
    bump_version(part)
