from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.database import get_session
from trading_system_api.models import WatchlistItem
from trading_system_api.schemas import WatchlistCreate, WatchlistRead, WatchlistUpdate
from trading_system_data.symbols import normalize_symbol, to_twelve_data_symbol

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistRead])
async def list_watchlist(session: AsyncSession = Depends(get_session)) -> list[WatchlistItem]:
    result = await session.execute(select(WatchlistItem).order_by(WatchlistItem.created_at.asc()))
    return list(result.scalars().all())


@router.post("", response_model=WatchlistRead, status_code=status.HTTP_201_CREATED)
async def create_watchlist_item(
    payload: WatchlistCreate,
    session: AsyncSession = Depends(get_session),
) -> WatchlistItem:
    identity = normalize_symbol(payload.symbol)
    item = WatchlistItem(
        ticker=identity.ticker,
        exchange=identity.exchange,
        market=identity.market,
        provider_symbol=to_twelve_data_symbol(identity),
        display_name=payload.display_name,
        enabled=payload.enabled,
        tags=payload.tags,
        alert_enabled=payload.alert_enabled,
        alert_threshold=payload.alert_threshold,
        data_stale_after_hours=payload.data_stale_after_hours,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/{item_id}", response_model=WatchlistRead)
async def get_watchlist_item(
    item_id: str,
    session: AsyncSession = Depends(get_session),
) -> WatchlistItem:
    return await _get_item_or_404(item_id, session)


@router.patch("/{item_id}", response_model=WatchlistRead)
async def update_watchlist_item(
    item_id: str,
    payload: WatchlistUpdate,
    session: AsyncSession = Depends(get_session),
) -> WatchlistItem:
    item = await _get_item_or_404(item_id, session)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(item, key, value)
    item.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist_item(
    item_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    item = await _get_item_or_404(item_id, session)
    await session.delete(item)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _get_item_or_404(item_id: str, session: AsyncSession) -> WatchlistItem:
    item = await session.get(WatchlistItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found")
    return item

