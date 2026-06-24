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
    prompt: str


ONSETS = [
    "b",
    "br",
    "d",
    "f",
    "fl",
    "g",
    "gl",
    "h",
    "k",
    "l",
    "m",
    "n",
    "p",
    "pr",
    "r",
    "s",
    "sh",
    "t",
    "tr",
    "v",
    "w",
    "z",
]

NUCLEI = [
    "a",
    "e",
    "i",
    "o",
    "u",
    "ai",
    "ee",
    "oa",
    "oo",
]

CODAS = [
    "",
    "",
    "",
    "l",
    "m",
    "n",
    "r",
    "s",
]


def random_word(min_syllables: int, max_syllables: int, rng: random.Random) -> str:
    if min_syllables < 1:
        raise ValueError("min_syllables must be at least 1.")
    if max_syllables < min_syllables:
        raise ValueError("max_syllables must be at least min_syllables.")

    syllables = [
        f"{rng.choice(ONSETS)}{rng.choice(NUCLEI)}{rng.choice(CODAS)}"
        for _ in range(rng.randint(min_syllables, max_syllables))
    ]
    return "".join(syllables)


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


def default_term_count(useful_count: int, decoy_count: int) -> int:
    return max(1, (useful_count + decoy_count) // 4)


def random_words(
    count: int,
    min_syllables: int,
    max_syllables: int,
    rng: random.Random,
) -> list[str]:
    if count < 1:
        raise ValueError("count must be at least 1.")

    words: list[str] = []
    seen: set[str] = set()
    while len(words) < count:
        word = random_word(min_syllables, max_syllables, rng)
        if word not in seen:
            seen.add(word)
            words.append(word)
    return words


def terms_from_args(args: argparse.Namespace) -> tuple[list[str], list[str]]:
    if args.terms is not None:
        return load_terms(args.terms)

    count = default_term_count(args.useful, args.decoy)
    noun_count = args.noun_count if args.noun_count is not None else count
    adjective_count = args.adjective_count if args.adjective_count is not None else count
    rng = random.Random(args.seed)
    nouns = random_words(noun_count, args.min_syllables, args.max_syllables, rng)
    adjectives = random_words(adjective_count, args.min_syllables, args.max_syllables, rng)
    return nouns, adjectives


def default_prompt(nouns: list[str], adjectives: list[str]) -> str:
    example = f"{adjectives[0]} {nouns[0]}"
    return (
        "Treat each two-word phrase as a single, atomic variable "
        f"(e.g., treat {example!r} as an indivisible token, not an intersection of two terms)."
    )


def build_terms(nouns: list[str], adjectives: list[str]) -> list[str]:
    terms = list(nouns)
    terms.extend(f"{adjective} {noun}" for adjective, noun in product(adjectives, nouns))
    return terms


def make_chain(terms: list[str], useful_count: int, rng: random.Random) -> tuple[list[Statement], Statement]:
    chosen = rng.sample(terms, useful_count + 1)
    statements: list[Statement] = []

    for index in range(useful_count):
        relation = "no" if index == useful_count - 1 else "all"
        statements.append(Statement(chosen[index], chosen[index + 1], relation))

    conclusion = Statement(chosen[0], chosen[-1], "no")
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
    prompt: str = "",
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
    return Puzzle(statements, conclusion, prompt)


def print_puzzle(puzzle: Puzzle) -> None:
    print("The Game of Logic")
    print()
    if puzzle.prompt:
        print(puzzle.prompt)
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
        help="JSON or TOML file containing nouns and adjectives lists.",
    )
    argument_parser.add_argument(
        "--min-syllables",
        type=int,
        default=3,
        help="Minimum syllables for generated random words.",
    )
    argument_parser.add_argument(
        "--max-syllables",
        type=int,
        default=5,
        help="Maximum syllables for generated random words.",
    )
    argument_parser.add_argument(
        "--noun-count",
        type=int,
        help="Number of random nouns to generate when --terms is omitted.",
    )
    argument_parser.add_argument(
        "--adjective-count",
        type=int,
        help="Number of random adjectives to generate when --terms is omitted.",
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
    argument_parser.add_argument(
        "--prompt",
        default="",
        help="Prompt text to print before the puzzle.",
    )
    return argument_parser


def main() -> None:
    args = parser().parse_args()

    if args.useful < 1:
        raise SystemExit("--useful must be at least 1.")
    if args.decoy < 0:
        raise SystemExit("--decoy cannot be negative.")
    if args.min_syllables < 1:
        raise SystemExit("--min-syllables must be at least 1.")
    if args.max_syllables < args.min_syllables:
        raise SystemExit("--max-syllables must be at least --min-syllables.")
    if args.noun_count is not None and args.noun_count < 1:
        raise SystemExit("--noun-count must be at least 1.")
    if args.adjective_count is not None and args.adjective_count < 1:
        raise SystemExit("--adjective-count must be at least 1.")

    nouns, adjectives = terms_from_args(args)
    if not nouns:
        raise SystemExit("At least one noun is required.")
    if not adjectives:
        raise SystemExit("At least one adjectival phrase is required.")
    prompt = args.prompt or default_prompt(nouns, adjectives)
    puzzle = make_puzzle(nouns, adjectives, args.useful, args.decoy, args.seed, prompt)
    print_puzzle(puzzle)


if __name__ == "__main__":
    main()
