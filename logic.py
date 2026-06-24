#!/usr/bin/env python3

"""Generate Lewis Carroll-style syllogism puzzles."""

import argparse
import json
import random
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import cast


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


@dataclass(frozen=True)
class Closure:
    all_relations: set[tuple[str, str]]
    no_relations: set[frozenset[str]]
    empty_terms: set[str]


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
    if not isinstance(data, Mapping):
        raise SystemExit("Terms file must contain an object.")
    terms_data = cast(Mapping[str, object], data)
    value = terms_data.get(key)
    if not isinstance(value, list):
        raise SystemExit(f"Terms file must contain a list of strings named {key!r}.")
    terms: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise SystemExit(
                f"Terms file must contain a list of strings named {key!r}."
            )
        terms.append(item.strip())
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
    adjective_count = (
        args.adjective_count if args.adjective_count is not None else count
    )
    rng = random.Random(args.seed)
    nouns = random_words(noun_count, args.min_syllables, args.max_syllables, rng)
    adjectives = random_words(
        adjective_count,
        args.min_syllables,
        args.max_syllables,
        rng,
    )
    return nouns, adjectives


def default_prompt(nouns: list[str], adjectives: list[str]) -> str:
    example = f"{adjectives[0]} {nouns[0]}"
    return (
        "Treat each two-word phrase as a single, atomic variable "
        f"(e.g., treat {example!r} as an indivisible token, "
        "not an intersection of two terms)."
    )


def build_terms(nouns: list[str], adjectives: list[str]) -> list[str]:
    terms = list(nouns)
    terms.extend(
        f"{adjective} {noun}" for adjective, noun in product(adjectives, nouns)
    )
    return terms


def relation_count(term_count: int) -> int:
    return term_count * (term_count - 1) // 2


def decompose_relation_count(total: int) -> list[int]:
    counts: list[int] = []
    remaining = total
    while remaining > 0:
        term_count = 2
        while relation_count(term_count + 1) <= remaining:
            term_count += 1
        counts.append(term_count)
        remaining -= relation_count(term_count)
    return counts


def all_chain_statements(terms: list[str]) -> list[Statement]:
    return [
        Statement(terms[left], terms[right], "all")
        for left in range(len(terms))
        for right in range(left + 1, len(terms))
    ]


def make_useful_statements(
    terms: list[str],
    useful_count: int,
    rng: random.Random,
) -> tuple[list[Statement], Statement]:
    if useful_count == 1:
        subject, predicate = rng.sample(terms, 2)
        conclusion = Statement(subject, predicate, "all")
        return [conclusion], conclusion

    component_sizes = decompose_relation_count(useful_count + 1)
    required_terms = sum(component_sizes)
    chosen = rng.sample(terms, required_terms)
    useful: list[Statement] = []
    conclusion: Statement | None = None
    offset = 0

    for component_index, component_size in enumerate(component_sizes):
        component_terms = chosen[offset : offset + component_size]
        offset += component_size
        statements = all_chain_statements(component_terms)
        if component_index == 0:
            conclusion = Statement(component_terms[0], component_terms[-1], "all")
            statements = [
                statement for statement in statements if statement != conclusion
            ]
        useful.extend(statements)

    if conclusion is None:
        raise SystemExit("Could not generate a puzzle conclusion.")
    rng.shuffle(useful)
    return useful, conclusion


def make_decoys(
    terms: list[str],
    used_terms: set[str],
    decoy_count: int,
    rng: random.Random,
) -> list[Statement]:
    available = [term for term in terms if term not in used_terms]
    if len(available) < decoy_count * 2:
        available = terms[:]

    rng.shuffle(available)
    decoys: list[Statement] = []
    for index in range(decoy_count):
        subject = available[index * 2]
        predicate = available[index * 2 + 1]
        relation = rng.choice(["all", "no"])
        decoys.append(Statement(subject, predicate, relation))
    return decoys


def required_term_count(useful_count: int, decoy_count: int) -> int:
    if useful_count == 1:
        return 2 + decoy_count * 2
    return sum(decompose_relation_count(useful_count + 1)) + decoy_count * 2


def statement_terms(statements: list[Statement]) -> set[str]:
    terms = {statement.subject for statement in statements}
    terms.update(statement.predicate for statement in statements)
    return terms


def all_closure(statements: list[Statement]) -> set[tuple[str, str]]:
    terms = statement_terms(statements)
    reachable = {(term, term) for term in terms}
    reachable.update(
        (statement.subject, statement.predicate)
        for statement in statements
        if statement.relation == "all"
    )

    changed = True
    while changed:
        changed = False
        additions = {
            (left, right_next)
            for left, right in reachable
            for left_next, right_next in reachable
            if right == left_next and (left, right_next) not in reachable
        }
        if additions:
            reachable.update(additions)
            changed = True

    return reachable


def no_key(subject: str, predicate: str) -> frozenset[str]:
    return frozenset((subject, predicate))


def closure(statements: list[Statement]) -> Closure:
    reachable = all_closure(statements)
    no_relations: set[frozenset[str]] = set()
    for statement in statements:
        if statement.relation == "no":
            no_relations.add(no_key(statement.subject, statement.predicate))
            for left_subject, left_predicate in reachable:
                for right_subject, right_predicate in reachable:
                    if (
                        left_predicate == statement.subject
                        and right_predicate == statement.predicate
                    ):
                        no_relations.add(no_key(left_subject, right_subject))
                    if (
                        left_predicate == statement.predicate
                        and right_predicate == statement.subject
                    ):
                        no_relations.add(no_key(left_subject, right_subject))

    empty_terms = {
        term
        for term in statement_terms(statements)
        if any(
            (term, subject) in reachable and (term, predicate) in reachable
            for subject, predicate in (
                tuple(relation) for relation in no_relations if len(relation) == 2
            )
        )
    }

    return Closure(reachable, no_relations, empty_terms)


def term_is_forced_empty(statements: list[Statement], term: str) -> bool:
    return term in closure(statements).empty_terms


def conclusion_key(statement: Statement) -> tuple[str, str, str]:
    if statement.relation == "no":
        subject, predicate = sorted([statement.subject, statement.predicate])
        return statement.relation, subject, predicate
    return statement.relation, statement.subject, statement.predicate


def implied_conclusions(statements: list[Statement]) -> set[tuple[str, str, str]]:
    statement_closure = closure(statements)
    premise_keys = {conclusion_key(statement) for statement in statements}
    conclusions: set[tuple[str, str, str]] = set()

    for subject, predicate in statement_closure.all_relations:
        if subject == predicate or subject in statement_closure.empty_terms:
            continue
        key = conclusion_key(Statement(subject, predicate, "all"))
        if key not in premise_keys:
            conclusions.add(key)

    for relation in statement_closure.no_relations:
        if len(relation) != 2:
            continue
        subject, predicate = sorted(relation)
        if (
            subject in statement_closure.empty_terms
            or predicate in statement_closure.empty_terms
        ):
            continue
        key = conclusion_key(Statement(subject, predicate, "no"))
        if key not in premise_keys:
            conclusions.add(key)

    return conclusions


def has_unique_solution(statements: list[Statement], conclusion: Statement) -> bool:
    conclusions = implied_conclusions(statements)
    if conclusion in statements:
        return False
    return any(
        conclusion_key(conclusion) == key for key in conclusions
    ) and len(conclusions) == 1


def make_puzzle(
    nouns: list[str],
    adjectives: list[str],
    useful_count: int,
    decoy_count: int,
    seed: int | None,
    prompt: str = "",
) -> Puzzle:
    if useful_count < 2:
        raise SystemExit("Need at least 2 useful statements for a new conclusion.")

    terms = build_terms(nouns, adjectives)
    required_terms = required_term_count(useful_count, decoy_count)
    if len(terms) < required_terms:
        raise SystemExit(f"Need at least {required_terms} distinct terms.")

    rng = random.Random(seed)
    for _ in range(1000):
        useful, conclusion = make_useful_statements(terms, useful_count, rng)
        used_terms = {statement.subject for statement in useful}
        used_terms.update(statement.predicate for statement in useful)
        decoys = make_decoys(terms, used_terms, decoy_count, rng)

        statements = [*useful, *decoys]
        if has_unique_solution(statements, conclusion):
            rng.shuffle(statements)
            return Puzzle(statements, conclusion, prompt)

    raise SystemExit("Could not generate a puzzle with a unique solution.")


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
    print("What new statement follows?")
    print("Do not repeat a premise.")
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
        default=2,
        help="Minimum syllables for generated random words.",
    )
    argument_parser.add_argument(
        "--max-syllables",
        type=int,
        default=4,
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
        default=14,
        help="Number of useful statements in the puzzle.",
    )
    argument_parser.add_argument(
        "--decoy",
        type=int,
        default=3,
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

    if args.useful < 2:
        raise SystemExit("--useful must be at least 2.")
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
