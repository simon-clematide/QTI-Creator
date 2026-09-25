"""Media extraction, inspection, security validation, and manifest generation."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
import shutil
from typing import List, Optional, Tuple
import zipfile

from qti_creator.session import MediaFile, MissingMediaReference, QuizSession
from src.media import extract_media_references
from src.model import Quiz
from src.parser import parse_quizmd

# Security limits for uploaded media ZIPs
MAX_FILES = 2000
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_SINGLE_FILE_BYTES = 25 * 1024 * 1024    # 25 MB


def safe_extract_media_zip(
    zip_filepath: str,
    target_dir: str,
) -> Tuple[bool, str, List[Path]]:
    """Safely validate and extract entries from a media ZIP archive into target_dir.

    Guards against:
    - Path traversal (e.g. `../`)
    - Absolute paths
    - Symlinks / directory traversal
    - Zip bombs (file count & uncompressed byte limits)
    """
    if not zip_filepath or not os.path.exists(zip_filepath):
        return False, "File does not exist.", []

    if not zipfile.is_zipfile(zip_filepath):
        return False, "Uploaded file is not a valid ZIP archive.", []

    target_path = Path(target_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    extracted_files: List[Path] = []
    total_uncompressed = 0
    total_files = 0

    try:
        with zipfile.ZipFile(zip_filepath, "r") as zf:
            infolist = zf.infolist()
            if len(infolist) > MAX_FILES:
                return False, f"ZIP contains too many entries ({len(infolist)} > {MAX_FILES}).", []

            for info in infolist:
                # Disallow directory traversal & absolute paths
                norm_name = os.path.normpath(info.filename)
                if norm_name.startswith("..") or os.path.isabs(norm_name):
                    return False, f"ZIP contains unsafe path: {info.filename}", []

                # Resolve destination
                dest = (target_path / norm_name).resolve()
                if not dest.is_relative_to(target_path):
                    return False, f"ZIP path escapes extraction root: {info.filename}", []

                # Check uncompressed size
                if info.file_size > MAX_SINGLE_FILE_BYTES:
                    return False, f"ZIP entry {info.filename} exceeds 25 MB limit.", []

                total_uncompressed += info.file_size
                if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                    return False, "Total uncompressed size exceeds 100 MB limit.", []

                if info.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                    continue

                total_files += 1
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted_files.append(dest)

    except Exception as e:
        return False, f"Failed to extract ZIP: {e}", []

    return True, f"Successfully extracted {len(extracted_files)} file(s).", extracted_files


def analyze_session_media(session: QuizSession) -> None:
    """Analyze references in session.source against extracted media files and update session.media."""
    media_root = Path(session.media.extracted_root) if session.media.extracted_root else None

    # Parse quiz to extract media references
    quiz = None
    if session.source and session.source.strip():
        try:
            quiz, _ = parse_quizmd(session.source)
        except Exception:
            quiz = None

    # Collect references from quiz questions
    ref_map: dict[str, list[str]] = {}
    if quiz and quiz.questions:
        for idx, q in enumerate(quiz.questions, start=1):
            q_label = f"Q{idx} ({q.title})" if getattr(q, "title", None) else f"Q{idx}"
            # Extract references from prompt, choices, hint, feedback, etc.
            text_sources = [getattr(q, "prompt", "") or ""]
            if hasattr(q, "choices"):
                for c in getattr(q, "choices", []):
                    text_sources.append(getattr(c, "text", "") or "")
            if getattr(q, "hint", None):
                text_sources.append(q.hint)
            if getattr(q, "feedback", None):
                text_sources.append(q.feedback)

            for text in text_sources:
                for r in extract_media_references(text):
                    if r.kind == "relative":
                        clean_src = os.path.normpath(r.source).lstrip("./\\")
                        if clean_src not in ref_map:
                            ref_map[clean_src] = []
                        if q_label not in ref_map[clean_src]:
                            ref_map[clean_src].append(q_label)

    # Scan extracted files
    files: List[MediaFile] = []
    found_relative_paths: set[str] = set()

    if media_root and media_root.exists():
        for path in sorted(media_root.rglob("*")):
            if path.is_file():
                # Avoid hidden files / OS metadata
                if path.name.startswith(".") or "__MACOSX" in path.parts:
                    continue
                rel_path = path.relative_to(media_root).as_posix()
                norm_rel = os.path.normpath(rel_path).lstrip("./\\")
                found_relative_paths.add(norm_rel)

                mime, _ = mimetypes.guess_type(path.name)
                ext = path.suffix.lower()
                size = path.stat().st_size

                # Check references (both as posix and normalized)
                refs = ref_map.get(norm_rel) or ref_map.get(rel_path) or []
                status = "referenced" if refs else "unused"

                files.append(
                    MediaFile(
                        relative_path=rel_path,
                        absolute_path=path,
                        name=path.name,
                        extension=ext,
                        mime_type=mime,
                        size=size,
                        referenced_by=refs,
                        status=status,
                    )
                )

    session.media.files = files

    # Determine missing references
    missing: List[MissingMediaReference] = []
    for ref_src, q_labels in ref_map.items():
        if ref_src not in found_relative_paths and ref_src.replace("\\", "/") not in found_relative_paths:
            missing.append(MissingMediaReference(relative_path=ref_src, referenced_by=q_labels))

    session.media.missing = missing
