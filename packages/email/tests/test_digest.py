from datetime import datetime, timedelta, timezone

from trading_system_email.digest import (
    EmailDebouncePolicy,
    EmailDigest,
    EmailDigestItem,
    debounce_key,
    render_digest_text,
    should_send_signal_alert,
)


def test_render_digest_text_aggregates_daily_results() -> None:
    digest = EmailDigest(
        run_id="run-1",
        triggered_by="manual",
        started_at=datetime(2026, 6, 5, 21, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 6, 5, 21, 5, tzinfo=timezone.utc),
        succeeded_count=2,
        failed_count=1,
        skipped_count=1,
        stale_count=1,
        degraded_count=1,
        items=[
            EmailDigestItem(
                ticker="NTSK",
                exchange="NASDAQ",
                status="succeeded",
                signal="BUY",
                confidence=0.72,
                reason="trend confirmed",
            ),
            EmailDigestItem(
                ticker="MDA",
                exchange="NYSE",
                status="failed",
                error_message="No OHLCV bars found",
            ),
        ],
    )

    body = render_digest_text(digest)

    assert "Daily trading-system digest" in body
    assert "succeeded=2 failed=1 skipped=1 stale=1 degraded=1" in body
    assert "NTSK/NASDAQ BUY confidence=0.72" in body
    assert "trend confirmed" in body
    assert "MDA/NYSE failed: No OHLCV bars found" in body


def test_debounce_suppresses_same_ticker_signal_within_window() -> None:
    now = datetime(2026, 6, 5, 21, 0, tzinfo=timezone.utc)
    policy = EmailDebouncePolicy(window_days=7)

    assert not should_send_signal_alert(
        policy,
        last_sent_at=now - timedelta(days=3),
        now=now,
    )


def test_debounce_allows_missing_or_expired_previous_signal() -> None:
    now = datetime(2026, 6, 5, 21, 0, tzinfo=timezone.utc)
    policy = EmailDebouncePolicy(window_days=7)

    assert should_send_signal_alert(policy, last_sent_at=None, now=now)
    assert should_send_signal_alert(
        policy,
        last_sent_at=now - timedelta(days=8),
        now=now,
    )


def test_debounce_key_includes_ticker_exchange_and_signal_direction() -> None:
    assert debounce_key("mda", "nyse", "buy") == "MDA::NYSE::BUY"
