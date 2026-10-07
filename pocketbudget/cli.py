"""CLI: user input and command routing."""

import argparse
import sys
from pathlib import Path

from pocketbudget.account import Account
from pocketbudget.exceptions import PocketBudgetError
from pocketbudget.storage import DEFAULT_PATH, load_account, save_account


def _money(amount: float) -> str:
    return f"${amount:.2f}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pocketbudget")
    commands = parser.add_subparsers(dest="command")

    income = commands.add_parser("add-income", help="record income")
    income.add_argument("amount", type=float)
    income.add_argument("category")

    expense = commands.add_parser("add-expense", help="record an expense")
    expense.add_argument("amount", type=float)
    expense.add_argument("category")

    budget = commands.add_parser("set-budget", help="set a category spending limit")
    budget.add_argument("category")
    budget.add_argument("limit", type=float)

    commands.add_parser("show-balance", help="print the current balance")
    commands.add_parser("show-history", help="list all transactions")
    commands.add_parser("show-summary", help="spending per category vs budgets")
    return parser


def _add_income(account: Account, args: argparse.Namespace) -> bool:
    account.add_income(args.amount, args.category)
    print(f"Added income {_money(args.amount)} to {args.category}")
    return True


def _add_expense(account: Account, args: argparse.Namespace) -> bool:
    account.add_expense(args.amount, args.category)
    print(f"Recorded expense {_money(args.amount)} in {args.category}")
    return True


def _set_budget(account: Account, args: argparse.Namespace) -> bool:
    account.set_budget(args.category, args.limit)
    print(f"Budget for {args.category} set to {_money(args.limit)}")
    return True


def _show_balance(account: Account, args: argparse.Namespace) -> bool:
    print(f"Balance: {_money(account.balance)}")
    return False


def _show_history(account: Account, args: argparse.Namespace) -> bool:
    transactions = account.get_transactions()
    if not transactions:
        print("No transactions yet.")
    for t in transactions:
        print(f"{t.date}  {t.kind:<7}  {_money(t.amount):>10}  {t.category}")
    return False


def _show_summary(account: Account, args: argparse.Namespace) -> bool:
    spending = account.spending_by_category()
    budgets = account.get_budgets()
    categories = sorted(set(spending) | set(budgets))
    if not categories:
        print("No spending or budgets yet.")
    for category in categories:
        spent = _money(spending.get(category, 0))
        remaining = account.remaining_budget(category)
        if remaining is None:
            print(f"{category}: {spent} spent (no budget)")
        else:
            print(
                f"{category}: {spent} of {_money(budgets[category])} "
                f"({_money(remaining)} remaining)"
            )
    return False


# Each handler returns True if it changed state and the account must be saved.
_HANDLERS = {
    "add-income": _add_income,
    "add-expense": _add_expense,
    "set-budget": _set_budget,
    "show-balance": _show_balance,
    "show-history": _show_history,
    "show-summary": _show_summary,
}


def main(argv: list[str], data_path: Path = DEFAULT_PATH) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    try:
        account = load_account(data_path)
        if _HANDLERS[args.command](account, args):
            save_account(account, data_path)
    except PocketBudgetError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0
