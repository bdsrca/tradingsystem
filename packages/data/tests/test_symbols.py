import pytest

from trading_system_data.symbols import normalize_symbol, to_twelve_data_symbol


@pytest.mark.parametrize(
    ("raw", "ticker", "exchange", "market"),
    [
        ("AAPL", "AAPL", "NASDAQ", "US"),
        ("SHOP.TO", "SHOP", "TSX", "CA"),
        ("RY.TO", "RY", "TSX", "CA"),
        ("SHOP.TRT", "SHOP", "TSX", "CA"),
        ("RY:TSX", "RY", "TSX", "CA"),
        ("BTE.V", "BTE", "TSXV", "CA"),
    ],
)
def test_normalize_symbol(raw: str, ticker: str, exchange: str, market: str) -> None:
    identity = normalize_symbol(raw)

    assert identity.ticker == ticker
    assert identity.exchange == exchange
    assert identity.market == market


def test_to_twelve_data_symbol_maps_canadian_exchanges() -> None:
    assert to_twelve_data_symbol(normalize_symbol("SHOP.TO")) == "SHOP:TSX"
    assert to_twelve_data_symbol(normalize_symbol("BTE.V")) == "BTE:TSXV"


def test_to_twelve_data_symbol_includes_non_nasdaq_us_exchange() -> None:
    assert to_twelve_data_symbol(normalize_symbol("MDA:NYSE")) == "MDA:NYSE"


def test_normalize_symbol_rejects_blank_input() -> None:
    with pytest.raises(ValueError):
        normalize_symbol(" ")
