"""Domain: budgeting rules and protected account state."""

import math
from dataclasses import dataclass
from datetime import date as Date

from pocketbudget.exceptions import (
    BudgetExceededError,
    InsufficientFundsError,
    InvalidAmountError,
    UnknownCategoryError,
)

DEFAULT_CATEGORY = "Uncategorized"
BUDGET_CATEGORIES = ("Food", "Transport", "Utilities")


@dataclass(frozen=True)
class Transaction:
    amount: float
    category: str
    date: Date
    kind: str  # "income" or "expense"


def _validate_amount(amount: float) -> None:
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise InvalidAmountError(f"Amount must be a number, got {amount!r}")
    if not math.isfinite(amount) or amount <= 0:
        raise InvalidAmountError(f"Amount must be positive, got {amount}")


def _validate_category(category: str) -> None:
    if not isinstance(category, str) or not category.strip():
        raise UnknownCategoryError(
            f"Category must be a non-empty name, got {category!r}"
        )


class Account:
    def __init__(self) -> None:
        self._balance: float = 0
        self._transactions: list[Transaction] = []
        self._budgets: dict[str, float] = {}

    @property
    def balance(self) -> float:
        return self._balance

    def get_transactions(self) -> list[Transaction]:
        # Copy so callers can't mutate our history; Transaction is frozen so
        # the shared records themselves are safe too.
        return list(self._transactions)

    def get_budgets(self) -> dict[str, float]:
        return dict(self._budgets)

    def get_budget(self, category: str) -> float | None:
        return self._budgets.get(category)

    def remaining_budget(self, category: str) -> float | None:
        limit = self._budgets.get(category)
        if limit is None:
            return None
        return limit - self._spent(category)

    def set_budget(self, category: str, limit: float) -> None:
        if category not in BUDGET_CATEGORIES:
            raise UnknownCategoryError(
                f"Unknown category {category!r}; "
                f"allowed: {', '.join(BUDGET_CATEGORIES)}"
            )
        _validate_amount(limit)
        spent = self._spent(category)
        if limit < spent:
            raise InvalidAmountError(
                f"Budget {limit} is below the {spent} already spent on {category}"
            )
        self._budgets[category] = limit

    def spending_by_category(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for t in self._transactions:
            if t.kind == "expense":
                totals[t.category] = totals.get(t.category, 0) + t.amount
        return totals

    def _spent(self, category: str) -> float:
        return sum(
            t.amount
            for t in self._transactions
            if t.kind == "expense" and t.category == category
        )

    def add_income(
        self,
        amount: float,
        category: str = DEFAULT_CATEGORY,
        on: Date | None = None,
    ) -> None:
        _validate_amount(amount)
        _validate_category(category)
        transaction = Transaction(amount, category, on or Date.today(), "income")
        self._balance += amount
        self._transactions.append(transaction)

    def add_expense(
        self,
        amount: float,
        category: str = DEFAULT_CATEGORY,
        on: Date | None = None,
    ) -> None:
        _validate_amount(amount)
        _validate_category(category)
        if amount > self._balance:
            raise InsufficientFundsError(
                f"Expense {amount} exceeds balance {self._balance}"
            )
        remaining = self.remaining_budget(category)
        if remaining is not None and amount > remaining:
            raise BudgetExceededError(
                f"Expense {amount} exceeds remaining {category} budget {remaining}"
            )
        transaction = Transaction(amount, category, on or Date.today(), "expense")
        self._balance -= amount
        self._transactions.append(transaction)
