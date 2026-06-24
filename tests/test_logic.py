import argparse
import io
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import logic


class LogicTests(unittest.TestCase):
    def test_loads_json_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "terms.json"
            path.write_text(
                '{"nouns": ["babies", "crocodiles"], "adjectives": ["red-haired"]}',
            )

            nouns, adjectives = logic.load_terms(path)

        self.assertEqual(nouns, ["babies", "crocodiles"])
        self.assertEqual(adjectives, ["red-haired"])

    def test_loads_toml_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "terms.toml"
            path.write_text(
                'nouns = ["babies", "crocodiles"]\n'
                'adjectives = ["red-haired", "sleepy"]\n',
            )

            nouns, adjectives = logic.load_terms(path)

        self.assertEqual(nouns, ["babies", "crocodiles"])
        self.assertEqual(adjectives, ["red-haired", "sleepy"])

    def test_rejects_non_string_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "terms.json"
            path.write_text('{"nouns": ["babies", 1], "adjectives": ["sleepy"]}')

            with self.assertRaises(SystemExit):
                logic.load_terms(path)

    def test_default_term_count_uses_quarter_of_statement_count(self) -> None:
        self.assertEqual(logic.default_term_count(17, 0), 4)
        self.assertEqual(logic.default_term_count(17, 5), 5)
        self.assertEqual(logic.default_term_count(1, 0), 1)

    def test_random_words_are_unique(self) -> None:
        rng = random.Random(123)
        words = logic.random_words(5, 3, 5, rng)

        self.assertEqual(len(words), 5)
        self.assertEqual(len(set(words)), 5)

    def test_terms_from_args_generates_missing_terms(self) -> None:
        args = argparse.Namespace(
            terms=None,
            useful=17,
            decoy=0,
            seed=123,
            min_syllables=3,
            max_syllables=5,
            noun_count=None,
            adjective_count=None,
        )

        nouns, adjectives = logic.terms_from_args(args)

        self.assertEqual(len(nouns), 4)
        self.assertEqual(len(adjectives), 4)

    def test_useful_statements_have_one_unstated_solution(self) -> None:
        terms = ["a", "b", "c", "d"]
        statements, conclusion = logic.make_useful_statements(
            terms,
            2,
            random.Random(0),
        )

        self.assertEqual(len(statements), 2)
        self.assertEqual(conclusion.relation, "all")
        self.assertTrue(logic.has_unique_solution(statements, conclusion))

    def test_detects_multiple_solutions(self) -> None:
        statements = [
            logic.Statement("a", "b", "all"),
            logic.Statement("b", "c", "all"),
            logic.Statement("c", "d", "all"),
        ]

        self.assertFalse(
            logic.has_unique_solution(statements, logic.Statement("a", "d", "all"))
        )

    def test_rejects_repeated_premise_as_solution(self) -> None:
        statement = logic.Statement("a", "b", "all")

        self.assertFalse(logic.has_unique_solution([statement], statement))

    def test_rejects_one_useful_statement_puzzles(self) -> None:
        with self.assertRaises(SystemExit):
            logic.make_puzzle(["a"], ["b"], 1, 0, seed=100)

    def test_generated_puzzle_has_unique_solution(self) -> None:
        puzzle = logic.make_puzzle(
            ["a", "b", "c", "d"],
            ["e", "f", "g", "h"],
            14,
            3,
            seed=1403,
        )

        self.assertTrue(logic.has_unique_solution(puzzle.statements, puzzle.conclusion))

    def test_detects_vacuous_conclusion_subject(self) -> None:
        statements = [
            logic.Statement("pairusfaroa", "rooloor", "all"),
            logic.Statement("pairusfaroa", "rooloor", "no"),
            logic.Statement("pairusfaroa", "preltre pairusfaroa", "all"),
            logic.Statement("goadin pairusfaroa", "goadin rooloor", "all"),
            logic.Statement("goadin rooloor", "preltre pairusfaroa", "all"),
            logic.Statement("preltre rooloor", "pairusfaroa", "all"),
            logic.Statement("preltre rooloor", "preltre pairusfaroa", "no"),
            logic.Statement("preltre pairusfaroa", "preltre rooloor", "all"),
        ]

        self.assertTrue(logic.term_is_forced_empty(statements, "goadin pairusfaroa"))

    def test_default_prompt_uses_first_generated_phrase(self) -> None:
        prompt = logic.default_prompt(["hatter"], ["mad"])

        self.assertEqual(
            prompt,
            "Treat each two-word phrase as a single, atomic variable "
            "(e.g., treat 'mad hatter' as an indivisible token, "
            "not an intersection of two terms).",
        )

    def test_print_puzzle_includes_prompt(self) -> None:
        puzzle = logic.Puzzle(
            [logic.Statement("a", "b", "all")],
            logic.Statement("a", "b", "all"),
            "Read atomically.",
        )
        output = io.StringIO()

        with redirect_stdout(output):
            logic.print_puzzle(puzzle)

        self.assertIn("Read atomically.\n\nPremises:", output.getvalue())
        self.assertIn(
            "\nWhat new statement follows?\nDo not repeat a premise.\n",
            output.getvalue(),
        )

    def test_parser_defaults_to_fourteen_useful_and_three_decoys(self) -> None:
        args = logic.parser().parse_args([])

        self.assertEqual(args.useful, 14)
        self.assertEqual(args.decoy, 3)
        self.assertEqual(args.min_syllables, 2)
        self.assertEqual(args.max_syllables, 4)


if __name__ == "__main__":
    unittest.main()
