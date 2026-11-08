"""Shared Anki export service for UI and headless callers."""
from pathlib import Path
import tempfile

from src.anki import prepare_anki_export, render_anki_preview, write_anki_package


def build_anki_export(source: str, deck_name: str = '', separate_gaps: bool = True,
                      media_zip: str | None = None) -> tuple[str, str]:
    """Return a downloadable package path and preview of the same notes."""
    media_bytes = Path(media_zip).read_bytes() if media_zip else None
    export = prepare_anki_export(source, deck_name=deck_name,
                                 separate_gaps=separate_gaps, media_zip_bytes=media_bytes)
    with tempfile.NamedTemporaryFile(prefix='quiz_anki_', suffix='.apkg', delete=False) as f:
        path = f.name
    try:
        write_anki_package(export, path)
        return path, render_anki_preview(export)
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise
