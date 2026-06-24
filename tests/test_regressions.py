import io
from contextlib import redirect_stdout

import logic
from pytest_regressions.file_regression import FileRegressionFixture


NOUNS = [
    "Alice",
    "White Rabbits",
    "Mad Hatters",
    "March Hares",
    "Dormice",
    "Cheshire Cats",
    "Queens of Hearts",
    "Kings of Hearts",
    "Knaves of Hearts",
    "Duchesses",
    "Mock Turtles",
    "Gryphons",
    "Caterpillars",
    "Dodos",
    "Lories",
    "Eaglets",
    "Bill the Lizards",
    "Footmen",
    "Gardeners",
    "Cards",
    "Flamingoes",
    "Hedgehogs",
    "Cookmaids",
    "Pigs",
]

ADJECTIVES = [
    "curious",
    "late",
    "grinning",
    "tea-drinking",
    "sleepy",
    "croquet-playing",
    "peppery",
    "weeping",
    "tiny",
    "enormous",
    "royal",
    "vanishing",
]


def render_puzzle(useful_count: int, decoy_count: int) -> str:
    puzzle = logic.make_puzzle(
        NOUNS,
        ADJECTIVES,
        useful_count,
        decoy_count,
        seed=useful_count * 100 + decoy_count,
    )
    output = io.StringIO()
    with redirect_stdout(output):
        logic.print_puzzle(puzzle)
    return output.getvalue()


def test_one_statement_no_decoys(file_regression: FileRegressionFixture) -> None:
    file_regression.check(render_puzzle(1, 0), extension=".txt")


def test_three_statements_one_decoy(file_regression: FileRegressionFixture) -> None:
    file_regression.check(render_puzzle(3, 1), extension=".txt")


def test_seven_statements_two_decoys(file_regression: FileRegressionFixture) -> None:
    file_regression.check(render_puzzle(7, 2), extension=".txt")


def test_twenty_three_statements_five_decoys(file_regression: FileRegressionFixture) -> None:
    file_regression.check(render_puzzle(23, 5), extension=".txt")
