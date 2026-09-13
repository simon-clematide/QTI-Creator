"""Comprehensive test suite for QuizMD media support and self-contained QTI packaging."""

import io
import unittest
import urllib.request
import zipfile
from unittest.mock import MagicMock, patch

from src.markdown import markdown_to_qti_xhtml
from src.media import (
    MediaReference,
    extract_media_references,
    extract_quiz_media_references,
    preflight_media,
)
from src.model import Choice, Question, Quiz, SingleChoiceQuestion
from src.packager import create_qti_package, create_qti_package_bytes
from src.parser import parse_quizmd
from src.validation import Severity

# Minimal valid 1x1 PNG binary bytes
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf"
    b"\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_media_zip(files: dict) -> bytes:
    """Helper to build an in-memory zip archive with given paths and byte contents."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, data in files.items():
            zf.writestr(path, data)
    return buf.getvalue()


class TestMediaSupport(unittest.TestCase):

    def test_markdown_image_vs_link(self):
        """Images ![alt](src) render to <img>, while links [text](src) render to <a>."""
        md = "See ![Tree Diagram](https://example.org/tree.png) and [Download](https://example.org/tree.png)."
        html = markdown_to_qti_xhtml(md)
        self.assertIn('<img src="https://example.org/tree.png" alt="Tree Diagram" />', html)
        self.assertIn('<a href="https://example.org/tree.png">Download</a>', html)

    def test_hackmd_image_sizing(self):
        """Images with HackMD size specifications (=300x, =30%x, =500x200) render with sizing attributes."""
        # Fixed width
        md_fixed = "![Diagram](diagram.png =300x)"
        html_fixed = markdown_to_qti_xhtml(md_fixed)
        self.assertIn('width="300px"', html_fixed)
        self.assertIn('alt="Diagram"', html_fixed)
        self.assertIn('max-width: 100%', html_fixed)

        # Proportional width
        md_prop = "![Chart](chart.png =30%x)"
        html_prop = markdown_to_qti_xhtml(md_prop)
        self.assertIn('width="30%"', html_prop)
        self.assertIn('alt="Chart"', html_prop)

        # Dimension width and height
        md_dim = "![Photo](photo.png =400x250)"
        html_dim = markdown_to_qti_xhtml(md_dim)
        self.assertIn('width="400px"', html_dim)
        self.assertIn('height="250px"', html_dim)

        # Media extraction parses the source URL cleanly without =size
        refs = extract_media_references(md_fixed)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].source, "diagram.png")
        self.assertEqual(refs[0].alt_text, "Diagram")

    def test_code_block_and_inline_code_media_protection(self):
        """Markdown images inside inline code or fenced code blocks must NOT be recognized as media."""
        md = """## Code Test
What does this syntax do?
```text
![not an image](code_fenced.png)
```
Also consider `![not an image either](code_inline.png)`.
- [X] Nothing
- [ ] Loads an image
"""
        quiz, _ = parse_quizmd(md)
        refs = extract_quiz_media_references(quiz)
        self.assertEqual(len(refs), 0, "Code blocks and inline code spans must not produce media references.")

    def test_passive_preflight_off_by_default(self):
        """When include_media is False, preflight collects inventory without network or ZIP operations."""
        md = """## Geography
![Map](https://example.org/map.png)
![Chart](images/chart.png)
Which is larger?
- [X] Map
- [ ] Chart
"""
        quiz, _ = parse_quizmd(md)
        result = preflight_media(quiz, include_media=False)
        self.assertEqual(len(result.references), 2)
        self.assertFalse(result.include_media)
        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.resolved_assets), 0)

        # Packaging with include_media=False retains original sources in QTI XML
        pkg_bytes = create_qti_package_bytes(quiz, media_preflight=result)
        with zipfile.ZipFile(io.BytesIO(pkg_bytes)) as zf:
            xml = zf.read(f"{quiz.questions[0].identifier}.xml").decode("utf-8")
            self.assertIn('src="https://example.org/map.png"', xml)
            self.assertIn('src="images/chart.png"', xml)
            # Media files should NOT be in the package
            self.assertNotIn("media/map.png", zf.namelist())

    def test_passive_preflight_reports_unsupported_schemes_as_warnings(self):
        """Passive preflight warns on unsupported schemes like file:/// without failing."""
        md = """## Question
![Local](file:///etc/passwd)
- [X] Yes
- [ ] No
"""
        quiz, _ = parse_quizmd(md)
        result = preflight_media(quiz, include_media=False)
        self.assertEqual(len(result.diagnostics), 1)
        self.assertEqual(result.diagnostics[0].severity, Severity.WARNING)
        self.assertFalse(result.has_errors)

    def test_active_preflight_relative_paths_with_zip(self):
        """Active preflight successfully resolves relative paths from root of uploaded media ZIP."""
        media_zip = make_media_zip({
            "diagrams/tree.png": TINY_PNG,
        })
        md = """## Linguistics
![Syntax Tree](diagrams/tree.png)
- [X] Correct
- [ ] Incorrect
"""
        quiz, _ = parse_quizmd(md)
        result = preflight_media(quiz, include_media=True, media_zip_bytes=media_zip)
        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.resolved_assets), 1)
        self.assertIn("diagrams/tree.png", result.resolved_assets)

        pkg_bytes = create_qti_package_bytes(quiz, media_preflight=result)
        with zipfile.ZipFile(io.BytesIO(pkg_bytes)) as zf:
            # Check packaged image
            self.assertIn("media/tree.png", zf.namelist())
            self.assertEqual(zf.read("media/tree.png"), TINY_PNG)
            # Check QTI XML rewritten
            xml = zf.read(f"{quiz.questions[0].identifier}.xml").decode("utf-8")
            self.assertIn('src="media/tree.png"', xml)
            # Check imsmanifest.xml includes media file under item resource
            manifest = zf.read("imsmanifest.xml").decode("utf-8")
            self.assertIn('<file href="media/tree.png"/>', manifest)

    def test_active_preflight_relative_path_missing_or_no_zip(self):
        """Active preflight fails cleanly if media ZIP is missing or path does not exist in ZIP."""
        md = """## Test
![Chart](charts/missing.png)
- [X] Yes
- [ ] No
"""
        quiz, _ = parse_quizmd(md)

        # 1. No zip provided
        res_no_zip = preflight_media(quiz, include_media=True, media_zip_bytes=None)
        self.assertTrue(res_no_zip.has_errors)
        self.assertTrue(any("no Media ZIP was uploaded" in d.message for d in res_no_zip.diagnostics))

        # 2. Path not in zip
        empty_zip = make_media_zip({"other.png": TINY_PNG})
        res_missing = preflight_media(quiz, include_media=True, media_zip_bytes=empty_zip)
        self.assertTrue(res_missing.has_errors)
        self.assertTrue(any("not found in uploaded Media ZIP" in d.message for d in res_missing.diagnostics))

    def test_active_preflight_rejects_path_traversal(self):
        """Paths attempting directory traversal (../) are rejected as security errors."""
        md = """## Traversal
![Escape](../../secret.png)
- [X] A
- [ ] B
"""
        quiz, _ = parse_quizmd(md)
        res = preflight_media(quiz, include_media=True, media_zip_bytes=make_media_zip({}))
        self.assertTrue(res.has_errors)
        self.assertTrue(any("traversal" in d.message for d in res.diagnostics))

    @patch("urllib.request.urlopen")
    @patch("socket.getaddrinfo")
    def test_active_preflight_remote_image_success_and_deduplication(self, mock_addr, mock_urlopen):
        """Remote image is fetched once, validated, packaged, and deduplicated across questions."""
        # Mock public IP resolution
        mock_addr.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
        
        # Mock HTTP 200 response
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Length": str(len(TINY_PNG))}
        mock_resp.read.return_value = TINY_PNG
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        md = """## Question 1
![Photo](https://example.org/photo.png)
- [X] A
- [ ] B

## Question 2
Here is the same photo again:
![Photo](https://example.org/photo.png)
- [X] C
- [ ] D
"""
        quiz, _ = parse_quizmd(md)
        result = preflight_media(quiz, include_media=True)
        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.resolved_assets), 1)
        # Verify network GET was called only once for deduplicated URL
        self.assertEqual(mock_urlopen.call_count, 1)

        pkg_bytes = create_qti_package_bytes(quiz, media_preflight=result)
        with zipfile.ZipFile(io.BytesIO(pkg_bytes)) as zf:
            self.assertIn("media/photo.png", zf.namelist())
            # Both questions use media/photo.png
            q1_xml = zf.read(f"{quiz.questions[0].identifier}.xml").decode("utf-8")
            q2_xml = zf.read(f"{quiz.questions[1].identifier}.xml").decode("utf-8")
            self.assertIn('src="media/photo.png"', q1_xml)
            self.assertIn('src="media/photo.png"', q2_xml)

    @patch("socket.getaddrinfo")
    def test_active_preflight_blocks_ssrf_private_networks(self, mock_addr):
        """Attempts to fetch from private IP addresses (RFC 1918, loopback) are blocked."""
        # Mock private IP 192.168.1.100
        mock_addr.return_value = [(2, 1, 6, "", ("192.168.1.100", 80))]

        md = """## SSRF Test
![Internal](http://internal-router.local/admin.png)
- [X] True
- [ ] False
"""
        quiz, _ = parse_quizmd(md)
        result = preflight_media(quiz, include_media=True)
        self.assertTrue(result.has_errors)
        self.assertTrue(any("private/internal network" in d.message for d in result.diagnostics))

    def test_zero_media_regression_baseline_identical(self):
        """Quizzes without media produce the exact same manifest and item XML as baseline."""
        md = """# Plain Quiz
## What is 2 + 2?
- [X] 4
- [ ] 5
"""
        quiz, _ = parse_quizmd(md)
        # Without preflight argument
        pkg_baseline = create_qti_package_bytes(quiz)
        # With preflight argument (passive or active)
        res_passive = preflight_media(quiz, include_media=False)
        pkg_with_preflight = create_qti_package_bytes(quiz, media_preflight=res_passive)

        with zipfile.ZipFile(io.BytesIO(pkg_baseline)) as zf_base:
            with zipfile.ZipFile(io.BytesIO(pkg_with_preflight)) as zf_test:
                self.assertEqual(zf_base.namelist(), zf_test.namelist())
                for name in zf_base.namelist():
                    self.assertEqual(zf_base.read(name), zf_test.read(name))


if __name__ == "__main__":
    unittest.main()
