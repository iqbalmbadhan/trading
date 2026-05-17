"""Strategy management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import Strategy, User
from app.db.session import get_db
from app.strategies import service
from app.strategies.registry import STRATEGIES

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


class StrategyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: str
    params: dict = Field(default_factory=dict)
    symbol: str = Field(min_length=1, max_length=64)
    timeframe: str = Field(default="1h")


class StrategyUpdate(BaseModel):
    name: str | None = None
    params: dict | None = None


class StrategyOut(BaseModel):
    id: int
    name: str
    type: str
    params: dict
    symbol: str
    timeframe: str
    is_paper: bool
    is_active: bool
    version: int


class RunOut(BaseModel):
    id: int
    strategy_id: int
    status: str


def _out(s: Strategy) -> StrategyOut:
    return StrategyOut(
        id=s.id,
        name=s.name,
        type=s.type,
        params=s.params,
        symbol=s.symbol,
        timeframe=s.timeframe,
        is_paper=s.is_paper,
        is_active=s.is_active,
        version=s.version,
    )


async def _require(strategy_id: int, user: User, db: AsyncSession) -> Strategy:
    s = await service.get_strategy(db, user.id, strategy_id)
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return s


@router.get("/templates")
async def templates(_: User = Depends(get_current_user)) -> list[dict]:
    out = []
    for name, klass in STRATEGIES.items():
        out.append(
            {
                "type": name,
                "default_params": klass.default_params().model_dump(),
                "param_ranges": klass.param_ranges,
                "required_timeframes": list(klass.required_timeframes),
                "required_indicators": list(klass.required_indicators),
            }
        )
    return out


@router.get("", response_model=list[StrategyOut])
async def list_strategies(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[StrategyOut]:
    return [_out(s) for s in await service.list_strategies(db, user.id)]


@router.post("", response_model=StrategyOut, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    payload: StrategyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StrategyOut:
    if payload.type not in STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown strategy type '{payload.type}'",
        )
    try:
        s = await service.create_strategy(
            db,
            user.id,
            name=payload.name,
            type=payload.type,
            params=payload.params,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
        )
    except service.StrategyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _out(s)


@router.get("/{strategy_id}", response_model=StrategyOut)
async def get_strategy(
    strategy_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StrategyOut:
    return _out(await _require(strategy_id, user, db))


@router.patch("/{strategy_id}", response_model=StrategyOut)
async def update_strategy(
    strategy_id: int,
    payload: StrategyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StrategyOut:
    s = await _require(strategy_id, user, db)
    try:
        s = await service.update_strategy(db, s, name=payload.name, params=payload.params)
    except service.StrategyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _out(s)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    s = await _require(strategy_id, user, db)
    try:
        await service.delete_strategy(db, s)
    except service.StrategyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return None


@router.post("/{strategy_id}/clone", response_model=StrategyOut, status_code=201)
async def clone_strategy(
    strategy_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StrategyOut:
    s = await _require(strategy_id, user, db)
    return _out(await service.clone_strategy(db, s))


@router.post("/{strategy_id}/start", response_model=RunOut)
async def start_strategy(
    strategy_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunOut:
    s = await _require(strategy_id, user, db)
    try:
        run = await service.start_strategy(db, s)
    except service.StrategyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return RunOut(id=run.id, strategy_id=run.strategy_id, status=run.status)


@router.post("/{strategy_id}/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_strategy(
    strategy_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    s = await _require(strategy_id, user, db)
    await service.stop_strategy(db, s)
    return None
