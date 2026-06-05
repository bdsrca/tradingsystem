from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SymbolIdentity:
    ticker: str
    exchange: str
    market: str


@dataclass(frozen=True)
class SymbolSearchCandidate:
    symbol: str
    exchange: str
    country: str | None = None


CANADIAN_SUFFIXES = {
    ".TO": "TSX",
    ".TRT": "TSX",
    ".V": "TSXV",
}

CANADIAN_EXCHANGES = {"TSX", "TSXV", "NEO", "CSE"}
US_EXCHANGE_PRIORITY = ("NASDAQ", "NYSE", "AMEX", "NYSE ARCA", "NYSE MKT", "BATS", "OTC")


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
    if identity.market == "CA" or identity.exchange != "NASDAQ":
        return f"{identity.ticker}:{identity.exchange}"
    return identity.ticker


def symbol_has_explicit_exchange(raw_symbol: str) -> bool:
    symbol = raw_symbol.strip().upper()
    if ":" in symbol:
        return True
    return any(symbol.endswith(suffix) for suffix in CANADIAN_SUFFIXES)


def resolve_bare_symbol_from_candidates(
    raw_symbol: str,
    candidates: Iterable[object],
    *,
    fallback: SymbolIdentity | None = None,
) -> SymbolIdentity:
    identity = normalize_symbol(raw_symbol)
    if symbol_has_explicit_exchange(raw_symbol):
        return identity

    exact_matches = [
        candidate
        for candidate in candidates
        if _candidate_value(candidate, "symbol").upper() == identity.ticker
        and _candidate_value(candidate, "exchange")
    ]

    us_match = _pick_us_match(exact_matches)
    if us_match is not None:
        return _identity_from_exchange(
            _candidate_value(us_match, "symbol"),
            _candidate_value(us_match, "exchange"),
        )

    ca_match = next(
        (
            candidate
            for candidate in exact_matches
            if _candidate_value(candidate, "country").upper() == "CANADA"
        ),
        None,
    )
    if ca_match is not None:
        return _identity_from_exchange(
            _candidate_value(ca_match, "symbol"),
            _candidate_value(ca_match, "exchange"),
        )

    return fallback or identity


def _identity_from_exchange(ticker: str, exchange: str) -> SymbolIdentity:
    cleaned_ticker = ticker.strip().upper()
    cleaned_exchange = exchange.strip().upper()
    if not cleaned_ticker or not cleaned_exchange:
        raise ValueError("Symbol and exchange must both be present")

    if cleaned_exchange in CANADIAN_EXCHANGES:
        return SymbolIdentity(ticker=cleaned_ticker, exchange=cleaned_exchange, market="CA")

    return SymbolIdentity(ticker=cleaned_ticker, exchange=cleaned_exchange, market="US")


def _pick_us_match(candidates: list[object]) -> object | None:
    us_candidates = [
        candidate
        for candidate in candidates
        if _candidate_value(candidate, "country").upper() in {"UNITED STATES", "US", "USA"}
    ]
    if not us_candidates:
        return None

    for exchange in US_EXCHANGE_PRIORITY:
        for candidate in us_candidates:
            if _candidate_value(candidate, "exchange").upper() == exchange:
                return candidate
    return us_candidates[0]


def _candidate_value(candidate: object, field_name: str) -> str:
    if isinstance(candidate, dict):
        value = candidate.get(field_name)
    else:
        value = getattr(candidate, field_name, None)
    return str(value or "").strip()
