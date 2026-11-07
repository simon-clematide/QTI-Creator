"""Media handling, extraction, validation, and preflight for QTI-Creator.

Rule: Distinguish quiz semantics from media resolution.
Preflight owns resolution; Markdown rendering only rewrites references;
packager only packages already-resolved assets.
"""

import base64
from dataclasses import dataclass, field
import hashlib
import html
import ipaddress
import os
import re
import socket
import struct
import urllib.parse
import urllib.request
import zipfile
from typing import Dict, List, Literal, Optional, Set, Tuple

from src.model import (
    EssayQuestion,
    FillBlankQuestion,
    HotspotQuestion,
    HottextQuestion,
    InlineChoiceQuestion,
    KprimQuestion,

    MultipleChoiceQuestion,
    NumericalQuestion,
    OrderQuestion,
    Question,
    Quiz,
    SingleChoiceQuestion,
    TrueFalseQuestion,
)
from src.validation import Diagnostic, Severity

# Supported raster image MIME magic bytes
MAGIC_NUMBERS: Dict[bytes, Tuple[str, str]] = {
    b"\x89PNG\r\n\x1a\n": ("image/png", ".png"),
    b"\xff\xd8\xff": ("image/jpeg", ".jpg"),
    b"GIF87a": ("image/gif", ".gif"),
    b"GIF89a": ("image/gif", ".gif"),
}

# Image markdown pattern: ![alt](url =WxH)
# Must not match code spans or ordinary links [text](url)
RE_IMAGE = re.compile(
    r"!\[([^\]]*)\]\(\s*(\S+?)(?:\s+=((?:\d+(?:%|px)?x\d*(?:%|px)?|\d*x\d+(?:%|px)?|\d+(?:%|px)?)))?\s*\)"
)
RE_INLINE_CODE = re.compile(r"`[^`]+`")


@dataclass
class MediaReference:
    """A referenced media resource in QuizMD content."""
    source: str
    alt_text: str
    kind: Literal["remote", "relative"]
    question_id: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class ResolvedAsset:
    """A fetched or extracted media file ready for QTI packaging."""
    source: str
    filename: str  # Safe relative path inside the QTI package (e.g. media/tree.png or media/hash.png)
    content_type: str
    data: bytes
    size_bytes: int
    content_hash: str

    @property
    def data_uri(self) -> str:
        """Return base64 Data URL for embedding directly in HTML previews."""
        b64 = base64.b64encode(self.data).decode("ascii")
        return f"data:{self.content_type};base64,{b64}"


@dataclass(frozen=True)
class ResolvedHotspotImage:
    """Resolved and validated hotspot background image metadata."""
    package_path: str
    mime_type: str
    width: int
    height: int
    content_hash: str


@dataclass(frozen=True)
class ResolvedHotspotRegion:
    """Resolved and validated hotspot region in integer pixel coordinates."""
    identifier: str
    shape: Literal["rect", "circle"]
    pixel_coords: Tuple[int, ...]
    correct: bool
    author_label: str = ""


@dataclass
class MediaPreflightResult:
    """The result of preflighting media references for a quiz."""
    references: List[MediaReference] = field(default_factory=list)
    include_media: bool = False
    diagnostics: List[Diagnostic] = field(default_factory=list)
    resolved_assets: Dict[str, ResolvedAsset] = field(default_factory=dict)  # Keyed by source
    # Mapping of question_identifier -> list of relative package filenames it uses
    question_asset_map: Dict[str, List[str]] = field(default_factory=dict)
    # Mapping of source -> relative package filename
    source_to_package_path: Dict[str, str] = field(default_factory=dict)
    # Resolved hotspot images and region pixel coordinates keyed by question_identifier
    resolved_hotspot_images: Dict[str, ResolvedHotspotImage] = field(default_factory=dict)
    resolved_hotspot_regions: Dict[str, Tuple[ResolvedHotspotRegion, ...]] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(d.severity == Severity.ERROR for d in self.diagnostics)

    def summary_text(self) -> str:
        if not self.references:
            return ""
        remote_cnt = sum(1 for r in self.references if r.kind == "remote")
        rel_cnt = sum(1 for r in self.references if r.kind == "relative")
        
        parts = []
        if remote_cnt:
            parts.append(f"{remote_cnt} remote")
        if rel_cnt:
            parts.append(f"{rel_cnt} relative")
        ref_summary = ", ".join(parts)

        if not self.include_media:
            return f"🖼️ **Media:** {len(self.references)} reference(s) ({ref_summary}) — external references retained."
        
        err_cnt = sum(1 for d in self.diagnostics if d.severity == Severity.ERROR)
        if err_cnt > 0:
            return f"⚠️ **Media Preflight Failed:** {err_cnt} error(s) across {len(self.references)} reference(s)."
        
        ready_cnt = len(self.resolved_assets)
        return f"✓ **Media Preflight:** {ready_cnt} asset(s) resolved and ready for packaging."


def extract_media_references(text: str, question_id: Optional[str] = None) -> List[MediaReference]:
    """Extract standard Markdown images ![alt](src) while ignoring inline code and fenced code blocks."""
    if not text:
        return []

    lines = text.splitlines()
    in_code_block = False
    refs: List[MediaReference] = []

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Strip inline code spans so `![not an image](url)` is ignored
        cleaned_line = RE_INLINE_CODE.sub("", line)

        for match in RE_IMAGE.finditer(cleaned_line):
            alt_text = match.group(1).strip()
            src = match.group(2).strip()
            if not src:
                continue

            parsed = urllib.parse.urlparse(src)
            kind: Literal["remote", "relative"] = "remote" if parsed.scheme in ("http", "https") else "relative"
            refs.append(
                MediaReference(
                    source=src,
                    alt_text=alt_text,
                    kind=kind,
                    question_id=question_id,
                    line_number=line_idx,
                )
            )

    return refs


def extract_quiz_media_references(quiz: Quiz) -> List[MediaReference]:
    """Scan all questions and section descriptions for media references."""
    all_refs: List[MediaReference] = []

    # Check section descriptions
    for sec in quiz.sections:
        if sec.description:
            sec_refs = extract_media_references(sec.description, question_id=sec.identifier)
            all_refs.extend(sec_refs)

    for q in quiz.questions:
        q_refs = extract_media_references(q.prompt, question_id=q.identifier)
        if q.feedback:
            q_refs.extend(extract_media_references(q.feedback, question_id=q.identifier))
        
        # Check choices or statements
        if isinstance(q, (SingleChoiceQuestion, MultipleChoiceQuestion, TrueFalseQuestion)):
            for c in q.choices:
                q_refs.extend(extract_media_references(c.text, question_id=q.identifier))
        elif isinstance(q, KprimQuestion):
            for s in q.statements:
                q_refs.extend(extract_media_references(s.text, question_id=q.identifier))
        elif isinstance(q, OrderQuestion):
            for item in q.items:
                q_refs.extend(extract_media_references(item.text, question_id=q.identifier))
        elif isinstance(q, FillBlankQuestion):
            for g in q.gaps:
                q_refs.extend(extract_media_references(g.expected_value, question_id=q.identifier))
                for alt in g.alternatives:
                    q_refs.extend(extract_media_references(alt, question_id=q.identifier))
        elif isinstance(q, InlineChoiceQuestion):
            for g in q.gaps:
                for c in g.choices:
                    q_refs.extend(extract_media_references(c.text, question_id=q.identifier))
        elif isinstance(q, HottextQuestion):
            for it in q.items:
                q_refs.extend(extract_media_references(it.text, question_id=q.identifier))
        elif isinstance(q, HotspotQuestion) and q.image_src:
            parsed = urllib.parse.urlparse(q.image_src)
            kind: Literal["remote", "relative"] = "remote" if parsed.scheme in ("http", "https") else "relative"
            q_refs.append(
                MediaReference(
                    source=q.image_src,
                    alt_text=q.image_alt,
                    kind=kind,
                    question_id=q.identifier,
                    line_number=q.line_number,
                )
            )

        all_refs.extend(q_refs)

    return all_refs


def _is_private_or_loopback_ip(ip_str: str) -> bool:
    """Check whether an IP address belongs to private, loopback, or link-local ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
        )
    except ValueError:
        return True


def _validate_remote_host(hostname: str) -> Optional[str]:
    """Validate remote host to prevent SSRF against private networks."""
    if not hostname:
        return "Missing hostname in URL."
    try:
        # Resolve hostname to IP
        addr_info = socket.getaddrinfo(hostname, None)
        for entry in addr_info:
            ip_str = entry[4][0]
            if _is_private_or_loopback_ip(ip_str):
                return f"Access to private/internal network address '{ip_str}' is forbidden."
    except Exception as e:
        return f"Cannot resolve host '{hostname}': {e}"
    return None


def _detect_image_mime(data: bytes) -> Optional[Tuple[str, str]]:
    """Detect image MIME type and file extension from magic bytes."""
    for magic, (mime, ext) in MAGIC_NUMBERS.items():
        if data.startswith(magic):
            return mime, ext
    # WebP check (RIFF....WEBP)
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def _extract_image_dimensions(data: bytes, mime_type: str) -> Optional[Tuple[int, int]]:
    """Extract intrinsic (width, height) in pixels from PNG or JPEG bytes."""
    if mime_type == "image/png":
        if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
            width, height = struct.unpack(">II", data[16:24])
            if 0 < width <= 32768 and 0 < height <= 32768:
                return int(width), int(height)
        return None

    elif mime_type == "image/jpeg":
        if len(data) < 4 or data[:2] != b"\xff\xd8":
            return None
        i = 2
        n = len(data)
        sof_markers = {
            0xC0, 0xC1, 0xC2, 0xC3,
            0xC5, 0xC6, 0xC7,
            0xC9, 0xCA, 0xCB,
            0xCD, 0xCE, 0xCF,
        }
        while i < n:
            if data[i] != 0xFF:
                i += 1
                continue
            while i < n and data[i] == 0xFF:
                i += 1
            if i >= n:
                break
            marker = data[i]
            i += 1
            if marker in (0xD9, 0xDA):  # EOI or SOS
                break
            if marker == 0x01 or (0xD0 <= marker <= 0xD7):
                continue
            if i + 2 > n:
                return None
            seg_len = struct.unpack(">H", data[i : i + 2])[0]
            if seg_len < 2 or i + seg_len > n:
                return None
            if marker in sof_markers:
                if seg_len < 7 or i + 7 > n:
                    return None
                height, width = struct.unpack(">HH", data[i + 3 : i + 7])
                if 0 < width <= 32768 and 0 < height <= 32768:
                    return int(width), int(height)
                return None
            i += seg_len
        return None

    return None


def _get_jpeg_exif_orientation(data: bytes) -> Optional[int]:
    """Extract JPEG EXIF Orientation tag (0x0112) from APP1 segment if present."""
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(data)
    while i < n:
        if data[i] != 0xFF:
            i += 1
            continue
        while i < n and data[i] == 0xFF:
            i += 1
        if i >= n:
            break
        marker = data[i]
        i += 1
        if marker in (0xD9, 0xDA):
            break
        if marker == 0x01 or (0xD0 <= marker <= 0xD7):
            continue
        if i + 2 > n:
            break
        seg_len = struct.unpack(">H", data[i : i + 2])[0]
        if seg_len < 2 or i + seg_len > n:
            break
        if marker == 0xE1 and seg_len >= 16:  # APP1
            seg_data = data[i + 2 : i + seg_len]
            if seg_data.startswith(b"Exif\x00\x00"):
                tiff = seg_data[6:]
                if len(tiff) >= 8:
                    byte_order = tiff[:2]
                    endian = "<" if byte_order == b"II" else (">" if byte_order == b"MM" else None)
                    if endian:
                        magic = struct.unpack(endian + "H", tiff[2:4])[0]
                        ifd_offset = struct.unpack(endian + "I", tiff[4:8])[0]
                        if magic == 42 and ifd_offset + 2 <= len(tiff):
                            num_entries = struct.unpack(endian + "H", tiff[ifd_offset : ifd_offset + 2])[0]
                            for idx in range(num_entries):
                                entry_pos = ifd_offset + 2 + idx * 12
                                if entry_pos + 12 > len(tiff):
                                    break
                                tag = struct.unpack(endian + "H", tiff[entry_pos : entry_pos + 2])[0]
                                if tag == 0x0112:
                                    orientation = struct.unpack(endian + "H", tiff[entry_pos + 8 : entry_pos + 10])[0]
                                    return int(orientation)
        i += seg_len
    return 1


def resolve_and_validate_hotspots(
    question: HotspotQuestion,
    resolved_image: ResolvedHotspotImage,
    question_index: Optional[int] = None,
) -> Tuple[Tuple[ResolvedHotspotRegion, ...], List[Diagnostic]]:
    """Stage 2 hotspot resolution: convert regions to intrinsic pixels and validate bounds/duplicates."""
    diagnostics: List[Diagnostic] = []
    resolved_regions: List[ResolvedHotspotRegion] = []
    seen_resolved: Set[Tuple[str, Tuple[int, ...]]] = set()
    w, h = resolved_image.width, resolved_image.height

    for idx, region in enumerate(question.regions, start=1):
        r_id = region.identifier or f"hc_{idx}"
        r_line = (
            region.source_location.choice_span.line_number
            if (region.source_location and region.source_location.choice_span.line_number)
            else question.line_number
        )
        px_coords = region.resolve_pixel_coords(w, h)

        if region.shape == "rect":
            x1, y1, x2, y2 = px_coords
            if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
                diagnostics.append(
                    Diagnostic(
                        f"Hotspot region {idx} ({r_id}): rectangle coordinates ({x1}, {y1}, {x2}, {y2}) exceed image bounds ({w}x{h} px).",
                        Severity.ERROR,
                        r_line,
                        question_index,
                    )
                )
            elif x1 >= x2 or y1 >= y2:
                diagnostics.append(
                    Diagnostic(
                        f"Hotspot region {idx} ({r_id}): resolved rectangle ({x1}, {y1}, {x2}, {y2}) has zero or negative width/height on {w}x{h} px image.",
                        Severity.ERROR,
                        r_line,
                        question_index,
                    )
                )
        elif region.shape == "circle":
            cx, cy, r = px_coords
            if r < 1:
                diagnostics.append(
                    Diagnostic(
                        f"Hotspot region {idx} ({r_id}): resolved circle radius ({r} px) must be at least 1 px.",
                        Severity.ERROR,
                        r_line,
                        question_index,
                    )
                )
            elif cx - r < 0 or cy - r < 0 or cx + r > w or cy + r > h:
                diagnostics.append(
                    Diagnostic(
                        f"Hotspot region {idx} ({r_id}): circle (cx={cx}, cy={cy}, r={r}) extends outside image bounds ({w}x{h} px).",
                        Severity.ERROR,
                        r_line,
                        question_index,
                    )
                )

        resolved_key = (region.shape, px_coords)
        if resolved_key in seen_resolved:
            diagnostics.append(
                Diagnostic(
                    f"Hotspot region {idx} ({r_id}): resolved pixel coordinates {px_coords} duplicate another region on this {w}x{h} px image.",
                    Severity.ERROR,
                    r_line,
                    question_index,
                )
            )
        seen_resolved.add(resolved_key)

        resolved_regions.append(
            ResolvedHotspotRegion(
                identifier=r_id,
                shape=region.shape,  # type: ignore[arg-type]
                pixel_coords=px_coords,
                correct=region.correct,
                author_label=region.author_label,
            )
        )

    return tuple(resolved_regions), diagnostics


def _is_safe_relative_path(path: str) -> bool:
    """Ensure relative path does not escape root (no ../, no leading slash, no Windows drive)."""
    clean = path.replace("\\", "/")
    if clean.startswith("/") or re.match(r"^[a-zA-Z]:", clean):
        return False
    parts = clean.split("/")
    depth = 0
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            depth -= 1
            if depth < 0:
                return False
        else:
            depth += 1
    return depth > 0


def preflight_media(
    quiz: Quiz,
    include_media: bool = False,
    media_zip_bytes: Optional[bytes] = None,
) -> MediaPreflightResult:
    """Perform passive or active media preflight for a Quiz.
    
    - When include_media is False: passive mode. Collects inventory, verifies URL schemes,
      and produces non-fatal diagnostics without any network or ZIP operations.
    - When include_media is True: active mode. Fetches remote images, extracts relative files
      from media_zip_bytes, validates MIME types and sizes, and deduplicates assets.
    """
    refs = extract_quiz_media_references(quiz)
    result = MediaPreflightResult(references=refs, include_media=include_media)

    if not refs:
        return result

    # Passive preflight checks
    for ref in refs:
        parsed = urllib.parse.urlparse(ref.source)
        if parsed.scheme and parsed.scheme not in ("http", "https"):
            result.diagnostics.append(
                Diagnostic(
                    f"Unsupported URL scheme '{parsed.scheme}:' in image reference: {ref.source}",
                    Severity.ERROR if include_media else Severity.WARNING,
                    ref.line_number,
                )
            )

    if not include_media:
        for q_idx, q in enumerate(quiz.questions):
            if isinstance(q, HotspotQuestion):
                result.diagnostics.append(
                    Diagnostic(
                        "Hotspot images must be packaged. Enable media packaging to download remote images or upload a media ZIP containing the referenced image.",
                        Severity.ERROR,
                        q.line_number,
                        q_idx,
                    )
                )
        return result

    # Active preflight: resolve assets
    zf: Optional[zipfile.ZipFile] = None
    zip_namelist: Set[str] = set()
    if media_zip_bytes:
        import io
        try:
            zf = zipfile.ZipFile(io.BytesIO(media_zip_bytes))
            zip_namelist = set(zf.namelist())
        except Exception as e:
            result.diagnostics.append(
                Diagnostic(f"Invalid or corrupted Media ZIP file: {e}", Severity.ERROR)
            )
            return result

    resolved_by_source: Dict[str, ResolvedAsset] = {}
    content_hash_to_path: Dict[str, str] = {}
    asset_counter = 1

    for ref in refs:
        src = ref.source
        if src in resolved_by_source:
            asset = resolved_by_source[src]
            result.source_to_package_path[src] = asset.filename
            if ref.question_id:
                result.question_asset_map.setdefault(ref.question_id, []).append(asset.filename)
            continue

        data: Optional[bytes] = None

        if ref.kind == "remote":
            parsed = urllib.parse.urlparse(src)
            host_err = _validate_remote_host(parsed.hostname or "")
            if host_err:
                result.diagnostics.append(
                    Diagnostic(f"Security error fetching '{src}': {host_err}", Severity.ERROR, ref.line_number)
                )
                continue

            try:
                req = urllib.request.Request(
                    src,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; QTI-Creator/1.0; +https://github.com/simon-clematide/QTI-Creator)"}
                )
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    if resp.status != 200:
                        result.diagnostics.append(
                            Diagnostic(f"HTTP {resp.status} error fetching image: {src}", Severity.ERROR, ref.line_number)
                        )
                        continue
                    content_length = resp.headers.get("Content-Length")
                    if content_length and int(content_length) > 10 * 1024 * 1024:
                        result.diagnostics.append(
                            Diagnostic(f"Image exceeds 10MB limit: {src}", Severity.ERROR, ref.line_number)
                        )
                        continue
                    data = resp.read(10 * 1024 * 1024 + 1)
                    if len(data) > 10 * 1024 * 1024:
                        result.diagnostics.append(
                            Diagnostic(f"Image exceeds 10MB limit: {src}", Severity.ERROR, ref.line_number)
                        )
                        continue
            except Exception as e:
                result.diagnostics.append(
                    Diagnostic(f"Failed to fetch image '{src}': {e}", Severity.ERROR, ref.line_number)
                )
                continue

        elif ref.kind == "relative":
            if not _is_safe_relative_path(src):
                result.diagnostics.append(
                    Diagnostic(
                        f"Unsafe relative path traversal attempt in image reference: '{src}'",
                        Severity.ERROR,
                        ref.line_number,
                    )
                )
                continue

            if not zf:
                result.diagnostics.append(
                    Diagnostic(
                        f"Relative image '{src}' referenced, but no Media ZIP was uploaded.",
                        Severity.ERROR,
                        ref.line_number,
                    )
                )
                continue

            normalized_src = src.replace("\\", "/").lstrip("./")
            if normalized_src not in zip_namelist:
                result.diagnostics.append(
                    Diagnostic(
                        f"Image '{src}' not found in uploaded Media ZIP.",
                        Severity.ERROR,
                        ref.line_number,
                    )
                )
                continue

            try:
                data = zf.read(normalized_src)
                if len(data) > 10 * 1024 * 1024:
                    result.diagnostics.append(
                        Diagnostic(f"Image '{src}' exceeds 10MB limit.", Severity.ERROR, ref.line_number)
                    )
                    continue
            except Exception as e:
                result.diagnostics.append(
                    Diagnostic(f"Failed to read '{src}' from Media ZIP: {e}", Severity.ERROR, ref.line_number)
                )
                continue

        if data is None:
            continue

        mime_info = _detect_image_mime(data)
        if not mime_info:
            result.diagnostics.append(
                Diagnostic(
                    f"Unsupported or invalid image format for '{src}'. Supported formats: PNG, JPEG, GIF, WebP.",
                    Severity.ERROR,
                    ref.line_number,
                )
            )
            continue

        mime_type, detected_ext = mime_info
        content_hash = hashlib.sha256(data).hexdigest()

        if content_hash in content_hash_to_path:
            package_path = content_hash_to_path[content_hash]
        else:
            clean_basename = os.path.basename(urllib.parse.urlparse(src).path)
            clean_name = re.sub(r"[^a-zA-Z0-9._-]", "_", clean_basename)
            if not clean_name or not any(clean_name.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp")):
                clean_name = f"image_{asset_counter:02d}{detected_ext}"
            
            package_path = f"media/{clean_name}"
            collision_idx = 1
            while package_path in content_hash_to_path.values():
                name_part, ext_part = os.path.splitext(clean_name)
                package_path = f"media/{name_part}_{collision_idx}{ext_part}"
                collision_idx += 1

            content_hash_to_path[content_hash] = package_path
            asset_counter += 1

        asset = ResolvedAsset(
            source=src,
            filename=package_path,
            content_type=mime_type,
            data=data,
            size_bytes=len(data),
            content_hash=content_hash,
        )
        resolved_by_source[src] = asset
        result.resolved_assets[src] = asset
        result.source_to_package_path[src] = package_path
        if ref.question_id:
            result.question_asset_map.setdefault(ref.question_id, []).append(package_path)

    # Resolve and validate Hotspot background images and pixel coordinates
    for q_idx, q in enumerate(quiz.questions):
        if isinstance(q, HotspotQuestion):
            asset = result.resolved_assets.get(q.image_src)
            if asset is None:
                continue

            if asset.content_type not in ("image/png", "image/jpeg"):
                result.diagnostics.append(
                    Diagnostic(
                        f"Hotspot background image '{q.image_src}' has unsupported format '{asset.content_type}'. Only PNG and JPEG are supported for Hotspot questions in Milestone 1.",
                        Severity.ERROR,
                        q.line_number,
                        q_idx,
                    )
                )
                continue

            if asset.content_type == "image/jpeg":
                orientation = _get_jpeg_exif_orientation(asset.data)
                if orientation is not None and orientation != 1:
                    result.diagnostics.append(
                        Diagnostic(
                            f"Hotspot JPEG image '{q.image_src}' has non-normal EXIF Orientation ({orientation}). Please normalize/rotate the image to Orientation=1 so hotspot coordinates align across browsers and OpenOLAT.",
                            Severity.ERROR,
                            q.line_number,
                            q_idx,
                        )
                    )
                    continue

            dims = _extract_image_dimensions(asset.data, asset.content_type)
            if dims is None:
                result.diagnostics.append(
                    Diagnostic(
                        f"Could not extract intrinsic pixel dimensions from Hotspot image '{q.image_src}'.",
                        Severity.ERROR,
                        q.line_number,
                        q_idx,
                    )
                )
                continue

            img_w, img_h = dims
            if (
                q.declared_width is not None
                and q.declared_height is not None
                and q.declared_width > 0
                and q.declared_height > 0
            ):
                intrinsic_ratio = img_w / img_h
                declared_ratio = q.declared_width / q.declared_height
                if abs(declared_ratio - intrinsic_ratio) / intrinsic_ratio > 0.01:
                    result.diagnostics.append(
                        Diagnostic(
                            f"Hotspot image '{q.image_src}' has intrinsic dimensions {img_w}x{img_h} (aspect ratio {intrinsic_ratio:.3f}), "
                            f"which differs by more than 1% from declared display dimensions {q.declared_width}x{q.declared_height} (aspect ratio {declared_ratio:.3f}). "
                            f"Hotspot coordinates are always resolved against intrinsic dimensions {img_w}x{img_h}.",
                            Severity.WARNING,
                            q.line_number,
                            q_idx,
                        )
                    )

            resolved_img = ResolvedHotspotImage(
                package_path=asset.filename,
                mime_type=asset.content_type,
                width=img_w,
                height=img_h,
                content_hash=asset.content_hash,
            )
            resolved_regs, reg_diags = resolve_and_validate_hotspots(q, resolved_img, question_index=q_idx)
            result.diagnostics.extend(reg_diags)
            result.resolved_hotspot_images[q.identifier] = resolved_img
            result.resolved_hotspot_regions[q.identifier] = resolved_regs

    return result
