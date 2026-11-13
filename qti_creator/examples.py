"""Load bundled QuizMD examples and their matching media into a session."""

from pathlib import Path
import shutil

import gradio as gr

from qti_creator.media_service import analyze_session_media, safe_extract_media_zip
from qti_creator.session import MediaSession, PackageState, QuizSession, resolve_session
from qti_creator.core.examples import EXAMPLES

HOTSPOT_EXAMPLE_NAME = "Hotspot Image Questions (with Media)"
ASSET_DIR = Path(__file__).resolve().parent / "assets"
HOTSPOT_MEDIA_ZIP = ASSET_DIR / "hotspot_media.zip"
HOTSPOT_SOURCE = (ASSET_DIR / "hotspot.md").read_text(encoding="utf-8")

UI_EXAMPLES = {**EXAMPLES, HOTSPOT_EXAMPLE_NAME: HOTSPOT_SOURCE}


def load_example(
    name: str,
    session: QuizSession | None,
    request: gr.Request | None = None,
) -> QuizSession:
    """Replace the working quiz/media only after the requested example is ready."""
    if name not in UI_EXAMPLES:
        raise gr.Error("Select an available example first.")
    session = resolve_session(session, request)
    media = MediaSession()
    if name == HOTSPOT_EXAMPLE_NAME:
        root = session.ensure_session_dir() / "hotspot_example"
        root.mkdir(parents=True, exist_ok=True)
        zip_path = root / "hotspot_media.zip"
        shutil.copy2(HOTSPOT_MEDIA_ZIP, zip_path)
        extracted_root = root / "media"
        ok, message, _ = safe_extract_media_zip(str(zip_path), str(extracted_root))
        if not ok:
            raise gr.Error(f"Could not load example media: {message}")
        media = MediaSession(
            zip_path=str(zip_path),
            zip_filename=zip_path.name,
            extracted_root=str(extracted_root),
            include_in_package=True,
            resolve_in_preview=True,
        )
    session.source = UI_EXAMPLES[name]
    session.media = media
    session.package = PackageState()
    analyze_session_media(session)
    return session
