from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from trading_system_agents.snapshot import DataSnapshot


ISO_DATE_PATTERN = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
NUMBER_PATTERN = re.compile(r"(?<![\w-])-?\d+(?:\.\d+)?(?![\w-])")


@dataclass(frozen=True)
class HallucinationWarning:
    kind: str
    value: str
    message: str


@dataclass(frozen=True)
class HallucinationValidationResult:
    warnings: list[HallucinationWarning]

    @property
    def is_degraded(self) -> bool:
        return bool(self.warnings)


def validate_agent_output(text: str, *, snapshot: DataSnapshot) -> HallucinationValidationResult:
    warnings: list[HallucinationWarning] = []
    warnings.extend(_unsupported_future_dates(text, snapshot))
    warnings.extend(_unsupported_numbers(text, snapshot))
    return HallucinationValidationResult(warnings=warnings)


def _unsupported_future_dates(text: str, snapshot: DataSnapshot) -> list[HallucinationWarning]:
    sourced_dates = snapshot.sourced_dates()
    analysis_date = date.fromisoformat(snapshot.analysis_date)
    warnings: list[HallucinationWarning] = []
    for value in sorted(set(ISO_DATE_PATTERN.findall(text))):
        event_date = date.fromisoformat(value)
        if event_date > analysis_date and value not in sourced_dates:
            warnings.append(
                HallucinationWarning(
                    kind="unsupported_future_date",
                    value=value,
                    message=f"Future event date {value} is not present in the data snapshot",
                )
            )
    return warnings


def _unsupported_numbers(text: str, snapshot: DataSnapshot) -> list[HallucinationWarning]:
    allowed = snapshot.numeric_values()
    warnings: list[HallucinationWarning] = []
    for value in sorted(set(NUMBER_PATTERN.findall(_remove_dates(text)))):
        number = float(value)
        if not _number_allowed(number, allowed):
            warnings.append(
                HallucinationWarning(
                    kind="unsupported_number",
                    value=value,
                    message=f"Number {value} is not present in the data snapshot",
                )
            )
    return warnings


def _remove_dates(text: str) -> str:
    return ISO_DATE_PATTERN.sub(" ", text)


def _number_allowed(number: float, allowed: set[float]) -> bool:
    return any(abs(number - item) < 0.0001 for item in allowed)

