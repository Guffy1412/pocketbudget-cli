import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import (
    BudgetExceededError,
    InsufficientFundsError,
    InvalidAmountError,
    UnknownCategoryError,
)


def _rich_account() -> Account:
    account = Account()
    account.add_income(1000, category="Salary")
    return account


def test_budget_can_be_set_and_read() -> None:
    account = _rich_account()
    account.set_budget("Food", 200)
    assert account.get_budget("Food") == 200


def test_category_without_budget_has_no_limit() -> None:
    account = _rich_account()
    assert account.get_budget("Food") is None
    assert account.remaining_budget("Food") is None


def test_expense_within_budget_is_recorded() -> None:
    account = _rich_account()
    account.set_budget("Food", 200)
    account.add_expense(150, category="Food")
    assert account.balance == 850
    assert account.remaining_budget("Food") == 50


def test_expense_exactly_at_limit_is_allowed() -> None:
    account = _rich_account()
    account.set_budget("Food", 200)
    account.add_expense(200, category="Food")
    assert account.remaining_budget("Food") == 0


def test_expense_over_budget_is_blocked_even_if_balance_covers_it() -> None:
    account = _rich_account()
    account.set_budget("Food", 200)
    with pytest.raises(BudgetExceededError):
        account.add_expense(200.01, category="Food")
    assert account.balance == 1000
    assert account.get_transactions()[-1].kind == "income"


def test_budget_accounts_for_earlier_spending() -> None:
    account = _rich_account()
    account.set_budget("Food", 200)
    account.add_expense(150, category="Food")
    with pytest.raises(BudgetExceededError):
        account.add_expense(60, category="Food")
    assert account.remaining_budget("Food") == 50


def test_budget_only_applies_to_its_own_category() -> None:
    account = _rich_account()
    account.set_budget("Food", 10)
    account.add_expense(500, category="Transport")
    assert account.balance == 500


def test_income_does_not_count_against_budget() -> None:
    account = _rich_account()
    account.set_budget("Food", 100)
    account.add_income(500, category="Food")
    assert account.remaining_budget("Food") == 100


def test_overspending_balance_is_still_blocked_within_budget() -> None:
    account = Account()
    account.add_income(50)
    account.set_budget("Food", 200)
    with pytest.raises(InsufficientFundsError):
        account.add_expense(100, category="Food")


@pytest.mark.parametrize("limit", [-5, 0])
def test_non_positive_budget_is_rejected(limit: int) -> None:
    with pytest.raises(InvalidAmountError):
        Account().set_budget("Food", limit)


def test_budget_for_unknown_category_is_rejected() -> None:
    with pytest.raises(UnknownCategoryError):
        Account().set_budget("Entertainment", 50)


def test_budget_cannot_be_set_below_amount_already_spent() -> None:
    account = _rich_account()
    account.add_expense(150, category="Food")
    with pytest.raises(InvalidAmountError):
        account.set_budget("Food", 100)
    assert account.get_budget("Food") is None


def test_budget_can_be_raised_and_lowered_above_spent() -> None:
    account = _rich_account()
    account.set_budget("Food", 200)
    account.add_expense(150, category="Food")
    account.set_budget("Food", 160)
    account.set_budget("Food", 400)
    assert account.remaining_budget("Food") == 250


def test_returned_budgets_are_a_copy() -> None:
    account = _rich_account()
    account.set_budget("Food", 200)
    account.get_budgets()["Food"] = 999_999
    account.get_budgets().clear()
    assert account.get_budget("Food") == 200


def test_spending_by_category_totals_expenses_only() -> None:
    account = _rich_account()
    account.add_expense(10, category="Food")
    account.add_expense(15, category="Food")
    account.add_expense(5, category="Transport")
    assert account.spending_by_category() == {"Food": 25, "Transport": 5}
