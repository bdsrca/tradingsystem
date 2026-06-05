from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trading_system_agents.snapshot import DataSnapshot


class RuntimePathError(RuntimeError):
    pass


@dataclass(frozen=True)
class TradingAgentsRuntimeDirs:
    run_dir: Path
    data_cache_dir: Path
    results_dir: Path

    def config_values(self) -> dict[str, str]:
        return {
            "data_cache_dir": str(self.data_cache_dir),
            "results_dir": str(self.results_dir),
        }


@contextmanager
def patch_resolve_instrument_identity(
    agent_utils_module: Any,
    snapshot: DataSnapshot,
    *,
    graph_module: Any | None = None,
) -> Iterator[None]:
    """Replace TradingAgents' yfinance-backed identity resolver for one run."""

    agent_original = agent_utils_module.resolve_instrument_identity
    graph_original = None
    if graph_module is not None and hasattr(graph_module, "resolve_instrument_identity"):
        graph_original = graph_module.resolve_instrument_identity

    for resolver in _unique_callables(agent_original, graph_original):
        cache_clear = getattr(resolver, "cache_clear", None)
        if callable(cache_clear):
            cache_clear()

    replacement = _identity_resolver(snapshot)
    agent_utils_module.resolve_instrument_identity = replacement
    if graph_module is not None and graph_original is not None:
        graph_module.resolve_instrument_identity = replacement

    try:
        yield
    finally:
        agent_utils_module.resolve_instrument_identity = agent_original
        if graph_module is not None and graph_original is not None:
            graph_module.resolve_instrument_identity = graph_original


@contextmanager
def disable_pending_entry_resolution(graph: Any) -> Iterator[None]:
    """Disable TradingAgents pending-memory return resolution during an agent run."""

    original = graph._resolve_pending_entries
    graph._resolve_pending_entries = lambda *_args, **_kwargs: None
    try:
        yield
    finally:
        graph._resolve_pending_entries = original


def prepare_isolated_runtime_dirs(base_dir: str | Path, *, run_id: str) -> TradingAgentsRuntimeDirs:
    """Create fresh TradingAgents runtime dirs so stale memory logs cannot be reused."""

    if not run_id or not run_id.strip():
        raise RuntimePathError("run_id must not be empty")

    base_path = Path(base_dir).resolve()
    run_dir = (base_path / run_id).resolve()
    if not _is_relative_to(run_dir, base_path):
        raise RuntimePathError(f"run_id escapes runtime base directory: {run_id}")
    if run_dir.exists():
        raise RuntimePathError(f"TradingAgents runtime directory already exists: {run_dir}")

    data_cache_dir = run_dir / "data_cache"
    results_dir = run_dir / "results"
    data_cache_dir.mkdir(parents=True, exist_ok=False)
    results_dir.mkdir(parents=False, exist_ok=False)
    return TradingAgentsRuntimeDirs(
        run_dir=run_dir,
        data_cache_dir=data_cache_dir,
        results_dir=results_dir,
    )


def _identity_resolver(snapshot: DataSnapshot) -> Callable[[str], dict[str, Any]]:
    def resolve(_ticker: str) -> dict[str, Any]:
        name = snapshot.display_name or snapshot.ticker
        return {
            "company_name": name,
            "name": name,
            "ticker": snapshot.ticker,
            "exchange": snapshot.exchange,
            "sector": snapshot.fundamentals.get("sector"),
            "industry": snapshot.fundamentals.get("industry"),
            "business_summary": snapshot.fundamentals.get("business_summary"),
        }

    return resolve


def _unique_callables(*values: Callable[..., Any] | None) -> list[Callable[..., Any]]:
    seen: set[int] = set()
    result = []
    for value in values:
        if value is None:
            continue
        identity = id(value)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(value)
    return result


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
