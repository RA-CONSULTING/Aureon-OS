"""Simple script to print a motivational resilience message."""

from __future__ import annotations

import argparse


MESSAGE = "If you don't quit, you can't lose. Keep going."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prints a reminder to stay persistent and resilient."
    )
    parser.add_argument(
        "--uppercase",
        action="store_true",
        help="Display the message in uppercase letters for extra emphasis.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of times to repeat the message. Default is 1.",
    )
    return parser


def format_message(uppercase: bool) -> str:
    return MESSAGE.upper() if uppercase else MESSAGE


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    message = format_message(args.uppercase)
    for _ in range(max(args.repeat, 1)):
        print(message)


if __name__ == "__main__":
    main()
