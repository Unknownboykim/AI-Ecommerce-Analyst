"""
menu.py
-------
Terminal version of the analyst. Pick a numbered question from the menu,
or type search terms (for example "discount" or "low stock") to find one.

Usage:
    python menu.py                 # interactive menu
    python menu.py --list          # print the menu and exit
    python menu.py --run dead_stock [--no-ai]
"""

import argparse
import sys

import pandas as pd

from analyst import llm
from analyst.queries import CATALOG, GROUPS, Query, get_query, queries_in_group
from analyst.search import search
from analyst.service import answer

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_colwidth", 40)


def print_menu() -> None:
    number = 1
    for group in GROUPS:
        print(f"\n{group.upper()}")
        for q in queries_in_group(group):
            print(f"  {number:>2}. {q.title}")
            number += 1


def show_answer(query: Query, with_ai: bool) -> None:
    print("\n" + "=" * 70)
    print(query.question)
    print("=" * 70)

    try:
        result = answer(query, with_analysis=with_ai)
    except FileNotFoundError as e:
        print(f"\n{e}")
        return

    if result.data.empty:
        print("\nNo rows returned.")
    else:
        print("\n" + result.data.to_string(index=False, max_rows=30))
        print(f"\n({len(result.data)} rows)")

    if result.analysis:
        print("\nANALYSIS")
        print("-" * 70)
        print(result.analysis)
    elif result.note and with_ai:
        print(f"\n{result.note}")


def pick_from(matches: list[Query]) -> Query | None:
    """Let the user choose between several search results."""
    if len(matches) == 1:
        return matches[0]
    print("\nMatching questions:")
    for i, q in enumerate(matches, 1):
        print(f"  {i}. {q.title}")
    choice = input("Pick a number (Enter to cancel): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(matches):
        return matches[int(choice) - 1]
    return None


def interactive(with_ai: bool) -> None:
    print("\nECOMMERCE AI ANALYST")
    print("Enter a number, or type search terms like 'discount' or 'low stock'.")
    print("Commands: m = show menu, q = quit")
    if with_ai and not llm.is_configured():
        print("Note: OPENAI_API_KEY is not set, so results will show without AI analysis.")
    print_menu()

    while True:
        try:
            entry = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not entry:
            continue
        if entry.lower() in {"q", "quit", "exit"}:
            break
        if entry.lower() in {"m", "menu"}:
            print_menu()
            continue

        if entry.isdigit():
            n = int(entry)
            if 1 <= n <= len(CATALOG):
                # Menu numbering follows group order, which matches catalog order
                ordered = [q for g in GROUPS for q in queries_in_group(g)]
                show_answer(ordered[n - 1], with_ai)
            else:
                print(f"Pick a number from 1 to {len(CATALOG)}.")
            continue

        matches = search(entry)
        if not matches:
            print("No question matches those terms. Type 'm' to see the full menu.")
            continue
        chosen = pick_from(matches)
        if chosen:
            show_answer(chosen, with_ai)


def main() -> int:
    parser = argparse.ArgumentParser(description="Menu driven ecommerce analyst.")
    parser.add_argument("--list", action="store_true", help="print the menu with query keys and exit")
    parser.add_argument("--run", metavar="KEY", help="run one query by key and exit")
    parser.add_argument("--no-ai", action="store_true", help="skip the AI analysis")
    args = parser.parse_args()

    if args.list:
        for group in GROUPS:
            print(f"\n{group}")
            for q in queries_in_group(group):
                print(f"  {q.key:<28} {q.title}")
        return 0

    if args.run:
        try:
            show_answer(get_query(args.run), with_ai=not args.no_ai)
        except KeyError as e:
            print(e.args[0])
            return 1
        return 0

    interactive(with_ai=not args.no_ai)
    return 0


if __name__ == "__main__":
    sys.exit(main())
