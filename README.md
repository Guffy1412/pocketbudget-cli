# PocketBudget

PocketBudget is a small command-line app for tracking personal income and expenses in dollars. You set a spending limit per category (Food, Transport, Utilities), and the app blocks any expense that would overspend your balance or break a category budget, so your records can't drift out of sync with reality. Everything is saved to a local JSON file between runs.

## Installation & Setup

Requires Python 3.10+.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows (PowerShell): .venv\Scripts\Activate.ps1

# 2. Install dependencies (pytest, ruff, mypy, pre-commit)
pip install -r requirements.txt

# 3. Install the pre-commit hooks (ruff lint + complexity <= 7, ruff format, mypy --strict, pytest)
pre-commit install
```

## Usage

Run commands from the project root with `python -m pocketbudget <command>`. State is saved to `data/budget.json` after every change.

```bash
python -m pocketbudget add-income 1000 Salary      # record income
python -m pocketbudget set-budget Food 200         # cap a category
python -m pocketbudget add-expense 45.50 Food      # record an expense
python -m pocketbudget show-balance
python -m pocketbudget show-history
python -m pocketbudget show-summary
```

Example session:

```text
$ python -m pocketbudget add-income 1000 Salary
Added income $1000.00 to Salary
$ python -m pocketbudget set-budget Food 200
Budget for Food set to $200.00
$ python -m pocketbudget add-expense 45.50 Food
Recorded expense $45.50 in Food
$ python -m pocketbudget add-expense 250 Food
Error: Expense 250.0 exceeds remaining Food budget 154.5
$ python -m pocketbudget show-balance
Balance: $954.50
$ python -m pocketbudget show-summary
Food: $45.50 of $200.00 ($154.50 remaining)
```

| Command | Description |
| --- | --- |
| `add-income <amount> <category>` | Record income. |
| `add-expense <amount> <category>` | Record an expense; blocked if it overdraws the balance or exceeds the category budget. |
| `set-budget <category> <limit>` | Set a spending limit. Categories: `Food`, `Transport`, `Utilities`. |
| `show-balance` | Print the current balance. |
| `show-history` | List every transaction. |
| `show-summary` | Show spending per category against its budget. |

Rejected commands print a single `Error: ...` line, exit with status 1, and change nothing.

## Running the Tests

```bash
pytest
```

A passing run ends with every test green and no failures, for example `123 passed`. To run the full pre-commit suite (lint, complexity, types, tests) on demand:

```bash
pre-commit run --all-files
```

## Design Decisions

**The balance can be read but not assigned.** `Account.balance` is an `@property` with a getter and deliberately no setter, so `account.balance = 500` raises `AttributeError`. A leading underscore (`_balance`) is only a convention; the missing setter is what actually blocks assignment. The only ways to change the balance are `add_income()` and `add_expense()`.

**Validate first, then change state.** Each domain method checks everything (amount is a finite positive number, category is valid, funds cover the expense, the category budget has room) before it touches any state. A failed call raises a specific exception and leaves the balance, history and budgets exactly as they were. Because validation lives in the domain, no caller can skip it.

**The history can't be mutated from outside.** `get_transactions()` returns a copy of the internal list (`list(self._transactions)`), so calling `.clear()`, `.pop()` or `.append()` on the result doesn't affect the account. Each `Transaction` is a frozen dataclass, so the records inside that copy can't be edited either. The same applies to `get_budgets()`, which returns a copy of the budgets.

**State is derived, not duplicated.** Spending per category is computed from the transaction history rather than kept in a separate counter, so there is one source of truth and nothing to fall out of sync.

**Loading goes through the front door.** `load_account()` never writes to private attributes. It builds a fresh `Account` and replays the saved budgets and transactions through `set_budget()`, `add_income()` and `add_expense()`, so file data passes the same rules as typed input. A hand-edited or corrupted file raises `CorruptedDataError` instead of silently producing a wrong balance, and the saved balance is cross-checked against the replayed history. Saves write to a temporary file and swap it in, so a failed write can't damage the previous save.

**The CLI contains no business rules.** [pocketbudget/cli.py](pocketbudget/cli.py) parses arguments, calls the domain and storage layers, and prints results. It never compares amounts or computes balances. It catches the project's own `PocketBudgetError` hierarchy and turns each error into a one-line message, while real bugs still surface instead of being swallowed.

**Specific errors.** `InvalidAmountError`, `InsufficientFundsError`, `BudgetExceededError`, `UnknownCategoryError`, `CorruptedDataError` and `StorageError` share a base class, so callers can handle "you overspent your Food budget" separately from "that save file is unreadable".
