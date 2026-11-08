"""Unit tests for src/patcher.py (Hotspot visual editor source synchronization)."""

import unittest

from src.parser import parse_quizmd
from src.patcher import (
    add_hotspot_region,
    compute_source_hash,
    delete_hotspot_region,
    format_shape_call,
    patch_hotspot_coordinates,
    toggle_hotspot_correctness,
    update_hotspot_author_label,
)


class TestHotspotPatcher(unittest.TestCase):
    def setUp(self):
        self.sample_sc = """# Anatomy Quiz

## Identify the left ventricle
Click the correct region in the diagram.
![Human heart](heart.png)
- [X] circle(65%, 60%, 10%) Left ventricle
- [ ] circle(35%, 60%, 10%) Right ventricle
- [ ] rect(28%, 25%, 45%, 45%) Right atrium

### Hint
Look at the bottom right of the heart from the anatomical perspective.
"""

        self.sample_mc = """# Peripherals Quiz

## Select all input devices
![Computer peripherals](peripherals.png)
- [x] rect(5%, 53%, 48%, 87%) Keyboard
- [x] circle(65%, 70%, 8%) Mouse
- [ ] rect(23%, 5%, 78%, 48%) Monitor
"""

    def test_patch_hotspot_coordinates_preserves_label_and_hint(self):
        h = compute_source_hash(self.sample_sc)
        new_source, err = patch_hotspot_coordinates(
            self.sample_sc,
            question_idx=1,
            region_idx=1,
            new_shape="circle",
            new_coords=(70.0, 62.5, 12.0),
            unit="pct",
            expected_hash=h,
        )
        self.assertIsNone(err)
        self.assertIn("- [X] circle(70%, 62.5%, 12%) Left ventricle", new_source)
        self.assertIn("### Hint\nLook at the bottom right", new_source)

        # Parse new source and verify model
        quiz, diags = parse_quizmd(new_source)
        self.assertEqual(len(diags), 0)
        self.assertEqual(quiz.questions[0].regions[0].coordinates, (70.0, 62.5, 12.0))

    def test_patch_hotspot_coordinates_with_pixels(self):
        new_source, err = patch_hotspot_coordinates(
            self.sample_sc,
            question_idx=1,
            region_idx=3,
            new_shape="rect",
            new_coords=(120, 150, 340, 410),
            unit="px",
        )
        self.assertIsNone(err)
        self.assertIn("- [ ] rect(120, 150, 340, 410) Right atrium", new_source)

    def test_stale_hash_protection(self):
        _, err = patch_hotspot_coordinates(
            self.sample_sc,
            question_idx=1,
            region_idx=1,
            new_shape="circle",
            new_coords=(10, 10, 5),
            expected_hash="stale_hash_value",
        )
        self.assertIsNotNone(err)
        self.assertIn("Source text was modified", err)

    def test_toggle_hotspot_correctness_sc(self):
        # Toggling region 2 (distractor) in SC should make region 2 [X] and unmark region 1 to [ ]
        new_source, err = toggle_hotspot_correctness(self.sample_sc, question_idx=1, region_idx=2)
        self.assertIsNone(err)
        self.assertIn("- [ ] circle(65%, 60%, 10%) Left ventricle", new_source)
        self.assertIn("- [X] circle(35%, 60%, 10%) Right ventricle", new_source)

        # Unmarking the only correct region in SC should error
        _, err2 = toggle_hotspot_correctness(new_source, question_idx=1, region_idx=2)
        self.assertIsNotNone(err2)
        self.assertIn("must have at least one correct", err2)

    def test_toggle_hotspot_correctness_mc(self):
        # In MC, toggling toggles between [x] and [ ]
        new_source, err = toggle_hotspot_correctness(self.sample_mc, question_idx=1, region_idx=1)
        self.assertIsNone(err)
        self.assertIn("- [ ] rect(5%, 53%, 48%, 87%) Keyboard", new_source)

        # Toggle back to [x]
        re_source, err2 = toggle_hotspot_correctness(new_source, question_idx=1, region_idx=1)
        self.assertIsNone(err2)
        self.assertIn("- [x] rect(5%, 53%, 48%, 87%) Keyboard", re_source)

    def test_delete_hotspot_region(self):
        new_source, err = delete_hotspot_region(self.sample_sc, question_idx=1, region_idx=2)
        self.assertIsNone(err)
        self.assertNotIn("Right ventricle", new_source)
        self.assertIn("Left ventricle", new_source)
        self.assertIn("Right atrium", new_source)

        # Cannot delete if only 1 region left
        source_single = """## Q\n![img](img.png)\n- [X] circle(10, 10, 5)\n"""
        _, err_single = delete_hotspot_region(source_single, question_idx=1, region_idx=1)
        self.assertIsNotNone(err_single)
        self.assertIn("Cannot delete the only region", err_single)

    def test_add_hotspot_region(self):
        new_source, err = add_hotspot_region(
            self.sample_sc,
            question_idx=1,
            shape="rect",
            coords=(10.0, 10.0, 20.0, 20.0),
            unit="pct",
            correct=False,
            author_label="Superior vena cava",
        )
        self.assertIsNone(err)
        self.assertIn("- [ ] rect(10%, 10%, 20%, 20%) Superior vena cava", new_source)
        self.assertIn("### Hint", new_source)

        quiz, diags = parse_quizmd(new_source)
        self.assertEqual(len(diags), 0)
        self.assertEqual(len(quiz.questions[0].regions), 4)

    def test_update_hotspot_author_label(self):
        new_source, err = update_hotspot_author_label(
            self.sample_sc,
            question_idx=1,
            region_idx=1,
            new_label="LV Apex",
        )
        self.assertIsNone(err)
        self.assertIn("- [X] circle(65%, 60%, 10%) LV Apex", new_source)
        self.assertNotIn("Left ventricle", new_source)


if __name__ == "__main__":
    unittest.main()
