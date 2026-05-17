"""Exchange layer exceptions."""


class ExchangeError(Exception):
    """Base class for exchange connector errors."""


class PermissionVerificationError(ExchangeError):
    """Raised when API key permissions cannot be verified or are unsafe."""


class WithdrawalScopeError(PermissionVerificationError):
    """Raised when an API key has withdrawal permission (forbidden)."""


class OrderError(ExchangeError):
    """Raised when an order cannot be placed or cancelled."""
