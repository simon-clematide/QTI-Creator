"""Tests for the typed domain model invariants."""

import unittest
from src.model import (
    Choice,
    SingleChoiceQuestion,
    MultipleChoiceQuestion,
    TrueFalseQuestion,
    EssayQuestion,
    FillBlankQuestion,
    Gap,
    InlineChoice,
    InlineChoiceGap,
    InlineChoiceQuestion,
    NumericalQuestion,
    KprimQuestion,
    KprimStatement,
    Quiz,
)
from src.validation import QuizValidationError



class TestModelInvariants(unittest.TestCase):

    def test_single_choice_valid(self):
        q = SingleChoiceQuestion(
            prompt="What is 2+2?",
            choices=[
                Choice("3", is_correct=False),
                Choice("4", is_correct=True),
                Choice("5", is_correct=False),
            ],
        )
        self.assertEqual(q.points, 1.0)
        self.assertEqual(q.title, "What is 2+2?")

    def test_single_choice_invalid_zero_correct(self):
        with self.assertRaises(QuizValidationError):
            SingleChoiceQuestion(
                prompt="What is 2+2?",
                choices=[
                    Choice("3", is_correct=False),
                    Choice("4", is_correct=False),
                ],
            )

    def test_single_choice_invalid_multiple_correct(self):
        with self.assertRaises(QuizValidationError):
            SingleChoiceQuestion(
                prompt="What is 2+2?",
                choices=[
                    Choice("3", is_correct=True),
                    Choice("4", is_correct=True),
                ],
            )

    def test_multiple_choice_valid(self):
        q = MultipleChoiceQuestion(
            prompt="Select primes:",
            choices=[
                Choice("2", is_correct=True),
                Choice("3", is_correct=True),
                Choice("4", is_correct=False),
            ],
        )
        self.assertEqual(len(q.choices), 3)
        self.assertEqual(q.scoring, "partial")

    def test_multiple_choice_invalid_scoring(self):
        with self.assertRaises(QuizValidationError):
            MultipleChoiceQuestion(
                prompt="Select primes:",
                choices=[
                    Choice("2", is_correct=True),
                    Choice("3", is_correct=True),
                ],
                scoring="unsupported-scoring",
            )

    def test_multiple_choice_scoring_aliases_normalized(self):
        choices = [Choice("2", True), Choice("3", True), Choice("4", False)]
        
        for alias in ("all-correct", "all_correct", "allcorrect", " ALL-CORRECT "):
            q = MultipleChoiceQuestion(prompt="P", choices=choices, scoring=alias)
            self.assertEqual(q.scoring, "all-correct")

        for alias in ("per-answer", "per_answer", "points-per-answer", "points_per_answer", "PER-ANSWER"):
            q = MultipleChoiceQuestion(prompt="P", choices=choices, scoring=alias)
            self.assertEqual(q.scoring, "per-answer")

        for alias in ("partial", "PARTIAL", ""):
            q = MultipleChoiceQuestion(prompt="P", choices=choices, scoring=alias)
            self.assertEqual(q.scoring, "partial")


    def test_true_false_valid(self):
        q = TrueFalseQuestion(
            prompt="Sky is blue.",
            choices=[
                Choice("True", is_correct=True),
                Choice("False", is_correct=False),
            ],
        )
        self.assertEqual(len(q.choices), 2)

    def test_true_false_invalid_labels(self):
        with self.assertRaises(QuizValidationError):
            TrueFalseQuestion(
                prompt="Sky is blue.",
                choices=[
                    Choice("Yes", is_correct=True),
                    Choice("No", is_correct=False),
                ],
            )

    def test_fill_blank_valid(self):
        q = FillBlankQuestion(
            prompt="The capital is {{Paris}}.",
            gaps=[Gap("Paris")],
        )
        self.assertEqual(len(q.gaps), 1)

    def test_fill_blank_invalid_no_gaps(self):
        with self.assertRaises(QuizValidationError):
            FillBlankQuestion(
                prompt="No gaps here.",
                gaps=[],
            )

    def test_numerical_valid(self):
        q = NumericalQuestion(
            prompt="Gravitational constant?",
            answer=9.81,
            tolerance=0.05,
        )
        self.assertEqual(q.tolerance, 0.05)

    def test_numerical_negative_tolerance(self):
        with self.assertRaises(QuizValidationError):
            NumericalQuestion(
                prompt="Speed?",
                answer=100.0,
                tolerance=-1.0,
            )

    def test_kprim_valid(self):
        q = KprimQuestion(
            prompt="Mammals:",
            statements=[
                KprimStatement("Have hair", True),
                KprimStatement("Produce milk", True),
                KprimStatement("Lay eggs always", False),
                KprimStatement("Ectothermic", False),
            ],
        )
        self.assertEqual(len(q.statements), 4)

    def test_kprim_invalid_count(self):
        with self.assertRaises(QuizValidationError):
            KprimQuestion(
                prompt="Mammals:",
                statements=[
                    KprimStatement("Have hair", True),
                    KprimStatement("Produce milk", True),
                    KprimStatement("Lay eggs always", False),
                ],
            )

    def test_quiz_validation(self):
        quiz = Quiz(title="My Quiz")
        q1 = SingleChoiceQuestion(
            prompt="Q1",
            choices=[Choice("A", True), Choice("B", False)],
        )
        quiz.questions.append(q1)
        diags = quiz.validate()
        self.assertEqual(len(diags), 0)

    def test_section_markdown_title_warning(self):
        from src.model import Section
        from src.markdown import contains_markdown
        from src.validation import Severity

        # Test contains_markdown directly
        self.assertTrue(contains_markdown("**Bold Section**"))
        self.assertTrue(contains_markdown("*Italic Section*"))
        self.assertTrue(contains_markdown("`code snippet`"))
        self.assertTrue(contains_markdown("$O(n)$"))
        self.assertTrue(contains_markdown("[link](https://example.com)"))
        self.assertTrue(contains_markdown("![img](pic.png)"))
        self.assertFalse(contains_markdown("Plain Section Title: 1.2 & 3 - A / B"))

        # Test Section.validate emits warning
        sec = Section(title="**Bold** & *Italic* Section", questions=[])
        diags = sec.validate()
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0].severity, Severity.WARNING)
        self.assertIn("contains Markdown syntax", diags[0].message)
        self.assertIn("OpenOLAT does not format Markdown in section titles", diags[0].message)


    def test_inline_choice_valid(self):
        q = InlineChoiceQuestion(
            prompt="Choose {[Bern|Zurich]}",
            gaps=[
                InlineChoiceGap(
                    choices=[
                        InlineChoice("Bern", is_correct=True),
                        InlineChoice("Zurich", is_correct=False),
                    ]
                )
            ],
        )
        self.assertEqual(len(q.gaps), 1)
        self.assertEqual(len(q.gaps[0].choices), 2)

    def test_inline_choice_invalid_empty_gaps(self):
        with self.assertRaises(QuizValidationError):
            InlineChoiceQuestion(
                prompt="No gaps here",
                gaps=[],
            )

    def test_inline_choice_invalid_single_choice(self):
        with self.assertRaises(QuizValidationError):
            InlineChoiceQuestion(
                prompt="Gap with one choice",
                gaps=[
                    InlineChoiceGap(
                        choices=[InlineChoice("OnlyOne", is_correct=True)]
                    )
                ],
            )

    def test_inline_choice_invalid_no_correct(self):
        with self.assertRaises(QuizValidationError):
            InlineChoiceQuestion(
                prompt="Gap with no correct choice",
                gaps=[
                    InlineChoiceGap(
                        choices=[
                            InlineChoice("A", is_correct=False),
                            InlineChoice("B", is_correct=False),
                        ]
                    )
                ],
            )

    def test_inline_choice_invalid_multiple_correct(self):
        with self.assertRaises(QuizValidationError):
            InlineChoiceQuestion(
                prompt="Gap with multiple correct choices",
                gaps=[
                    InlineChoiceGap(
                        choices=[
                            InlineChoice("A", is_correct=True),
                            InlineChoice("B", is_correct=True),
                        ]
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main()



