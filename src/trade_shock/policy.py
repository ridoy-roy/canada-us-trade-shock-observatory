"""Section 232 steel policy history and monthly treatment assignment."""

from __future__ import annotations

import calendar
from datetime import date


MARCH_EFFECTIVE = date(2025, 3, 12)
JUNE_EFFECTIVE = date(2025, 6, 4)


def rate_on(day: date) -> float:
    if day < MARCH_EFFECTIVE:
        return 0.0
    if day < JUNE_EFFECTIVE:
        return 0.25
    return 0.50


def monthly_policy(year: int, month: int) -> dict[str, object]:
    """Return start/end and day-weighted policy rates for a calendar month.

    The weighted rate is descriptive only. Transition months are explicitly
    excluded from clean full-month treatment comparisons.
    """
    days = calendar.monthrange(year, month)[1]
    daily_rates = [rate_on(date(year, month, day)) for day in range(1, days + 1)]
    start_rate, end_rate = daily_rates[0], daily_rates[-1]
    transition = start_rate != end_rate
    if transition and (year, month) == (2025, 3):
        regime = "transition_0_to_25"
    elif transition and (year, month) == (2025, 6):
        regime = "transition_25_to_50"
    elif end_rate == 0:
        regime = "no_section232_tariff"
    elif end_rate == 0.25:
        regime = "25_percent"
    else:
        regime = "50_percent"
    return {
        "section232_rate_month_start": start_rate,
        "section232_rate_month_end": end_rate,
        "section232_rate_day_weighted": sum(daily_rates) / days,
        "section232_rate_clean_month": None if transition else start_rate,
        "policy_regime": regime,
        "is_transition_month": transition,
        "include_clean_month_analysis": not transition,
    }

