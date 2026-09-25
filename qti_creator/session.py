"""Session and application state models for QTI-Creator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
from pathlib import Path
import shutil
import tempfile
from typing import Any, Dict, List, Literal, Optional


@dataclass
class MediaFile:
    """Metadata for an extracted media file in the session."""
    relative_path: str
    absolute_path: Path
    name: str
    extension: str
    mime_type: Optional[str]
    size: int
    referenced_by: List[str] = field(default_factory=list)
    status: Literal["referenced", "unused", "unsupported"] = "unused"


@dataclass
class MissingMediaReference:
    """A media file referenced in QuizMD but not present in the media directory."""
    relative_path: str
    referenced_by: List[str] = field(default_factory=list)


@dataclass
class MediaSession:
    """State of uploaded/extracted media for a user session."""
    zip_path: Optional[str] = None
    zip_filename: Optional[str] = None
    extracted_root: Optional[str] = None
    files: List[MediaFile] = field(default_factory=list)
    missing: List[MissingMediaReference] = field(default_factory=list)
    include_in_package: bool = False
    resolve_in_preview: bool = True

    def calculate_revision(self) -> str:
        """Derive a hash of the media state affecting package generation."""
        hasher = hashlib.sha256()
        hasher.update(str(self.zip_filename or "").encode("utf-8"))
        hasher.update(str(self.include_in_package).encode("utf-8"))
        hasher.update(str(self.resolve_in_preview).encode("utf-8"))
        for f in sorted(self.files, key=lambda x: x.relative_path):
            hasher.update(f"{f.relative_path}:{f.size}".encode("utf-8"))
        return hasher.hexdigest()


@dataclass
class PackageState:
    """State of the generated QTI package."""
    output_path: Optional[str] = None
    filename: Optional[str] = None
    source_revision: Optional[str] = None
    media_revision: Optional[str] = None
    generated_at: Optional[datetime] = None

    def is_fresh(self, current_source_rev: str, current_media_rev: str) -> bool:
        if not self.output_path or not self.source_revision:
            return False
        return (
            self.source_revision == current_source_rev
            and self.media_revision == current_media_rev
        )


@dataclass
class QuizSession:
    """Authoritative backend session model across pages."""
    session_id: str = field(default_factory=lambda: tempfile.mkdtemp(prefix="qti_sess_"))
    source: str = ""
    media: MediaSession = field(default_factory=MediaSession)
    package: PackageState = field(default_factory=PackageState)

    @property
    def source_revision(self) -> str:
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()

    @property
    def media_revision(self) -> str:
        return self.media.calculate_revision()

    def is_package_fresh(self) -> bool:
        return self.package.is_fresh(self.source_revision, self.media_revision)

    def cleanup(self) -> None:
        """Clean up session temporary directories and files."""
        if self.session_id and Path(self.session_id).exists():
            try:
                shutil.rmtree(self.session_id, ignore_errors=True)
            except Exception:
                pass


def cleanup_session_callback(session: Any) -> None:
    """Gradio State delete_callback handler."""
    if isinstance(session, QuizSession):
        session.cleanup()
