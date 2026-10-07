import json
from datetime import date
from pathlib import Path

import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import CorruptedDataError
from pocketbudget.storage import load_account, save_account


def _sample_account() -> Account:
    account = Account()
    account.add_income(100, category="Salary", on=date(2026, 1, 1))
    account.add_expense(30.5, category="Food", on=date(2026, 1, 2))
    return account


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_round_trip_preserves_balance_and_history(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    original = _sample_account()
    save_account(original, path)

    loaded = load_account(path)

    assert loaded.balance == original.balance
    assert loaded.get_transactions() == original.get_transactions()


def test_save_creates_missing_data_folder(tmp_path: Path) -> None:
    path = tmp_path / "data" / "budget.json"
    save_account(_sample_account(), path)
    assert path.exists()


def test_missing_file_gives_clean_empty_account(tmp_path: Path) -> None:
    account = load_account(tmp_path / "nope.json")
    assert account.balance == 0
    assert account.get_transactions() == []


@pytest.mark.parametrize(
    "garbage", ["", "not json at all", "{", "[1, 2, 3]", "null", '"text"']
)
def test_garbage_file_is_reported_not_crashed(tmp_path: Path, garbage: str) -> None:
    path = tmp_path / "budget.json"
    path.write_text(garbage, encoding="utf-8")
    with pytest.raises(CorruptedDataError):
        load_account(path)


def test_non_utf8_file_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    path.write_bytes(b"\xff\xfe\x00garbage")
    with pytest.raises(CorruptedDataError):
        load_account(path)


def _tx(**overrides: object) -> dict[str, object]:
    tx: dict[str, object] = {
        "kind": "income",
        "amount": 100,
        "category": "Salary",
        "date": "2026-01-01",
    }
    tx.update(overrides)
    return tx


@pytest.mark.parametrize(
    "bad_tx",
    [
        _tx(amount=-100),  # negative amount
        _tx(amount=0),
        _tx(amount="100"),  # wrong type
        _tx(amount=True),  # bool is not a money amount
        _tx(kind="gift"),  # unknown kind
        _tx(date="not-a-date"),
        _tx(date=20260101),
        _tx(category=5),
        "just a string",
    ],
)
def test_invalid_transaction_in_file_is_rejected(
    tmp_path: Path, bad_tx: object
) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": 100, "transactions": [bad_tx]})
    with pytest.raises(CorruptedDataError):
        load_account(path)


def test_missing_field_in_transaction_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    tx = _tx()
    del tx["category"]
    _write(path, {"balance": 100, "transactions": [tx]})
    with pytest.raises(CorruptedDataError):
        load_account(path)


def test_missing_transactions_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": 0})
    with pytest.raises(CorruptedDataError):
        load_account(path)


def test_history_that_overdraws_is_rejected(tmp_path: Path) -> None:
    """Same overspending rule applies to loaded data as to live data."""
    path = tmp_path / "budget.json"
    _write(path, {"balance": 0, "transactions": [_tx(kind="expense", amount=50)]})
    with pytest.raises(CorruptedDataError):
        load_account(path)


def test_hand_edited_balance_is_not_trusted(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": 1_000_000, "transactions": [_tx()]})
    with pytest.raises(CorruptedDataError):
        load_account(path)


def test_failed_load_does_not_modify_the_file(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    path.write_text("garbage", encoding="utf-8")
    with pytest.raises(CorruptedDataError):
        load_account(path)
    assert path.read_text(encoding="utf-8") == "garbage"
