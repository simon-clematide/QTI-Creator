"""Comprehensive tests for Milestone 1 Hotspot Image questions."""

import io
import struct
import unittest
import zipfile
import zlib

from src.difficulty import question_difficulty, quiz_difficulty
from src.jqti_validator import (
    is_java_available,
    is_javac_available,
    validate_qti_xml_string,
    validate_qti_zip_bytes,
)
from src.media import (
    ResolvedHotspotImage,
    _extract_image_dimensions,
    _get_jpeg_exif_orientation,
    preflight_media,
    resolve_and_validate_hotspots,
)
from src.model import (
    HotspotQuestion,
    HotspotRegion,
    InvalidQuestion,
    MultipleChoiceQuestion,
    SingleChoiceQuestion,
)
from src.packager import create_qti_package_bytes
from src.parser import parse_quizmd
from src.preview import render_quiz_preview_html
from src.qti21 import generate_item_xml
from src.validation import QuizValidationError, Severity

JAVA_PRESENT = is_java_available() and is_javac_available()


def make_png_bytes(width: int = 800, height: int = 600) -> bytes:
    """Create a valid minimal PNG image header + 1-pixel IDAT with arbitrary IHDR (width, height)."""
    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    # Minimal valid compressed scanline for a small image or header-valid PNG
    raw_idat = zlib.compress(b"\x00\x00\x00\x00")
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", raw_idat)
        + _chunk(b"IEND", b"")
    )


def make_jpeg_bytes(width: int = 1000, height: int = 500, exif_orientation: int | None = None) -> bytes:
    """Create a minimal valid JPEG byte stream with SOF0 (width, height) and optional EXIF Orientation."""
    segments = [b"\xff\xd8"]  # SOI
    if exif_orientation is not None:
        # Little-endian TIFF header ("II", 42, offset=8) + 1 IFD entry for Orientation (0x0112)
        tiff = (
            b"II"
            + struct.pack("<H", 42)
            + struct.pack("<I", 8)
            + struct.pack("<H", 1)
            + struct.pack("<HHII", 0x0112, 3, 1, exif_orientation)
            + struct.pack("<I", 0)
        )
        app1_payload = b"Exif\x00\x00" + tiff
        segments.append(b"\xff\xe1" + struct.pack(">H", len(app1_payload) + 2) + app1_payload)

    # SOF0 marker (0xFFC0): precision=8, height, width, components=3
    sof0_payload = struct.pack(">BHHB", 8, height, width, 1) + b"\x01\x11\x00"
    segments.append(b"\xff\xc0" + struct.pack(">H", len(sof0_payload) + 2) + sof0_payload)
    segments.append(b"\xff\xd9")  # EOI
    return b"".join(segments)


def make_media_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, data in files.items():
            zf.writestr(path, data)
    return buf.getvalue()


class TestHotspotMilestone1(unittest.TestCase):

    def test_single_and_multiple_choice_hotspot_parsing_and_spans(self):
        md = """# Anatomy & Hardware Quiz

## Identify the left ventricle.
Click the correct region in the diagram.
![Human heart](heart.png)
- [X] circle(65%, 60%, 10%) Left ventricle
- [ ] circle(35%, 60%, 10%) Right ventricle
- [ ] rect(28%, 25%, 45%, 45%) Right atrium

## Select all input devices.
![Computer peripherals](peripherals.jpg)
- [x] rectangle(5%, 53%, 48%, 87%) Keyboard
- [x] circle(65%, 70%, 8%) Mouse
- [ ] rect(23%, 5%, 78%, 48%) Monitor
"""
        quiz, diags = parse_quizmd(md)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(len(quiz.questions), 2)

        q1 = quiz.questions[0]
        self.assertIsInstance(q1, HotspotQuestion)
        self.assertFalse(q1.multiple)
        self.assertEqual(q1.image_src, "heart.png")
        self.assertEqual(q1.image_alt, "Human heart")
        self.assertEqual(q1.prompt, "Click the correct region in the diagram.")
        self.assertEqual([r.identifier for r in q1.regions], ["hc_1", "hc_2", "hc_3"])
        self.assertEqual(q1.regions[0].author_label, "Left ventricle")
        self.assertTrue(q1.regions[0].correct)
        self.assertEqual(q1.regions[0].unit, "pct")
        self.assertEqual(q1.regions[0].coordinates, (65.0, 60.0, 10.0))

        # Check exact character spans for visual editor readiness
        loc0 = q1.regions[0].source_location
        self.assertIsNotNone(loc0)
        self.assertEqual(
            md[loc0.choice_span.start_offset : loc0.choice_span.end_offset],
            "- [X] circle(65%, 60%, 10%) Left ventricle",
        )
        self.assertEqual(
            md[loc0.shape_span.start_offset : loc0.shape_span.end_offset],
            "circle(65%, 60%, 10%)",
        )

        q2 = quiz.questions[1]
        self.assertIsInstance(q2, HotspotQuestion)
        self.assertTrue(q2.multiple)
        self.assertEqual(q2.image_src, "peripherals.jpg")
        self.assertEqual(q2.regions[0].shape, "rect")  # rectangle normalized to rect

    def test_single_region_single_choice_is_valid_with_warning(self):
        md = """## Find the hidden star.
![Scene](scene.png)
- [X] circle(50%, 50%, 10%) Star
"""
        quiz, diags = parse_quizmd(md)
        errors = [d for d in diags if d.severity == Severity.ERROR]
        warnings = [d for d in diags if d.severity == Severity.WARNING]
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(warnings), 1)
        self.assertIn("only 1 region", warnings[0].message)
        self.assertIsInstance(quiz.questions[0], HotspotQuestion)

    def test_single_marked_lowercase_x_is_multiple_choice_hotspot(self):
        md = """## Select applicable regions.
![Map](map.png)
- [x] rect(10%, 10%, 30%, 30%) Region A
- [ ] rect(50%, 50%, 80%, 80%) Region B
"""
        quiz, diags = parse_quizmd(md)
        self.assertEqual(len(diags), 0)
        q = quiz.questions[0]
        self.assertIsInstance(q, HotspotQuestion)
        self.assertTrue(q.multiple)

    def test_two_stage_recognition_catches_all_malformed_shapes(self):
        """Even when every shape expression is malformed, parser emits Hotspot errors instead of falling back to SC."""
        md = """## Broken Hotspot
![Diagram](diagram.png)
- [X] circle(30%, 40%) Target missing radius
- [ ] rect(10%, 20%, 30%) Distractor missing y2
"""
        quiz, diags = parse_quizmd(md)
        errors = [d for d in diags if d.severity == Severity.ERROR]
        self.assertEqual(len(errors), 2)
        self.assertIsInstance(quiz.questions[0], InvalidQuestion)
        self.assertIn("requires 3 coordinates", errors[0].message)
        self.assertIn("requires 4 coordinates", errors[1].message)

    def test_mixed_shape_and_ordinary_choice_emits_ambiguity_error_and_explicit_type_override(self):
        md_ambiguous = """## Which notation is correct?
![Diagram](diagram.png)
- [X] circle(10, 20, 5)
- [ ] A standard circle with center (10, 20)
"""
        quiz, diags = parse_quizmd(md_ambiguous)
        errors = [d for d in diags if d.severity == Severity.ERROR]
        self.assertEqual(len(errors), 1)
        self.assertIn("Ambiguous Hotspot question", errors[0].message)
        self.assertIn("Type: single-choice", errors[0].message)

        # With explicit Type: single-choice, it parses as an ordinary SingleChoiceQuestion
        md_explicit_sc = """## Which notation is correct?
Type: single-choice
![Diagram](diagram.png)
- [X] circle(10, 20, 5)
- [ ] A standard circle with center (10, 20)
"""
        quiz_sc, diags_sc = parse_quizmd(md_explicit_sc)
        self.assertEqual(len(diags_sc), 0)
        self.assertIsInstance(quiz_sc.questions[0], SingleChoiceQuestion)

    def test_percentage_circle_cross_axis_validation_on_wide_image(self):
        """A circle(5%, 50%, 8%) on a 1200x600 image has cx=60, cy=300, r=48 and is completely inside the image."""
        md = """## Wide Image Circle Test
![Banner](banner.png)
- [X] circle(5%, 50%, 8%) Left target
- [ ] circle(50%, 50%, 10%) Center distractor
"""
        quiz, diags = parse_quizmd(md)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])

        media_zip = make_media_zip({"banner.png": make_png_bytes(1200, 600)})
        preflight = preflight_media(quiz, include_media=True, media_zip_bytes=media_zip)
        self.assertFalse(preflight.has_errors, [str(d) for d in preflight.diagnostics])

        q = quiz.questions[0]
        resolved_regs = preflight.resolved_hotspot_regions[q.identifier]
        self.assertEqual(resolved_regs[0].pixel_coords, (60, 300, 48))

        # Now test a circle that genuinely exceeds the left edge after pixel conversion:
        # circle(3%, 50%, 8%) on 1200x600 -> cx=36, cy=300, r=48 -> cx - r = -12 < 0
        md_oob = """## Wide Image OOB Circle Test
![Banner](banner.png)
- [X] circle(3%, 50%, 8%) Out of bounds left
- [ ] circle(50%, 50%, 10%) Center distractor
"""
        quiz_oob, diags_oob = parse_quizmd(md_oob)
        self.assertEqual(len(diags_oob), 0)
        preflight_oob = preflight_media(quiz_oob, include_media=True, media_zip_bytes=media_zip)
        self.assertTrue(preflight_oob.has_errors)
        self.assertTrue(any("extends outside image bounds" in d.message for d in preflight_oob.diagnostics))

    def test_intrinsic_vs_declared_dimensions_and_aspect_ratio_warning(self):
        """Coordinates always resolve against intrinsic image dimensions; aspect-ratio mismatch >1% warns."""
        md_matching_ratio = """## Heart Diagram
![Heart](heart.png =800x600)
- [X] rect(50%, 50%, 75%, 75%) Target
- [ ] rect(10%, 10%, 25%, 25%) Distractor
"""
        quiz, _ = parse_quizmd(md_matching_ratio)
        # Actual image is 1600x1200 (same 4:3 aspect ratio as 800x600)
        media_zip = make_media_zip({"heart.png": make_png_bytes(1600, 1200)})
        preflight = preflight_media(quiz, include_media=True, media_zip_bytes=media_zip)
        self.assertFalse(preflight.has_errors)
        self.assertEqual(len(preflight.diagnostics), 0)

        q = quiz.questions[0]
        resolved_img = preflight.resolved_hotspot_images[q.identifier]
        resolved_regs = preflight.resolved_hotspot_regions[q.identifier]
        self.assertEqual((resolved_img.width, resolved_img.height), (1600, 1200))
        self.assertEqual(resolved_regs[0].pixel_coords, (800, 600, 1200, 900))

        xml_str = generate_item_xml(q, resolved_image=resolved_img, resolved_regions=resolved_regs)
        self.assertIn('width="1600" height="1200"', xml_str)
        self.assertIn('coords="800,600,1200,900"', xml_str)

        # Mismatched declared aspect ratio (=800x800 vs 1600x1200) -> emits WARNING
        md_mismatch = """## Heart Diagram
![Heart](heart.png =800x800)
- [X] rect(50%, 50%, 75%, 75%) Target
- [ ] rect(10%, 10%, 25%, 25%) Distractor
"""
        quiz_mm, _ = parse_quizmd(md_mismatch)
        preflight_mm = preflight_media(quiz_mm, include_media=True, media_zip_bytes=media_zip)
        self.assertFalse(preflight_mm.has_errors)
        warnings = [d for d in preflight_mm.diagnostics if d.severity == Severity.WARNING]
        self.assertEqual(len(warnings), 1)
        self.assertIn("differs by more than 1%", warnings[0].message)

    def test_media_packaging_required_and_jpeg_exif_orientation_check(self):
        md = """## Photo Hotspot
![Photo](photo.jpg)
- [X] circle(50%, 50%, 20%) Center
- [ ] rect(5%, 5%, 20%, 20%) Corner
"""
        quiz, _ = parse_quizmd(md)

        # 1. include_media=False fails preflight and blocks package creation
        res_passive = preflight_media(quiz, include_media=False)
        self.assertTrue(res_passive.has_errors)
        self.assertTrue(any("Hotspot images must be packaged" in d.message for d in res_passive.diagnostics))
        with self.assertRaises(QuizValidationError):
            create_qti_package_bytes(quiz, media_preflight=res_passive)

        # 2. JPEG with EXIF Orientation=6 fails preflight
        rotated_zip = make_media_zip({"photo.jpg": make_jpeg_bytes(1000, 500, exif_orientation=6)})
        res_rotated = preflight_media(quiz, include_media=True, media_zip_bytes=rotated_zip)
        self.assertTrue(res_rotated.has_errors)
        self.assertTrue(any("EXIF Orientation (6)" in d.message for d in res_rotated.diagnostics))

        # 3. JPEG with EXIF Orientation=1 succeeds
        normal_zip = make_media_zip({"photo.jpg": make_jpeg_bytes(1000, 500, exif_orientation=1)})
        res_normal = preflight_media(quiz, include_media=True, media_zip_bytes=normal_zip)
        self.assertFalse(res_normal.has_errors, [str(d) for d in res_normal.diagnostics])
        q = quiz.questions[0]
        self.assertEqual(res_normal.resolved_hotspot_images[q.identifier].width, 1000)
        self.assertEqual(res_normal.resolved_hotspot_images[q.identifier].height, 500)
        # r = 20% of min(1000, 500) = 100
        self.assertEqual(res_normal.resolved_hotspot_regions[q.identifier][0].pixel_coords, (500, 250, 100))

    def test_author_labels_never_leaked_and_difficulty_skipped(self):
        md = """## Secret Label Test
Click the correct region.
![Diagram](diag.png)
- [X] circle(50%, 50%, 15%) SecretCorrectOrganName
- [ ] rect(10%, 10%, 25%, 25%) SecretDistractorName
"""
        quiz, _ = parse_quizmd(md)
        media_zip = make_media_zip({"diag.png": make_png_bytes(400, 400)})
        preflight = preflight_media(quiz, include_media=True, media_zip_bytes=media_zip)
        pkg_bytes = create_qti_package_bytes(quiz, media_preflight=preflight)

        with zipfile.ZipFile(io.BytesIO(pkg_bytes)) as zf:
            item_xml = zf.read(f"{quiz.questions[0].identifier}.xml").decode("utf-8")
            manifest_xml = zf.read("imsmanifest.xml").decode("utf-8")

        self.assertNotIn("SecretCorrectOrganName", item_xml)
        self.assertNotIn("SecretDistractorName", item_xml)
        self.assertNotIn("hotspotLabel", item_xml)
        self.assertNotIn("<img", item_xml)  # Standalone image stripped from <p> prompt
        self.assertIn('<hotspotInteraction responseIdentifier="RESPONSE" maxChoices="1" class="interaction-responsive">', item_xml)
        self.assertIn('<imsqti:interactionType>hotspotInteraction</imsqti:interactionType>', manifest_xml)
        self.assertIn('<ns4:questionType>hotspot</ns4:questionType>', manifest_xml)
        self.assertIn('<file href="media/diag.png"/>', manifest_xml)

        # Difficulty report skips HotspotQuestion with explanatory note
        diff_q = question_difficulty(quiz.questions[0], 0)
        self.assertTrue(diff_q.skipped)
        self.assertEqual(diff_q.note, "Difficulty estimate unavailable for image-based hotspot questions")
        report = quiz_difficulty(quiz)
        self.assertEqual(report.skipped_questions, 1)

    @unittest.skipUnless(JAVA_PRESENT, "Java and javac are required for JQTI+ runtime tests")
    def test_hotspot_packages_validate_in_jqtiplus(self):
        """Validate SC, MC (partial, all-correct, all-regions-correct, and with Hint) Hotspot packages in JQTI+."""
        md = """# Hotspot JQTI+ Validation Suite

## Q1: Single Choice Hotspot
Identify the left ventricle.
![Heart](heart.png)
- [X] circle(65%, 60%, 10%) Left ventricle
- [ ] circle(35%, 60%, 10%) Right ventricle
- [ ] rect(28%, 25%, 45%, 45%) Right atrium

## Q2: Multiple Choice Partial Scoring with Hint
Select all input devices.
![Peripherals](peripherals.jpg)
- [x] rect(5%, 53%, 48%, 87%) Keyboard
- [x] circle(65%, 70%, 8%) Mouse
- [ ] rect(23%, 5%, 78%, 48%) Monitor
### Hint
Look at the devices that send data to the computer.
### Feedback
Both the keyboard and mouse are input devices.

## Q3: Multiple Choice All-Correct Scoring
Scoring: all-correct
![Peripherals](peripherals.jpg)
- [x] rect(5%, 53%, 48%, 87%) Keyboard
- [x] circle(65%, 70%, 8%) Mouse
- [ ] rect(23%, 5%, 78%, 48%) Monitor

## Q4: Multiple Choice Partial Scoring Where All Regions Are Correct
![Heart](heart.png)
- [x] circle(65%, 60%, 10%) Region 1
- [x] circle(35%, 60%, 10%) Region 2
"""
        quiz, diags = parse_quizmd(md)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])

        media_zip = make_media_zip({
            "heart.png": make_png_bytes(800, 600),
            "peripherals.jpg": make_jpeg_bytes(1000, 800, exif_orientation=1),
        })
        preflight = preflight_media(quiz, include_media=True, media_zip_bytes=media_zip)
        self.assertFalse(preflight.has_errors, [str(d) for d in preflight.diagnostics])

        pkg_bytes = create_qti_package_bytes(quiz, media_preflight=preflight)
        is_valid, errors = validate_qti_zip_bytes(pkg_bytes)
        self.assertTrue(is_valid, f"Hotspot QTI package failed JQTI+ validation: {errors}")
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
