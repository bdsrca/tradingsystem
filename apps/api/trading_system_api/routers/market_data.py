from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.config import Settings, get_settings
from trading_system_api.database import get_session
from trading_system_api.models import MarketDataBar
from trading_system_api.schemas import MarketDataBarRead, MarketDataRefreshResult
from trading_system_data.symbols import normalize_symbol
from trading_system_data.twelve_data import TwelveDataClient

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/{ticker}/bars", response_model=list[MarketDataBarRead])
async def list_bars(
    ticker: str,
    exchange: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[MarketDataBarRead]:
    statement: Select[tuple[MarketDataBar]] = select(MarketDataBar).where(
        MarketDataBar.ticker == ticker.upper()
    )
    if exchange:
        statement = statement.where(MarketDataBar.exchange == exchange.upper())
    statement = statement.order_by(MarketDataBar.bar_date.asc())

    rows = (await session.execute(statement)).scalars().all()
    return [
        MarketDataBarRead(
            time=row.bar_date.isoformat(),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=row.volume,
        )
        for row in rows
    ]


def get_twelve_data_client(settings: Settings = Depends(get_settings)) -> TwelveDataClient:
    if not settings.twelve_data_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TWELVE_DATA_API_KEY is not configured",
        )
    return TwelveDataClient(settings.twelve_data_api_key)


@router.post("/{symbol}/refresh", response_model=MarketDataRefreshResult)
async def refresh_daily_bars(
    symbol: str,
    exchange: str | None = None,
    outputsize: int = Query(500, ge=1, le=5000),
    session: AsyncSession = Depends(get_session),
    client: TwelveDataClient = Depends(get_twelve_data_client),
) -> MarketDataRefreshResult:
    identity = normalize_symbol(_symbol_with_optional_exchange(symbol, exchange))
    bars = await client.fetch_daily_bars(identity, outputsize=outputsize)

    for bar in bars:
        statement = select(MarketDataBar).where(
            MarketDataBar.ticker == identity.ticker,
            MarketDataBar.exchange == identity.exchange,
            MarketDataBar.bar_date == bar.bar_date,
            MarketDataBar.source_provider == bar.source_provider,
        )
        existing = (await session.execute(statement)).scalar_one_or_none()
        if existing is None:
            session.add(
                MarketDataBar(
                    ticker=identity.ticker,
                    exchange=identity.exchange,
                    bar_date=bar.bar_date,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    source_provider=bar.source_provider,
                    source_symbol=bar.source_symbol,
                    fetched_at=bar.fetched_at,
                    adjustment_mode=bar.adjustment_mode,
                )
            )
        else:
            existing.open = bar.open
            existing.high = bar.high
            existing.low = bar.low
            existing.close = bar.close
            existing.volume = bar.volume
            existing.source_symbol = bar.source_symbol
            existing.fetched_at = bar.fetched_at
            existing.adjustment_mode = bar.adjustment_mode

    await session.commit()

    latest_bar_date = max((bar.bar_date for bar in bars), default=None)
    source_symbol = bars[0].source_symbol if bars else identity.ticker
    return MarketDataRefreshResult(
        ticker=identity.ticker,
        exchange=identity.exchange,
        source_provider="twelve_data",
        source_symbol=source_symbol,
        bars_upserted=len(bars),
        latest_bar_date=latest_bar_date.isoformat() if latest_bar_date else None,
    )


def _symbol_with_optional_exchange(symbol: str, exchange: str | None) -> str:
    if exchange and ":" not in symbol and "." not in symbol:
        return f"{symbol}:{exchange}"
    return symbol
