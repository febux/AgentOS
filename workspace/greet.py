#!/usr/bin/env python3
"""CLI-утилита: приветствует пользователя по имени."""

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a greeting.")
    parser.add_argument("name", help="имя для приветствия")
    args = parser.parse_args()
    print(f"Hello, {args.name}!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
