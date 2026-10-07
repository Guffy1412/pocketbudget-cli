from pathlib import Path

import pytest

from pocketbudget import cli


def run(tmp_path: Path, *args: str) -> int:
    return cli.main(list(args), tmp_path / "budget.json")


def test_show_balance_reports_balance_after_income(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(tmp_path, "add-income", "100", "Salary") == 0
    capsys.readouterr()

    assert run(tmp_path, "show-balance") == 0

    assert "$100.00" in capsys.readouterr().out


def test_state_persists_between_invocations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run(tmp_path, "add-income", "100", "Salary")
    run(tmp_path, "add-expense", "30.50", "Food")
    capsys.readouterr()

    run(tmp_path, "show-balance")

    assert "$69.50" in capsys.readouterr().out


def test_show_balance_on_fresh_install_is_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(tmp_path, "show-balance") == 0
    assert "$0.00" in capsys.readouterr().out


def test_overspending_is_reported_as_error_and_not_saved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run(tmp_path, "add-income", "50", "Salary")
    capsys.readouterr()

    assert run(tmp_path, "add-expense", "80", "Food") == 1
    captured = capsys.readouterr()
    assert "Error" in captured.err

    run(tmp_path, "show-balance")
    assert "$50.00" in capsys.readouterr().out


def test_negative_amount_is_reported_as_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(tmp_path, "add-income", "-5", "Salary") == 1
    assert "Error" in capsys.readouterr().err


def test_non_numeric_amount_is_rejected_by_parser(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        run(tmp_path, "add-income", "lots", "Salary")
    assert exc.value.code == 2


def test_budget_blocks_expense_through_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run(tmp_path, "add-income", "1000", "Salary")
    assert run(tmp_path, "set-budget", "Food", "100") == 0
    capsys.readouterr()

    assert run(tmp_path, "add-expense", "150", "Food") == 1
    assert "Error" in capsys.readouterr().err


def test_set_budget_unknown_category_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(tmp_path, "set-budget", "Entertainment", "50") == 1
    assert "Error" in capsys.readouterr().err


def test_show_history_lists_transactions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run(tmp_path, "add-income", "100", "Salary")
    run(tmp_path, "add-expense", "30", "Food")
    capsys.readouterr()

    assert run(tmp_path, "show-history") == 0

    out = capsys.readouterr().out
    assert "income" in out and "$100.00" in out and "Salary" in out
    assert "expense" in out and "$30.00" in out and "Food" in out


def test_show_history_when_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(tmp_path, "show-history") == 0
    assert "No transactions" in capsys.readouterr().out


def test_show_summary_compares_spending_to_budgets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run(tmp_path, "add-income", "1000", "Salary")
    run(tmp_path, "set-budget", "Food", "200")
    run(tmp_path, "add-expense", "150", "Food")
    run(tmp_path, "add-expense", "40", "Transport")
    capsys.readouterr()

    assert run(tmp_path, "show-summary") == 0

    out = capsys.readouterr().out
    assert "Food" in out and "$150.00" in out and "$200.00" in out
    assert "$50.00" in out  # remaining
    assert "Transport" in out and "$40.00" in out


def test_corrupted_save_file_is_reported_not_crashed_or_overwritten(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "budget.json"
    path.write_text("garbage", encoding="utf-8")

    assert cli.main(["add-income", "10", "Salary"], path) == 1

    assert "Error" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == "garbage"


def test_no_command_prints_usage_and_succeeds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(tmp_path) == 0
    assert "usage" in capsys.readouterr().out.lower()
