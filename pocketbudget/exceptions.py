"""Custom domain exceptions."""


class PocketBudgetError(Exception):
    """Base class for every error PocketBudget raises on purpose."""


class InvalidAmountError(PocketBudgetError):
    """Raised when a transaction amount is not a positive, finite number."""


class InsufficientFundsError(PocketBudgetError):
    """Raised when an expense is larger than the available balance."""


class BudgetExceededError(PocketBudgetError):
    """Raised when an expense would exceed its category's budget limit."""


class UnknownCategoryError(PocketBudgetError):
    """Raised when a category is not one of the allowed categories."""


class CorruptedDataError(PocketBudgetError):
    """Raised when a save file is unreadable or fails validation."""


class StorageError(PocketBudgetError):
    """Raised when the save file cannot be written."""
