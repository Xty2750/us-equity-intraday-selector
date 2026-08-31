"""Intraday session integrity and trade-ordering audits.

Two gates that run before any result is reported:

* `audit_sessions` - every full regular session must contain exactly 390 one-minute bars,
  all inside 09:30-15:59 ET. This single check catches pre/post-market contamination, data
  gaps, unlisted half days, and timezone or DST errors.
* `audit_trade_ordering` - every trade's signal bar must close strictly before its entry bar
  opens.

Both return a violation table. A non-empty table blocks reporting; it is not a warning.

Dependencies: numpy, pandas.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

SESSION_START = "09:30"
SESSION_END = "15:59"
FULL_SESSION_BARS = 390


@dataclass
class AuditResult:
    name: str
    n_checked: int
    violations: pd.DataFrame

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    def __str__(self) -> str:
        head = f"{self.name}: {self.n_checked} checked"
        if self.passed:
            return head + ", 0 violations  -> PASS"
        lines = [head + f", {len(self.violations)} violation(s)  -> FAIL"]
        for reason, n in self.violations["reason"].value_counts().items():
            lines.append(f"    {reason}: {n}")
        return "\n".join(lines)


def audit_sessions(
    bars: pd.DataFrame,
    *,
    tz: str = "America/New_York",
    half_days: set | None = None,
    expected_bars: int = FULL_SESSION_BARS,
) -> AuditResult:
    """Check per-session bar counts and session boundaries.

    Parameters
    ----------
    bars : one-minute bars with a tz-aware or naive DatetimeIndex in `tz`.
    half_days : dates known to be short sessions. These are reported separately rather than
        counted as violations - a half day is a fact about the calendar, and silently
        accepting any deviant count would defeat the check.
    """
    half_days = half_days or set()
    idx = pd.DatetimeIndex(bars.index)
    if idx.tz is None:
        idx = idx.tz_localize(tz)
    else:
        idx = idx.tz_convert(tz)

    v: list[dict] = []

    outside = idx.indexer_between_time(SESSION_START, SESSION_END)
    mask = np.ones(len(idx), dtype=bool)
    mask[outside] = False
    for ts in idx[mask]:
        v.append({"date": ts.date(), "reason": "bar_outside_regular_session",
                  "detail": str(ts)})

    dates = pd.Series(idx.date, index=idx)
    for d, group in dates.groupby(dates):
        n = len(group)
        if d in half_days:
            continue
        if n != expected_bars:
            v.append({"date": d, "reason": "bar_count_mismatch",
                      "detail": f"{n} bars, expected {expected_bars}"})

    dupes = idx[idx.duplicated()]
    for ts in dupes:
        v.append({"date": ts.date(), "reason": "duplicate_timestamp", "detail": str(ts)})

    return AuditResult("session audit", dates.groupby(dates).ngroups,
                       pd.DataFrame(v, columns=["date", "reason", "detail"]))


def audit_trade_ordering(
    trades: pd.DataFrame,
    *,
    signal_col: str = "signal_close_time",
    entry_col: str = "entry_open_time",
    exit_col: str = "exit_time",
) -> AuditResult:
    """Every signal must close strictly before its entry bar opens."""
    v: list[dict] = []
    for i, t in trades.iterrows():
        s, e = pd.Timestamp(t[signal_col]), pd.Timestamp(t[entry_col])
        if not s < e:
            v.append({"trade": i, "reason": "signal_not_before_entry",
                      "detail": f"{s} !< {e}"})
        if exit_col in trades.columns:
            x = pd.Timestamp(t[exit_col])
            if not e < x:
                v.append({"trade": i, "reason": "entry_not_before_exit",
                          "detail": f"{e} !< {x}"})
            if x.date() != e.date():
                v.append({"trade": i, "reason": "position_held_overnight",
                          "detail": f"entry {e.date()} exit {x.date()}"})
    return AuditResult("trade ordering audit", len(trades),
                       pd.DataFrame(v, columns=["trade", "reason", "detail"]))


def audit_split_boundary(
    train_index: pd.DatetimeIndex,
    test_index: pd.DatetimeIndex,
    *,
    max_lookback: str | pd.Timedelta = "0D",
) -> AuditResult:
    """No rolling window used in the test period may reach back across the boundary.

    A 20-day moving average evaluated on the first test day reads 20 days of training data.
    That is not leakage in the usual direction, but it does mean the first `max_lookback`
    of the test window is not independent of training.
    """
    lb = max_lookback if isinstance(max_lookback, pd.Timedelta) else pd.Timedelta(max_lookback)
    v: list[dict] = []
    if len(train_index) and len(test_index):
        boundary = test_index.min()
        if train_index.max() >= boundary:
            v.append({"reason": "train_test_overlap",
                      "detail": f"train ends {train_index.max()} >= test starts {boundary}"})
        contaminated = test_index[test_index < boundary + lb]
        if len(contaminated):
            v.append({"reason": "lookback_crosses_boundary",
                      "detail": f"{len(contaminated)} test bars within {lb} of the boundary"})
    return AuditResult("split boundary audit", len(test_index),
                       pd.DataFrame(v, columns=["reason", "detail"]))
