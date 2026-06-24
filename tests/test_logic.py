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

    def test_negative_statement_ends_useful_chain(self) -> None:
        terms = ["a", "b", "c", "d"]
        statements, conclusion = logic.make_chain(terms, 3, random.Random(0))

        self.assertEqual(
            [statement.relation for statement in statements],
            ["all", "all", "no"],
        )
        self.assertEqual(conclusion.relation, "no")
        self.assertEqual(conclusion.subject, statements[0].subject)
        self.assertEqual(conclusion.predicate, statements[-1].predicate)

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

    def test_parser_defaults_to_fourteen_useful_and_three_decoys(self) -> None:
        args = logic.parser().parse_args([])

        self.assertEqual(args.useful, 14)
        self.assertEqual(args.decoy, 3)
        self.assertEqual(args.min_syllables, 2)
        self.assertEqual(args.max_syllables, 4)


if __name__ == "__main__":
    unittest.main()
