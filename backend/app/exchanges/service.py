"""Persistence and lifecycle for exchange accounts.

Credentials are envelope-encrypted before they touch the database and are
only decrypted in-memory when an adapter is built. Plaintext keys are never
logged or returned by the API.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret
from app.db.models import ExchangeAccount
from app.exchanges.base import BaseExchange
from app.exchanges.permissions import verify_trade_only
from app.exchanges.registry import build_exchange


@dataclass(frozen=True)
class Credentials:
    api_key: str
    secret: str


async def connect_account(
    db: AsyncSession,
    user_id: int,
    exchange: str,
    label: str,
    creds: Credentials,
) -> ExchangeAccount:
    """Verify the key is trade-only, then store it encrypted.

    Raises WithdrawalScopeError before anything is persisted if the key has
    withdrawal scope.
    """
    adapter = build_exchange(exchange, creds.api_key, creds.secret)
    try:
        await verify_trade_only(adapter)
    finally:
        await adapter.close()

    enc_key = encrypt_secret(creds.api_key)
    enc_secret = encrypt_secret(creds.secret)
    account = ExchangeAccount(
        user_id=user_id,
        exchange=exchange,
        label=label,
        encrypted_api_key_dek=enc_key.encrypted_dek,
        encrypted_api_key=enc_key.ciphertext,
        encrypted_secret_dek=enc_secret.encrypted_dek,
        encrypted_secret=enc_secret.ciphertext,
        permissions_verified=True,
        is_active=True,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def list_accounts(db: AsyncSession, user_id: int) -> list[ExchangeAccount]:
    result = await db.execute(select(ExchangeAccount).where(ExchangeAccount.user_id == user_id))
    return list(result.scalars().all())


async def get_account(db: AsyncSession, user_id: int, account_id: int) -> ExchangeAccount | None:
    account = await db.get(ExchangeAccount, account_id)
    if account is None or account.user_id != user_id:
        return None
    return account


def decrypt_credentials(account: ExchangeAccount) -> Credentials:
    return Credentials(
        api_key=decrypt_secret(account.encrypted_api_key_dek, account.encrypted_api_key),
        secret=decrypt_secret(account.encrypted_secret_dek, account.encrypted_secret),
    )


def build_adapter_for(account: ExchangeAccount) -> BaseExchange:
    creds = decrypt_credentials(account)
    return build_exchange(account.exchange, creds.api_key, creds.secret)
