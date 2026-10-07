"""Custom domain exceptions."""


class InvalidAmountError(ValueError):
    """Raised when a transaction amount is not a positive number."""


class CorruptedDataError(Exception):
    """Raised when a save file is unreadable or fails validation."""


class InsufficientFundsError(ValueError):
    """Raised when an expense is larger than the available balance."""
