import dataclasses
from datetime import date

import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import InsufficientFundsError, InvalidAmountError


def _account_with_history() -> Account:
    account = Account()
    account.add_income(100, category="Salary", on=date(2026, 1, 1))
    account.add_expense(30, category="Food", on=date(2026, 1, 2))
    return account


def test_transactions_are_recorded_with_amount_category_and_date() -> None:
    history = _account_with_history().get_transactions()
    assert [(t.amount, t.category, t.date) for t in history] == [
        (100, "Salary", date(2026, 1, 1)),
        (30, "Food", date(2026, 1, 2)),
    ]


def test_new_account_has_empty_history() -> None:
    assert Account().get_transactions() == []


def test_rejected_transactions_are_not_recorded() -> None:
    account = Account()
    with pytest.raises(InvalidAmountError):
        account.add_income(-5)
    with pytest.raises(InsufficientFundsError):
        account.add_expense(10)
    assert account.get_transactions() == []


def test_clearing_returned_history_does_not_affect_account() -> None:
    account = _account_with_history()
    account.get_transactions().clear()
    assert len(account.get_transactions()) == 2


def test_popping_returned_history_does_not_affect_account() -> None:
    account = _account_with_history()
    account.get_transactions().pop()
    assert len(account.get_transactions()) == 2


def test_appending_to_returned_history_does_not_affect_account() -> None:
    account = _account_with_history()
    account.get_transactions().append("junk")  # type: ignore[arg-type]
    assert len(account.get_transactions()) == 2


def test_individual_transactions_cannot_be_modified() -> None:
    account = _account_with_history()
    with pytest.raises(dataclasses.FrozenInstanceError):
        account.get_transactions()[0].amount = 999  # type: ignore[misc]
    assert account.get_transactions()[0].amount == 100
