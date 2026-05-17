"""Phase 3: permission verifier rejects withdrawal-scoped keys."""

import pytest

from app.exchanges.base import ExchangePermissions
from app.exchanges.errors import WithdrawalScopeError
from app.exchanges.permissions import verify_trade_only


class _FakeExchange:
    def __init__(self, perms: ExchangePermissions) -> None:
        self._perms = perms

    async def verify_permissions(self) -> ExchangePermissions:
        return self._perms


async def test_trade_only_key_accepted():
    perms = await verify_trade_only(
        _FakeExchange(ExchangePermissions(can_trade=True, can_withdraw=False))
    )
    assert perms.is_trade_only


async def test_withdrawal_scoped_key_rejected():
    with pytest.raises(WithdrawalScopeError):
        await verify_trade_only(
            _FakeExchange(ExchangePermissions(can_trade=True, can_withdraw=True))
        )


async def test_non_trading_key_rejected():
    with pytest.raises(WithdrawalScopeError):
        await verify_trade_only(
            _FakeExchange(ExchangePermissions(can_trade=False, can_withdraw=False))
        )
