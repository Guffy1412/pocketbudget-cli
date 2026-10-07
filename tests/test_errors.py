import math
from datetime import date
from pathlib import Path

import pytest

from pocketbudget import cli
from pocketbudget.account import Account
from pocketbudget.exceptions import (
    BudgetExceededError,
    CorruptedDataError,
    InsufficientFundsError,
    InvalidAmountError,
    PocketBudgetError,
    StorageError,
    UnknownCategoryError,
)
from pocketbudget.storage import load_account, save_account


def _snapshot(account: Account) -> tuple[object, ...]:
    return (
        account.balance,
        account.get_transactions(),
        account.get_budgets(),
        account.spending_by_category(),
    )


def _funded_account() -> Account:
    account = Account()
    account.add_income(500, category="Salary", on=date(2026, 1, 1))
    account.set_budget("Food", 100)
    account.add_expense(40, category="Food", on=date(2026, 1, 2))
    return account


# --- exception hierarchy -----------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        InvalidAmountError,
        InsufficientFundsError,
        BudgetExceededError,
        UnknownCategoryError,
        CorruptedDataError,
        StorageError,
    ],
)
def test_all_domain_errors_share_one_base(error: type[Exception]) -> None:
    assert issubclass(error, PocketBudgetError)


def test_distinct_failures_have_distinct_types() -> None:
    assert not issubclass(BudgetExceededError, InsufficientFundsError)
    assert not issubclass(InsufficientFundsError, BudgetExceededError)
    assert not issubclass(BudgetExceededError, CorruptedDataError)
    assert not issubclass(CorruptedDataError, BudgetExceededError)


# --- failures leave state untouched ------------------------------------------


@pytest.mark.parametrize("bad", [-1, 0, math.nan, math.inf, "5", None, True])
def test_bad_income_amount_raises_and_changes_nothing(bad: object) -> None:
    account = _funded_account()
    before = _snapshot(account)
    with pytest.raises(InvalidAmountError):
        account.add_income(bad)  # type: ignore[arg-type]
    assert _snapshot(account) == before


@pytest.mark.parametrize("bad", [-1, 0, math.nan, math.inf, "5", None, True])
def test_bad_expense_amount_raises_and_changes_nothing(bad: object) -> None:
    account = _funded_account()
    before = _snapshot(account)
    with pytest.raises(InvalidAmountError):
        account.add_expense(bad, category="Food")  # type: ignore[arg-type]
    assert _snapshot(account) == before


def test_over_budget_expense_raises_and_changes_nothing() -> None:
    account = _funded_account()
    before = _snapshot(account)
    with pytest.raises(BudgetExceededError):
        account.add_expense(60.01, category="Food")
    assert _snapshot(account) == before
    assert account.balance == 460


def test_overspending_raises_and_changes_nothing() -> None:
    account = _funded_account()
    before = _snapshot(account)
    with pytest.raises(InsufficientFundsError):
        account.add_expense(1000, category="Transport")
    assert _snapshot(account) == before


@pytest.mark.parametrize("category, limit", [("Food", 30), ("Food", -1), ("Pets", 10)])
def test_bad_budget_raises_and_changes_nothing(category: str, limit: float) -> None:
    account = _funded_account()
    before = _snapshot(account)
    with pytest.raises(PocketBudgetError):
        account.set_budget(category, limit)
    assert _snapshot(account) == before


def test_account_keeps_working_after_a_failure() -> None:
    account = _funded_account()
    with pytest.raises(BudgetExceededError):
        account.add_expense(70, category="Food")
    account.add_expense(10, category="Food")
    assert account.balance == 450


# --- storage failures --------------------------------------------------------


def test_corrupted_file_raises_corrupted_data_error(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(CorruptedDataError):
        load_account(path)
    assert path.read_text(encoding="utf-8") == "{ not json"


def test_unwritable_location_raises_storage_error(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a folder", encoding="utf-8")
    with pytest.raises(StorageError):
        save_account(_funded_account(), blocker / "budget.json")


def test_failed_save_leaves_previous_save_intact(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    save_account(_funded_account(), path)
    good = path.read_text(encoding="utf-8")

    path.with_name(path.name + ".tmp").mkdir()  # make the temp-file write fail
    with pytest.raises(StorageError):
        save_account(Account(), path)

    assert path.read_text(encoding="utf-8") == good


# --- the CLI turns errors into sentences, never tracebacks ---------------------


@pytest.mark.parametrize(
    "args",
    [
        ["add-income", "-5", "Salary"],
        ["add-income", "nan", "Salary"],
        ["add-income", "inf", "Salary"],
        ["add-expense", "999", "Food"],
        ["set-budget", "Pets", "10"],
        ["set-budget", "Food", "0"],
    ],
)
def test_cli_reports_domain_errors_cleanly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], args: list[str]
) -> None:
    assert cli.main(args, tmp_path / "budget.json") == 1
    err = capsys.readouterr().err
    assert err.startswith("Error: ")
    assert "Traceback" not in err


def test_cli_messages_differ_for_budget_and_corruption(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "budget.json"
    cli.main(["add-income", "1000", "Salary"], path)
    cli.main(["set-budget", "Food", "100"], path)
    capsys.readouterr()
    cli.main(["add-expense", "500", "Food"], path)
    budget_msg = capsys.readouterr().err

    path.write_text("garbage", encoding="utf-8")
    cli.main(["show-balance"], path)
    corrupt_msg = capsys.readouterr().err

    assert "exceeds" in budget_msg
    assert "Cannot read" in corrupt_msg
    assert budget_msg != corrupt_msg


def test_cli_reports_unwritable_save_location(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("file", encoding="utf-8")
    assert cli.main(["add-income", "5", "Salary"], blocker / "budget.json") == 1
    err = capsys.readouterr().err
    assert err.startswith("Error: ")
    assert "Traceback" not in err


def test_cli_does_not_swallow_unexpected_bugs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_: object, **__: object) -> None:
        raise RuntimeError("real bug")

    monkeypatch.setattr(cli, "load_account", boom)
    with pytest.raises(RuntimeError):
        cli.main(["show-balance"], tmp_path / "budget.json")


@pytest.mark.parametrize("bad", [None, "", "   ", 5])
def test_bad_category_raises_and_changes_nothing(bad: object) -> None:
    account = _funded_account()
    before = _snapshot(account)
    with pytest.raises(UnknownCategoryError):
        account.add_income(10, category=bad)  # type: ignore[arg-type]
    with pytest.raises(UnknownCategoryError):
        account.add_expense(10, category=bad)  # type: ignore[arg-type]
    assert _snapshot(account) == before
