"""Command-line interface for QTI-Creator."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import List, Optional

from qti_creator import (
    __version__,
    check_quiz_api,
    export_anki_api,
    export_qti_api,
    validate_jqti_api,
)


def _read_markdown(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="qti-creator",
        description="Validate QuizMD files and export OpenOLAT QTI 2.1 or Anki packages.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_check = subparsers.add_parser("check", help="Validate QuizMD syntax and structure")
    p_check.add_argument("input", help="Path to QuizMD markdown file")

    p_val = subparsers.add_parser("validate", help="Validate with JQTI+ engine (requires Java 17+)")
    p_val.add_argument("input", help="Path to QuizMD markdown file")

    p_export = subparsers.add_parser("export", help="Export QTI 2.1 ZIP package")
    p_export.add_argument("input", help="Path to QuizMD markdown file")
    p_export.add_argument("-o", "--output", help="Output .zip path (default: <input-stem>.zip)")

    p_anki = subparsers.add_parser("anki", help="Export Anki .apkg deck")
    p_anki.add_argument("input", help="Path to QuizMD markdown file")
    p_anki.add_argument("-o", "--output", help="Output .apkg path (default: <input-stem>.apkg)")
    p_anki.add_argument("--deck-name", default="", help="Anki deck name (default: quiz title)")
    p_anki.add_argument(
        "--no-separate-gaps",
        action="store_true",
        help="Do not create one card per gap",
    )
    p_anki.add_argument("--media-zip", default=None, help="Optional ZIP of locally referenced images")

    args = parser.parse_args(argv)
    md = _read_markdown(args.input)

    if args.command == "check":
        res = check_quiz_api(md)
        print(json.dumps(res, indent=2))
        return 0 if res.get("valid") else 1

    if args.command == "validate":
        res = validate_jqti_api(md)
        print(json.dumps(res, indent=2))
        return 0 if res.get("valid") else 1

    if args.command == "export":
        tmp_zip = export_qti_api(md)
        out_path = Path(args.output) if args.output else Path(args.input).with_suffix(".zip")
        shutil.move(tmp_zip, out_path)
        print(out_path)
        return 0

    if args.command == "anki":
        tmp_apkg = export_anki_api(
            md,
            deck_name=args.deck_name,
            separate_gaps=not args.no_separate_gaps,
            media_zip=args.media_zip,
        )
        out_path = Path(args.output) if args.output else Path(args.input).with_suffix(".apkg")
        shutil.move(tmp_apkg, out_path)
        print(out_path)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
