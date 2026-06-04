from decimal import Decimal

from trading_system_data.twelve_data import parse_time_series


def test_parse_time_series_converts_strings_to_bars() -> None:
    payload = {
        "meta": {"symbol": "SHOP:TSX", "exchange": "TSX"},
        "values": [
            {
                "datetime": "2026-06-03",
                "open": "100.10",
                "high": "102.25",
                "low": "99.50",
                "close": "101.75",
                "volume": "1234567",
            }
        ],
    }

    bars = parse_time_series(payload)

    assert len(bars) == 1
    assert bars[0].bar_date.isoformat() == "2026-06-03"
    assert bars[0].open == Decimal("100.10")
    assert bars[0].volume == 1234567
    assert bars[0].source_symbol == "SHOP:TSX"

