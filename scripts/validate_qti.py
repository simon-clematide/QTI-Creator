#!/usr/bin/env python3
"""CLI utility to validate QTI 2.1 XML files or ZIP packages against OpenOLAT JQTI+ runtime.

Usage:
    python3 scripts/validate_qti.py sample_quizzes/13_all_types_combined_qti21.zip
    python3 scripts/validate_qti.py path/to/item.xml
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.jqti_validator import is_java_available, is_javac_available, validate_with_jqti


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/validate_qti.py <file.xml|package.zip> ...")
        sys.exit(2)

    if not is_java_available() or not is_javac_available():
        print("Error: Java and javac must be installed to run JQTI+ validation.", file=sys.stderr)
        sys.exit(3)

    paths = [Path(p) for p in sys.argv[1:]]
    print(f"Validating {len(paths)} path(s) against OpenOLAT JQTI+ runtime...")

    is_valid, errors = validate_with_jqti(paths)

    if is_valid:
        print("\n✅ SUCCESS: All QTI items/tests passed OpenOLAT JQTI+ validation with 0 errors!")
        sys.exit(0)
    else:
        print(f"\n❌ FAILED: Found {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
