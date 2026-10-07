import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import InsufficientFundsError, InvalidAmountError


def test_new_account_starts_at_zero() -> None:
    assert Account().balance == 0


def test_add_income_increases_balance() -> None:
    account = Account()
    account.add_income(100)
    assert account.balance == 100


def test_add_expense_decreases_balance() -> None:
    account = Account()
    account.add_income(100)
    account.add_expense(30)
    assert account.balance == 70


def test_balance_cannot_be_assigned_from_outside() -> None:
    account = Account()
    with pytest.raises(AttributeError):
        account.balance = 500  # type: ignore[misc]
    assert account.balance == 0


@pytest.mark.parametrize("amount", [-1, 0])
def test_non_positive_income_is_rejected(amount: int) -> None:
    account = Account()
    with pytest.raises(InvalidAmountError):
        account.add_income(amount)
    assert account.balance == 0


@pytest.mark.parametrize("amount", [-1, 0])
def test_non_positive_expense_is_rejected(amount: int) -> None:
    account = Account()
    account.add_income(100)
    with pytest.raises(InvalidAmountError):
        account.add_expense(amount)
    assert account.balance == 100


def test_overspending_is_blocked_and_balance_unchanged() -> None:
    account = Account()
    account.add_income(50)
    with pytest.raises(InsufficientFundsError):
        account.add_expense(50.01)
    assert account.balance == 50


def test_spending_exact_balance_is_allowed() -> None:
    account = Account()
    account.add_income(50)
    account.add_expense(50)
    assert account.balance == 0
