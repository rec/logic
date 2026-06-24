import argparse
import random
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
