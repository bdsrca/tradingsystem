from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True)
class KronosBatchItem:
    ticker: str
    exchange: str
    lookback_bars: int
    pred_len: int


def group_kronos_batch_jobs(
    jobs: list[KronosBatchItem],
) -> "OrderedDict[tuple[int, int], list[KronosBatchItem]]":
    grouped: OrderedDict[tuple[int, int], list[KronosBatchItem]] = OrderedDict()
    for job in jobs:
        key = (job.lookback_bars, job.pred_len)
        grouped.setdefault(key, []).append(job)
    return grouped


def validate_batch_compatible(jobs: list[KronosBatchItem]) -> None:
    if not jobs:
        return
    lookbacks = {job.lookback_bars for job in jobs}
    pred_lens = {job.pred_len for job in jobs}
    if len(lookbacks) != 1:
        raise ValueError(f"Kronos predict_batch requires the same lookback length, got {lookbacks}")
    if len(pred_lens) != 1:
        raise ValueError(f"Kronos predict_batch requires the same pred_len, got {pred_lens}")
