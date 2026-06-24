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


if __name__ == "__main__":
    unittest.main()
