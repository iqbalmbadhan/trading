"""Exchange account management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import ExchangeAccount, User
from app.db.session import get_db
from app.exchanges import service
from app.exchanges.errors import ExchangeError, PermissionVerificationError

router = APIRouter(prefix="/api/v1/exchanges", tags=["exchanges"])


class ConnectRequest(BaseModel):
    exchange: str = Field(min_length=2, max_length=64)
    label: str = Field(min_length=1, max_length=120)
    api_key: str = Field(min_length=8)
    secret: str = Field(min_length=8)


class AccountOut(BaseModel):
    id: int
    exchange: str
    label: str
    permissions_verified: bool
    is_active: bool


def _to_out(a: ExchangeAccount) -> AccountOut:
    return AccountOut(
        id=a.id,
        exchange=a.exchange,
        label=a.label,
        permissions_verified=a.permissions_verified,
        is_active=a.is_active,
    )


@router.get("", response_model=list[AccountOut])
async def list_exchanges(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[AccountOut]:
    return [_to_out(a) for a in await service.list_accounts(db, user.id)]


@router.post("/connect", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def connect_exchange(
    payload: ConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountOut:
    try:
        account = await service.connect_account(
            db,
            user.id,
            payload.exchange,
            payload.label,
            service.Credentials(api_key=payload.api_key, secret=payload.secret),
        )
    except PermissionVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ExchangeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return _to_out(account)


@router.post("/{account_id}/test")
async def test_exchange(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    account = await service.get_account(db, user.id, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    adapter = service.build_adapter_for(account)
    try:
        balance = await adapter.fetch_balance()
    except ExchangeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    finally:
        await adapter.close()
    return {"ok": True, "balances": balance}


@router.post("/{account_id}/verify-permissions", response_model=AccountOut)
async def verify_permissions(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountOut:
    account = await service.get_account(db, user.id, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    adapter = service.build_adapter_for(account)
    try:
        from app.exchanges.permissions import verify_trade_only

        await verify_trade_only(adapter)
    except PermissionVerificationError as exc:
        account.permissions_verified = False
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        await adapter.close()
    account.permissions_verified = True
    await db.commit()
    await db.refresh(account)
    return _to_out(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_exchange(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    account = await service.get_account(db, user.id, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    await db.delete(account)
    await db.commit()
    return None
