"""Domain: budgeting rules and protected account state."""

from dataclasses import dataclass
from datetime import date as Date

from pocketbudget.exceptions import InsufficientFundsError, InvalidAmountError

DEFAULT_CATEGORY = "Uncategorized"


@dataclass(frozen=True)
class Transaction:
    amount: float
    category: str
    date: Date
    kind: str  # "income" or "expense"


def _validate_amount(amount: float) -> None:
    if amount <= 0:
        raise InvalidAmountError(f"Amount must be positive, got {amount}")


class Account:
    def __init__(self) -> None:
        self._balance: float = 0
        self._transactions: list[Transaction] = []

    @property
    def balance(self) -> float:
        return self._balance

    def get_transactions(self) -> list[Transaction]:
        # Copy so callers can't mutate our history; Transaction is frozen so
        # the shared records themselves are safe too.
        return list(self._transactions)

    def add_income(
        self,
        amount: float,
        category: str = DEFAULT_CATEGORY,
        on: Date | None = None,
    ) -> None:
        _validate_amount(amount)
        self._balance += amount
        self._record(amount, category, on, "income")

    def add_expense(
        self,
        amount: float,
        category: str = DEFAULT_CATEGORY,
        on: Date | None = None,
    ) -> None:
        _validate_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError(
                f"Expense {amount} exceeds balance {self._balance}"
            )
        self._balance -= amount
        self._record(amount, category, on, "expense")

    def _record(
        self, amount: float, category: str, on: Date | None, kind: str
    ) -> None:
        self._transactions.append(
            Transaction(amount, category, on or Date.today(), kind)
        )
