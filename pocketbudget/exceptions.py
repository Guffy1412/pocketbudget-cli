"""Custom domain exceptions."""


class InvalidAmountError(ValueError):
    """Raised when a transaction amount is not a positive number."""


class CorruptedDataError(Exception):
    """Raised when a save file is unreadable or fails validation."""


class BudgetExceededError(ValueError):
    """Raised when an expense would exceed its category's budget limit."""


class UnknownCategoryError(ValueError):
    """Raised when a category is not one of the allowed categories."""


class InsufficientFundsError(ValueError):
    """Raised when an expense is larger than the available balance."""
