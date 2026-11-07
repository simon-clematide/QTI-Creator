"""Session and application state models for QTI-Creator."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
from pathlib import Path
import shutil
import tempfile
import threading
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

    def ensure_session_dir(self) -> Path:
        """Ensure the session temporary directory exists and return its Path."""
        if not self.session_id:
            self.session_id = tempfile.mkdtemp(prefix="qti_sess_")
        p = Path(self.session_id)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def cleanup(self) -> None:
        """Clean up session temporary directories and files."""
        if self.session_id and Path(self.session_id).exists():
            try:
                shutil.rmtree(self.session_id, ignore_errors=True)
            except Exception:
                pass


_STORE_LOCK = threading.Lock()
_SESSION_STORE: OrderedDict[str, QuizSession] = OrderedDict()
_MAX_SESSIONS = 256


def _extract_request_keys(request: Any) -> tuple[Optional[str], Optional[str]]:
    """Extract (cookie_sid, fallback_key) from a Gradio Request if available."""
    if request is None:
        return None, None
    try:
        cookies = dict(getattr(request, "cookies", {}) or {})
    except Exception:
        cookies = {}
    cookie_sid = cookies.get("qti_creator_sid")

    try:
        raw_headers = dict(getattr(request, "headers", {}) or {})
        headers = {str(k).lower(): str(v) for k, v in raw_headers.items()}
    except Exception:
        headers = {}

    client_obj = getattr(request, "client", None)
    client_host = (getattr(client_obj, "host", None) if client_obj else None) or headers.get(
        "x-forwarded-for", "local"
    )
    user_agent = headers.get("user-agent", "default")
    fallback_key = "fb_" + hashlib.sha256(
        f"{client_host}|{user_agent}".encode("utf-8")
    ).hexdigest()[:24]
    return cookie_sid, fallback_key


def resolve_session(
    session: Optional[QuizSession],
    request: Any = None,
    default_source: str = "",
) -> QuizSession:
    """Resolve the authoritative QuizSession across multipage Gradio route loads.

    In Gradio multipage apps (`demo.route` + `gr.Navbar`), each route navigation
    is a separate browser page load with a new `session_hash`, causing `gr.State`
    to be reset on each tab switch. This resolver binds the session to a persistent
    browser session identifier (`qti_creator_sid` cookie with a client fingerprint
    fallback) while remaining fully compatible with direct unit-test calls where
    `request` is None.
    """
    cookie_sid, fallback_key = _extract_request_keys(request)

    if cookie_sid is None and fallback_key is None:
        if isinstance(session, QuizSession):
            session.ensure_session_dir()
            return session
        return QuizSession(source=default_source)

    with _STORE_LOCK:
        resolved: Optional[QuizSession] = None
        if cookie_sid and cookie_sid in _SESSION_STORE:
            resolved = _SESSION_STORE[cookie_sid]
        elif fallback_key and fallback_key in _SESSION_STORE:
            resolved = _SESSION_STORE[fallback_key]
        elif isinstance(session, QuizSession):
            resolved = session
        else:
            resolved = QuizSession(source=default_source)

        resolved.ensure_session_dir()

        if fallback_key:
            _SESSION_STORE[fallback_key] = resolved
            _SESSION_STORE.move_to_end(fallback_key)
        if cookie_sid:
            _SESSION_STORE[cookie_sid] = resolved
            _SESSION_STORE.move_to_end(cookie_sid)

        while len(_SESSION_STORE) > _MAX_SESSIONS:
            _, evicted = _SESSION_STORE.popitem(last=False)
            if not any(s is evicted for s in _SESSION_STORE.values()):
                evicted.cleanup()

        return resolved


def cleanup_session_callback(session: Any) -> None:
    """Gradio State delete_callback handler."""
    if isinstance(session, QuizSession):
        with _STORE_LOCK:
            if any(s is session for s in _SESSION_STORE.values()):
                return
        session.cleanup()
