from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolIdentity:
    ticker: str
    exchange: str
    market: str


CANADIAN_SUFFIXES = {
    ".TO": "TSX",
    ".TRT": "TSX",
    ".V": "TSXV",
}


def normalize_symbol(raw_symbol: str) -> SymbolIdentity:
    symbol = raw_symbol.strip().upper()
    if not symbol:
        raise ValueError("Symbol cannot be blank")

    if ":" in symbol:
        ticker, exchange = symbol.split(":", 1)
        return _identity_from_exchange(ticker, exchange)

    for suffix, exchange in CANADIAN_SUFFIXES.items():
        if symbol.endswith(suffix):
            return SymbolIdentity(
                ticker=symbol[: -len(suffix)],
                exchange=exchange,
                market="CA",
            )

    return SymbolIdentity(ticker=symbol, exchange="NASDAQ", market="US")


def to_twelve_data_symbol(identity: SymbolIdentity) -> str:
    if identity.market == "CA":
        return f"{identity.ticker}:{identity.exchange}"
    return identity.ticker


def _identity_from_exchange(ticker: str, exchange: str) -> SymbolIdentity:
    cleaned_ticker = ticker.strip().upper()
    cleaned_exchange = exchange.strip().upper()
    if not cleaned_ticker or not cleaned_exchange:
        raise ValueError("Symbol and exchange must both be present")

    if cleaned_exchange in {"TSX", "TSXV"}:
        return SymbolIdentity(ticker=cleaned_ticker, exchange=cleaned_exchange, market="CA")

    return SymbolIdentity(ticker=cleaned_ticker, exchange=cleaned_exchange, market="US")

