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


if __name__ == "__main__":
    unittest.main()
