from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class EmailDigestItem:
    ticker: str
    exchange: str
    status: str
    signal: str | None = None
    confidence: float | None = None
    reason: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class EmailDigest:
    run_id: str
    triggered_by: str
    started_at: datetime
    finished_at: datetime | None
    succeeded_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    stale_count: int = 0
    degraded_count: int = 0
    items: list[EmailDigestItem] = field(default_factory=list)


@dataclass(frozen=True)
class EmailDebouncePolicy:
    window_days: int = 7


def debounce_key(ticker: str, exchange: str, signal: str) -> str:
    return f"{ticker.strip().upper()}::{exchange.strip().upper()}::{signal.strip().upper()}"


def should_send_signal_alert(
    policy: EmailDebouncePolicy,
    *,
    last_sent_at: datetime | None,
    now: datetime,
) -> bool:
    if last_sent_at is None:
        return True
    if last_sent_at.tzinfo is None:
        last_sent_at = last_sent_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - last_sent_at).days >= policy.window_days


def render_digest_text(digest: EmailDigest) -> str:
    finished = digest.finished_at.isoformat() if digest.finished_at else "running"
    lines = [
        "Daily trading-system digest",
        f"run_id={digest.run_id}",
        f"triggered_by={digest.triggered_by}",
        f"started_at={digest.started_at.isoformat()}",
        f"finished_at={finished}",
        (
            "counts: "
            f"succeeded={digest.succeeded_count} "
            f"failed={digest.failed_count} "
            f"skipped={digest.skipped_count} "
            f"stale={digest.stale_count} "
            f"degraded={digest.degraded_count}"
        ),
        "",
        "Results:",
    ]

    if not digest.items:
        lines.append("- No ticker results.")
        return "\n".join(lines)

    for item in digest.items:
        lines.append(_render_item(item))
    return "\n".join(lines)


def _render_item(item: EmailDigestItem) -> str:
    label = f"{item.ticker.upper()}/{item.exchange.upper()}"
    if item.status == "succeeded" and item.signal:
        confidence = f"{item.confidence:.2f}" if item.confidence is not None else "n/a"
        suffix = f" - {item.reason}" if item.reason else ""
        return f"- {label} {item.signal.upper()} confidence={confidence}{suffix}"
    if item.error_message:
        return f"- {label} {item.status}: {item.error_message}"
    return f"- {label} {item.status}"
