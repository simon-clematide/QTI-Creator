"""Unit tests for src/difficulty.py."""

from __future__ import annotations

import math
import unittest

from src.difficulty import DifficultyReport, quiz_difficulty, question_difficulty
from src.model import (
    AssociationItem,
    AssociationQuestion,
    AssociationTarget,
    Choice,
    EssayQuestion,
    FillBlankQuestion,
    HottextItem,
    HottextQuestion,
    InlineChoice,
    InlineChoiceGap,
    InlineChoiceQuestion,
    KprimQuestion,
    KprimStatement,
    MultipleChoiceQuestion,
    NumericalQuestion,
    OrderItem,
    OrderQuestion,
    Quiz,
    SingleChoiceQuestion,
    TrueFalseQuestion,
)


def _sc(choices_correct: list[tuple[str, bool]], points: float = 1.0) -> SingleChoiceQuestion:
    """Build a SingleChoiceQuestion from (text, is_correct) pairs."""
    return SingleChoiceQuestion(
        prompt="Q?",
        title="Q",
        choices=[Choice(text=t, is_correct=c) for t, c in choices_correct],
        points=points,
    )


def _mc(choices_correct: list[tuple[str, bool]], scoring: str = "partial", points: float = 1.0) -> MultipleChoiceQuestion:
    return MultipleChoiceQuestion(
        prompt="Q?",
        title="Q",
        choices=[Choice(text=t, is_correct=c) for t, c in choices_correct],
        scoring=scoring,
        points=points,
    )


class TestSingleChoice(unittest.TestCase):

    def test_random_2_choices(self):
        q = _sc([("A", True), ("BB", False)])
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 0.5)

    def test_random_4_choices(self):
        q = _sc([("A", True), ("B", False), ("C", False), ("D", False)])
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 0.25)

    def test_bias_shortest_wins(self):
        # Correct answer is the shortest one
        q = _sc([("A", True), ("BBBB", False), ("CCC", False)])
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.shortest_score, 1.0)
        self.assertAlmostEqual(d.longest_score, 0.0)

    def test_bias_shortest_loses(self):
        # Correct answer is the longest one
        q = _sc([("A", False), ("BBBB", True), ("CC", False)])
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.shortest_score, 0.0)
        self.assertAlmostEqual(d.longest_score, 1.0)

    def test_bias_tie_all_tied_lengths(self):
        # All choices same length — all are tied shortest AND longest
        # correct is among them → score = 1.0
        q = _sc([("AA", True), ("BB", False), ("CC", False)])
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.shortest_score, 1.0)
        self.assertAlmostEqual(d.longest_score, 1.0)

    def test_points_scaling(self):
        q = _sc([("A", True), ("B", False)], points=4.0)
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 2.0)


class TestTrueFalse(unittest.TestCase):

    def test_random_half(self):
        q = TrueFalseQuestion(
            prompt="Q?",
            title="Q",
            choices=[Choice("True", True), Choice("False", False)],
        )
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 0.5)


class TestMultipleChoicePartial(unittest.TestCase):

    def test_random_balanced(self):
        # 2 correct, 2 wrong → (points/2) × (2-2)/2 = 0
        q = _mc([("A", True), ("B", True), ("C", False), ("D", False)], scoring="partial")
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 0.0)

    def test_random_all_correct(self):
        # All correct → (points/2) × (4-0)/4 = 0.5
        q = _mc([("A", True), ("B", True), ("C", True), ("D", True)], scoring="partial")
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 0.5)

    def test_random_more_correct_than_wrong(self):
        # 3 correct, 1 wrong → (1/2)×(3-1)/3 = 1/3
        q = _mc([("A", True), ("B", True), ("C", True), ("D", False)], scoring="partial")
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 1 / 3)

    def test_floor_at_zero(self):
        # More wrong than correct → formula gives negative → floored to 0
        q = _mc([("A", True), ("B", False), ("C", False), ("D", False)], scoring="partial")
        d = question_difficulty(q, 0)
        self.assertGreaterEqual(d.random_score, 0.0)

    def test_bias_shortest_selects_correct(self):
        # Shortest text is the only correct one → full points for shortest bias
        q = _mc([("A", True), ("BBBB", False)], scoring="partial", points=2.0)
        d = question_difficulty(q, 0)
        # selecting "A" only → 1 correct, 0 wrong → 2.0 points
        self.assertAlmostEqual(d.shortest_score, 2.0)


class TestMultipleChoiceAllCorrect(unittest.TestCase):

    def test_random_2_choices(self):
        q = _mc([("A", True), ("B", False)], scoring="all-correct")
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 0.25)  # (0.5)^2

    def test_random_3_choices(self):
        q = _mc([("A", True), ("B", True), ("C", False)], scoring="all-correct")
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 0.125)  # (0.5)^3

    def test_bias_matches_correct_set(self):
        # Only "A" is shortest and it is the only correct choice
        q = _mc([("A", True), ("BBBB", False)], scoring="all-correct")
        d = question_difficulty(q, 0)
        # selecting {A} == correct set {A} → 1.0
        self.assertAlmostEqual(d.shortest_score, 1.0)


class TestMultipleChoicePerAnswer(unittest.TestCase):

    def test_random_is_half_points(self):
        q = _mc([("A", True), ("B", True), ("C", False)], scoring="per-answer", points=2.0)
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 1.0)  # points/2

    def test_bias_selects_one_correct(self):
        # Shortest is correct, 2 correct total → 1/2 points
        q = _mc([("A", True), ("BB", True), ("CCC", False)], scoring="per-answer", points=2.0)
        d = question_difficulty(q, 0)
        # shortest = "A" (correct) → 1 correct selected out of 2 → 1.0 pts
        self.assertAlmostEqual(d.shortest_score, 1.0)


class TestKprim(unittest.TestCase):

    def test_random_5_over_16(self):
        stmts = [KprimStatement(text=f"S{i}", is_correct=(i < 2)) for i in range(4)]
        q = KprimQuestion(prompt="Q?", title="Q", statements=stmts, points=1.0)
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 3 / 16)

    def test_bias_equals_random_due_to_tied_lengths(self):
        stmts = [KprimStatement(text=f"S{i}", is_correct=(i < 2)) for i in range(4)]
        q = KprimQuestion(prompt="Q?", title="Q", statements=stmts, points=1.0)
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.shortest_score, d.random_score)
        self.assertAlmostEqual(d.longest_score, d.random_score)


class TestInlineChoice(unittest.TestCase):

    def _gap(self, choices: list[tuple[str, bool]]) -> InlineChoiceGap:
        return InlineChoiceGap(choices=[InlineChoice(text=t, is_correct=c) for t, c in choices])

    def test_single_gap_random(self):
        gap = self._gap([("A", True), ("BB", False), ("CCC", False)])
        q = InlineChoiceQuestion(prompt="Q?", title="Q", gaps=[gap], points=3.0)
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 1.0)  # 1/3 × 3 pts

    def test_two_gaps_average(self):
        # Gap 1: correct is shortest → bias 1.0; Gap 2: correct is longest → bias 1.0
        g1 = self._gap([("A", True), ("BBBB", False)])
        g2 = self._gap([("CC", False), ("DDDD", True)])
        q = InlineChoiceQuestion(prompt="Q?", title="Q", gaps=[g1, g2], points=2.0)
        d = question_difficulty(q, 0)
        # avg shortest: (1+0)/2 → 0.5 fraction × 2 pts = 1.0
        self.assertAlmostEqual(d.shortest_score, 1.0)
        # avg longest: (0+1)/2 → 0.5 fraction × 2 pts = 1.0
        self.assertAlmostEqual(d.longest_score, 1.0)

    def test_random_two_gaps(self):
        g1 = self._gap([("A", True), ("B", False)])
        g2 = self._gap([("X", True), ("Y", False), ("Z", False)])
        q = InlineChoiceQuestion(prompt="Q?", title="Q", gaps=[g1, g2], points=1.0)
        d = question_difficulty(q, 0)
        expected_random = ((1 / 2 + 1 / 3) / 2)  # avg per-gap probability × 1 pt
        self.assertAlmostEqual(d.random_score, expected_random, places=5)


class TestHottext(unittest.TestCase):

    def _ht(self, items: list[tuple[str, bool]], scoring="partial", points=1.0) -> HottextQuestion:
        return HottextQuestion(
            prompt="Q?",
            title="Q",
            items=[HottextItem(text=t, is_correct=c) for t, c in items],
            scoring=scoring,
            points=points,
        )

    def test_partial_random_balanced(self):
        q = self._ht([("A", True), ("B", True), ("C", False), ("D", False)])
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 0.0)  # 2 correct, 2 wrong → 0

    def test_all_correct_random(self):
        q = self._ht([("A", True), ("BB", False)], scoring="all-correct")
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 0.25)  # (0.5)^2

    def test_partial_bias_shortest_correct(self):
        q = self._ht([("A", True), ("BBBB", False)], scoring="partial", points=1.0)
        d = question_difficulty(q, 0)
        # selecting "A" only → 1 correct, 0 wrong → full points
        self.assertAlmostEqual(d.shortest_score, 1.0)


class TestOrder(unittest.TestCase):

    def test_random_factorial(self):
        items = [OrderItem(text=f"I{i}") for i in range(4)]
        q = OrderQuestion(prompt="Q?", title="Q", items=items, points=1.0)
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.random_score, 1 / math.factorial(4))

    def test_bias_equals_random(self):
        items = [OrderItem(text=f"Item {i}" if i % 2 == 0 else f"X") for i in range(4)]
        q = OrderQuestion(prompt="Q?", title="Q", items=items, points=1.0)
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.shortest_score, d.random_score)
        self.assertAlmostEqual(d.longest_score, d.random_score)


class TestAssociation(unittest.TestCase):

    def test_random_one_correct_per_item(self):
        t1 = AssociationTarget(text="Cat1")
        t2 = AssociationTarget(text="Cat2")
        i1 = AssociationItem(text="Item1", target_ids=[t1.identifier])
        i2 = AssociationItem(text="Item2", target_ids=[t2.identifier])
        q = AssociationQuestion(prompt="Q?", title="Q", items=[i1, i2], targets=[t1, t2], points=2.0)
        d = question_difficulty(q, 0)
        # 1 correct out of 2 targets per item → 0.5 fraction × 2 pts = 1.0
        self.assertAlmostEqual(d.random_score, 1.0)

    def test_bias_shortest_target_correct(self):
        t1 = AssociationTarget(text="A")      # shortest
        t2 = AssociationTarget(text="BBBBB")  # longest
        i1 = AssociationItem(text="Item1", target_ids=[t1.identifier])  # correct = shortest
        q = AssociationQuestion(prompt="Q?", title="Q", items=[i1], targets=[t1, t2], points=1.0)
        d = question_difficulty(q, 0)
        self.assertAlmostEqual(d.shortest_score, 1.0)
        self.assertAlmostEqual(d.longest_score, 0.0)


class TestSkippedTypes(unittest.TestCase):

    def test_essay_skipped(self):
        q = EssayQuestion(prompt="Q?", title="Q", points=1.0)
        d = question_difficulty(q, 0)
        self.assertTrue(d.skipped)
        self.assertEqual(d.random_score, 0.0)

    def test_numerical_skipped(self):
        q = NumericalQuestion(prompt="Q?", title="Q", points=1.0, answer=42.0)
        d = question_difficulty(q, 0)
        self.assertTrue(d.skipped)

    def test_fill_blank_skipped(self):
        from src.model import Gap
        q = FillBlankQuestion(prompt="Fill {{}}", title="Q", gaps=[Gap(expected_value="x")], points=1.0)
        d = question_difficulty(q, 0)
        self.assertTrue(d.skipped)


class TestQuizAggregation(unittest.TestCase):

    def test_weighted_mean(self):
        # Q1: single choice 2 choices, 1pt → random=0.5
        # Q2: single choice 4 choices, 3pt → random=0.25
        # weighted mean = (0.5×1 + 0.25×3) / 4 = 1.25/4 = 0.3125
        q1 = _sc([("A", True), ("B", False)], points=1.0)
        q2 = _sc([("A", True), ("B", False), ("C", False), ("D", False)], points=3.0)
        quiz = Quiz(title="T", questions=[q1, q2])
        report = quiz_difficulty(quiz)
        self.assertAlmostEqual(report.random_score, 0.3125, places=4)
        self.assertEqual(report.scorable_questions, 2)
        self.assertEqual(report.skipped_questions, 0)

    def test_skipped_counted(self):
        q1 = _sc([("A", True), ("B", False)])
        q2 = EssayQuestion(prompt="E?", title="E", points=2.0)
        quiz = Quiz(title="T", questions=[q1, q2])
        report = quiz_difficulty(quiz)
        self.assertEqual(report.scorable_questions, 1)
        self.assertEqual(report.skipped_questions, 1)

    def test_all_skipped_returns_zeros(self):
        quiz = Quiz(title="T", questions=[EssayQuestion(prompt="E?", title="E", points=1.0)])
        report = quiz_difficulty(quiz)
        self.assertEqual(report.random_score, 0.0)
        self.assertEqual(report.scorable_questions, 0)
        self.assertEqual(report.skipped_questions, 1)

    def test_per_question_count(self):
        q1 = _sc([("A", True), ("B", False)])
        q2 = EssayQuestion(prompt="E?", title="E", points=2.0)
        quiz = Quiz(title="T", questions=[q1, q2])
        report = quiz_difficulty(quiz)
        self.assertEqual(len(report.per_question), 2)
        self.assertEqual(report.per_question[0].question_index, 0)
        self.assertEqual(report.per_question[1].question_index, 1)


class TestBiasWarnings(unittest.TestCase):

    def test_shortest_bias_warning_fires(self):
        # All correct answers are the shortest → shortest_bias = 1.0 >> random 0.5
        q1 = _sc([("A", True), ("BB", False)])   # shortest is correct
        q2 = _sc([("X", True), ("YY", False)])   # shortest is correct
        quiz = Quiz(title="T", questions=[q1, q2])
        report = quiz_difficulty(quiz)
        self.assertGreater(report.shortest_bias, report.random_score + 0.005)
        self.assertTrue(any("Shortest" in w for w in report.bias_warnings))

    def test_longest_bias_warning_fires(self):
        # All correct answers are the longest → longest_bias = 1.0 >> random 0.5
        q1 = _sc([("AA", False), ("BBB", True)])
        q2 = _sc([("X", False), ("YYY", True)])
        quiz = Quiz(title="T", questions=[q1, q2])
        report = quiz_difficulty(quiz)
        self.assertGreater(report.longest_bias, report.random_score + 0.005)
        self.assertTrue(any("Longest" in w for w in report.bias_warnings))

    def test_no_warning_when_random_wins(self):
        # Random 1/4 > any deterministic bias (correct is in the middle length-wise)
        # Single choice 4 options, correct has mid-length → no length advantage
        q = _sc([("A", False), ("BB", True), ("CCC", False), ("DDDD", False)])
        quiz = Quiz(title="T", questions=[q])
        report = quiz_difficulty(quiz)
        # shortest bias picks "A" (wrong) → 0; longest picks "DDDD" (wrong) → 0
        # random = 0.25 > both biases → no warning
        self.assertEqual(report.bias_warnings, [])

    def test_kprim_no_warning_tied(self):
        # Kprim ± always tied → bias == random → no warning
        stmts = [KprimStatement(text=f"S{i}", is_correct=(i < 2)) for i in range(4)]
        q = KprimQuestion(prompt="Q?", title="Q", statements=stmts, points=1.0)
        quiz = Quiz(title="T", questions=[q])
        report = quiz_difficulty(quiz)
        self.assertEqual(report.bias_warnings, [])

    def test_both_warnings_can_fire(self):
        # All choices same length → tied → both shortest and longest pick all → correct included
        # 2-choice SC: tied lengths → both biases = 1.0 >> random 0.5
        q1 = _sc([("AA", True), ("BB", False)])   # both length 2, correct included in tie
        q2 = _sc([("XX", True), ("YY", False)])
        quiz = Quiz(title="T", questions=[q1, q2])
        report = quiz_difficulty(quiz)
        # shortest_bias = longest_bias = 1.0 > random 0.5 → both warn
        self.assertEqual(len(report.bias_warnings), 2)


if __name__ == "__main__":
    unittest.main()
