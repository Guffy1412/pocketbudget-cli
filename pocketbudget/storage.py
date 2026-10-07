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
    InsufficientFundsError,
    InvalidAmountError,
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
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file then swap, so a crash mid-write can't corrupt the save.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_account(path: Path = DEFAULT_PATH) -> Account:
    """Rebuild an Account by replaying saved transactions through its public API.

    Raises CorruptedDataError if the file is unreadable or fails validation.
    """
    if not path.exists():
        return Account()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorruptedDataError(f"Cannot read {path}: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("transactions"), list):
        raise CorruptedDataError(f"{path} has an unexpected structure")

    account = Account()
    budgets = data.get("budgets", {})
    if not isinstance(budgets, dict):
        raise CorruptedDataError("budgets must be an object")
    # Budgets go in first so replayed expenses are checked against them.
    for category, limit in budgets.items():
        try:
            if isinstance(limit, bool) or not isinstance(limit, (int, float)):
                raise TypeError("limit must be a number")
            account.set_budget(category, limit)
        except (TypeError, ValueError) as exc:
            raise CorruptedDataError(f"Invalid budget {category!r}: {exc}") from exc

    for index, raw in enumerate(data["transactions"]):
        try:
            _replay(account, raw)
        except (
            KeyError,
            TypeError,
            ValueError,  # includes InvalidAmountError, InsufficientFundsError
        ) as exc:
            raise CorruptedDataError(f"Invalid transaction #{index}: {exc}") from exc

    saved_balance = data.get("balance")
    if (
        isinstance(saved_balance, bool)
        or not isinstance(saved_balance, (int, float))
        or not math.isclose(saved_balance, account.balance)
    ):
        raise CorruptedDataError(
            f"Saved balance {saved_balance!r} does not match history "
            f"({account.balance})"
        )
    return account


def _replay(account: Account, raw: Any) -> None:
    if not isinstance(raw, dict):
        raise TypeError("transaction must be an object")
    amount, category = raw["amount"], raw["category"]
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise TypeError("amount must be a number")
    if not isinstance(category, str):
        raise TypeError("category must be a string")
    if not isinstance(raw["date"], str):
        raise TypeError("date must be a string")
    when = date.fromisoformat(raw["date"])

    kind = raw["kind"]
    if kind == "income":
        account.add_income(amount, category, when)
    elif kind == "expense":
        account.add_expense(amount, category, when)
    else:
        raise ValueError(f"unknown kind {kind!r}")
