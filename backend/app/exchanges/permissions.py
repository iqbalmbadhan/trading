"""Permission verification: reject any API key that can withdraw."""

from app.exchanges.base import BaseExchange, ExchangePermissions
from app.exchanges.errors import WithdrawalScopeError


async def verify_trade_only(exchange: BaseExchange) -> ExchangePermissions:
    """Return permissions, raising if the key can withdraw or cannot trade.

    Withdrawal-scoped keys are a critical risk; this is the single
    chokepoint every connect path must pass through.
    """
    perms = await exchange.verify_permissions()
    if perms.can_withdraw:
        raise WithdrawalScopeError(
            "API key has withdrawal permission. Recreate the key with "
            "trade-only access (no withdrawal scope) and try again."
        )
    if not perms.can_trade:
        raise WithdrawalScopeError("API key cannot trade; check key permissions.")
    return perms
