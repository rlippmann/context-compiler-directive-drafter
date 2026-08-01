"""CLI entrypoint placeholder for directive drafting."""

import argparse
import sys


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
        help="Emit the current CLI status as JSON.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.user_input:
        parser.print_help(sys.stderr)
        return 2

    if args.json:
        print(
            '{"available": false, "reason": '
            '"The public high-level drafting API requires a host-provided engine."}'
        )
    else:
        print(
            "directive-drafter: the public high-level drafting API requires a "
            "host-provided engine.",
            file=sys.stderr,
        )

    return 1
