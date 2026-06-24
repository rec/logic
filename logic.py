#!/usr/bin/env python3

"""Generate Lewis Carroll-style syllogism puzzles."""

import argparse
import json
import random
import tomllib
from dataclasses import dataclass
from itertools import product
from pathlib import Path


@dataclass(frozen=True)
class Statement:
    subject: str
    predicate: str
    relation: str

    def text(self) -> str:
        if self.relation == "all":
            return f"All {self.subject} are {self.predicate}."
        return f"No {self.subject} are {self.predicate}."


@dataclass(frozen=True)
class Puzzle:
    statements: list[Statement]
    conclusion: Statement


def string_list(data: object, key: str) -> list[str]:
    if not isinstance(data, dict):
        raise SystemExit("Terms file must contain an object.")
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit(f"Terms file must contain a list of strings named {key!r}.")
    terms = [item.strip() for item in value]
    return [term for term in terms if term]


def load_terms(path: Path) -> tuple[list[str], list[str]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text())
    elif suffix == ".toml":
        data = tomllib.loads(path.read_text())
    else:
        raise SystemExit("Terms file must be JSON or TOML.")

    nouns = string_list(data, "nouns")
    adjectives = string_list(data, "adjectives")
    return nouns, adjectives


def build_terms(nouns: list[str], adjectives: list[str]) -> list[str]:
    terms = list(nouns)
    terms.extend(f"{adjective} {noun}" for adjective, noun in product(adjectives, nouns))
    return terms


def make_chain(terms: list[str], useful_count: int, rng: random.Random) -> tuple[list[Statement], Statement]:
    chosen = rng.sample(terms, useful_count + 1)
    negative_at = rng.randrange(useful_count)
    statements: list[Statement] = []

    for index in range(useful_count):
        relation = "no" if index == negative_at else "all"
        statements.append(Statement(chosen[index], chosen[index + 1], relation))

    conclusion_relation = "no" if any(statement.relation == "no" for statement in statements) else "all"
    conclusion = Statement(chosen[0], chosen[-1], conclusion_relation)
    return statements, conclusion


def make_decoys(
    terms: list[str],
    used_terms: set[str],
    decoy_count: int,
    rng: random.Random,
) -> list[Statement]:
    available = [term for term in terms if term not in used_terms]
    if len(available) < decoy_count * 2:
        available = terms[:]

    decoys: list[Statement] = []
    while len(decoys) < decoy_count:
        subject, predicate = rng.sample(available, 2)
        relation = rng.choice(["all", "no"])
        candidate = Statement(subject, predicate, relation)
        if candidate not in decoys:
            decoys.append(candidate)
    return decoys


def make_puzzle(
    nouns: list[str],
    adjectives: list[str],
    useful_count: int,
    decoy_count: int,
    seed: int | None,
) -> Puzzle:
    terms = build_terms(nouns, adjectives)
    required_terms = useful_count + 1
    if len(terms) < required_terms:
        raise SystemExit(f"Need at least {required_terms} distinct terms.")

    rng = random.Random(seed)
    useful, conclusion = make_chain(terms, useful_count, rng)
    used_terms = {statement.subject for statement in useful}
    used_terms.update(statement.predicate for statement in useful)
    decoys = make_decoys(terms, used_terms, decoy_count, rng)

    statements = [*useful, *decoys]
    rng.shuffle(statements)
    return Puzzle(statements, conclusion)


def print_puzzle(puzzle: Puzzle) -> None:
    print("The Game of Logic")
    print()
    print("Premises:")
    for index, statement in enumerate(puzzle.statements, start=1):
        print(f"{index}. {statement.text()}")
    print()
    print("What follows?")
    print()
    print(f"Answer: {puzzle.conclusion.text()}")


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(
        description="Generate a Lewis Carroll-style syllogism puzzle.",
    )
    argument_parser.add_argument(
        "--terms",
        type=Path,
        required=True,
        help="JSON or TOML file containing nouns and adjectives lists.",
    )
    argument_parser.add_argument(
        "--useful",
        type=int,
        required=True,
        help="Number of useful statements in the puzzle.",
    )
    argument_parser.add_argument(
        "--decoy",
        type=int,
        default=0,
        help="Number of unrelated decoy statements.",
    )
    argument_parser.add_argument(
        "--seed",
        type=int,
        help="Random seed.",
    )
    return argument_parser


def main() -> None:
    args = parser().parse_args()
    nouns, adjectives = load_terms(args.terms)

    if not nouns:
        raise SystemExit("At least one noun is required.")
    if not adjectives:
        raise SystemExit("At least one adjectival phrase is required.")
    if args.useful < 1:
        raise SystemExit("--useful must be at least 1.")
    if args.decoy < 0:
        raise SystemExit("--decoy cannot be negative.")

    puzzle = make_puzzle(nouns, adjectives, args.useful, args.decoy, args.seed)
    print_puzzle(puzzle)


if __name__ == "__main__":
    main()
