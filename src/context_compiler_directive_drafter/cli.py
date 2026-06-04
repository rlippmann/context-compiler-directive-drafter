"""CLI entrypoint placeholder for directive drafting."""

import argparse
import json
import sys

from context_compiler_directive_drafter import draft_directive


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="directive-drafter",
        description="Draft candidate Context Compiler directives from natural-language input.",
    )
    parser.add_argument(
        "user_input",
        nargs="?",
        help="Natural-language text to draft into a candidate directive.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit placeholder result as JSON.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.user_input:
        parser.print_help(sys.stderr)
        return 2

    result = draft_directive(args.user_input)

    if args.json:
        print(json.dumps(result.__dict__, sort_keys=True))
    else:
        print("directive-drafter: drafting is not implemented yet.", file=sys.stderr)
        print(f"input: {result.user_input}", file=sys.stderr)
        print("candidate_directive: none", file=sys.stderr)

    return 1
