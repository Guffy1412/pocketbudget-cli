"""Storage: saving and loading application state."""

import json
import math
import os
from datetime import date
from pathlib import Path
from typing import Any

from pocketbudget.account import Account
from pocketbudget.exceptions import (
    CorruptedDataError,
    PocketBudgetError,
    StorageError,
)

DEFAULT_PATH = Path("data") / "budget.json"


def save_account(account: Account, path: Path = DEFAULT_PATH) -> None:
    data = {
        "balance": account.balance,
        "budgets": account.get_budgets(),
        "transactions": [
            {
                "kind": t.kind,
                "amount": t.amount,
                "category": t.category,
                "date": t.date.isoformat(),
            }
            for t in account.get_transactions()
        ],
    }
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file then swap, so a failure can't corrupt the old save.
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        raise StorageError(f"Cannot save to {path}: {exc.strerror or exc}") from exc


def load_account(path: Path = DEFAULT_PATH) -> Account:
    """Rebuild an Account by replaying saved transactions through its public API.

    Raises CorruptedDataError if the file is unreadable or fails validation.
    """
    if not path.exists():
        return Account()

    data = _read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("transactions"), list):
        raise CorruptedDataError(f"{path} has an unexpected structure")

    account = Account()
    # Budgets go in first so replayed expenses are checked against them.
    _apply_budgets(account, data.get("budgets", {}))
    _replay_transactions(account, data["transactions"])
    _check_balance(account, data.get("balance"))
    return account


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorruptedDataError(f"Cannot read {path}: {exc}") from exc


def _apply_budgets(account: Account, budgets: Any) -> None:
    if not isinstance(budgets, dict):
        raise CorruptedDataError("budgets must be an object")
    for category, limit in budgets.items():
        try:
            account.set_budget(category, limit)
        except PocketBudgetError as exc:
            raise CorruptedDataError(f"Invalid budget {category!r}: {exc}") from exc


def _replay_transactions(account: Account, transactions: list[Any]) -> None:
    for index, raw in enumerate(transactions):
        try:
            _replay(account, raw)
        except (KeyError, TypeError, ValueError, PocketBudgetError) as exc:
            raise CorruptedDataError(f"Invalid transaction #{index}: {exc}") from exc


def _check_balance(account: Account, saved_balance: Any) -> None:
    if (
        isinstance(saved_balance, bool)
        or not isinstance(saved_balance, (int, float))
        or not math.isclose(saved_balance, account.balance)
    ):
        raise CorruptedDataError(
            f"Saved balance {saved_balance!r} does not match history "
            f"({account.balance})"
        )


def _replay(account: Account, raw: Any) -> None:
    """Feed one saved record through the domain; it does the amount/category checks."""
    if not isinstance(raw, dict):
        raise TypeError("transaction must be an object")
    if not isinstance(raw["date"], str):
        raise TypeError("date must be a string")
    when = date.fromisoformat(raw["date"])

    kind = raw["kind"]
    if kind == "income":
        account.add_income(raw["amount"], raw["category"], when)
    elif kind == "expense":
        account.add_expense(raw["amount"], raw["category"], when)
    else:
        raise ValueError(f"unknown kind {kind!r}")
