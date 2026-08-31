"""Runs the audit and tiering tools on synthetic session data. `python examples/demo.py`

The synthetic universe is built with *no* real edge - every ticker's test quarter is drawn
from the same zero-mean distribution. The tiering rule should still produce a handful of
Tier A names, which is exactly the point being demonstrated.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit import (audit_sessions, audit_split_boundary,      # noqa: E402
                         audit_trade_ordering)
from tools.tiering import (TierRule, both_years_positive,           # noqa: E402
                           survival_report, tier_universe)

rng = np.random.default_rng(11)


def rule(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def session_bars(days: int, bars_per_day: int = 390, extra_premarket: int = 0) -> pd.DataFrame:
    frames = []
    for d in pd.bdate_range("2026-01-05", periods=days):
        start = d + pd.Timedelta("9h30min") - pd.Timedelta(minutes=extra_premarket)
        n = bars_per_day + extra_premarket
        frames.append(pd.DataFrame(
            {"close": 100 + np.cumsum(rng.normal(0, 0.02, n))},
            index=pd.date_range(start, periods=n, freq="1min")))
    return pd.concat(frames)


# ---------------------------------------------------------------- 1. session audit
rule("1. Session audit - clean sessions, then contaminated ones")

print(audit_sessions(session_bars(5)))

print()
print(audit_sessions(session_bars(5, extra_premarket=15)))

print()
full = session_bars(5)
last_day = full.index.normalize().max()
gap = full[~((full.index.normalize() == last_day) & (full.index.time > pd.Timestamp("15:41").time()))]
print(f"(last session truncated to {int((gap.index.normalize() == last_day).sum())} bars)")
print(audit_sessions(gap))

# ---------------------------------------------------------------- 2. trade ordering
rule("2. Trade ordering audit")

d = pd.Timestamp("2026-01-05")
good = pd.DataFrame({
    "signal_close_time": [d + pd.Timedelta("9h44min"), d + pd.Timedelta("9h39min")],
    "entry_open_time":   [d + pd.Timedelta("9h45min"), d + pd.Timedelta("9h40min")],
    "exit_time":         [d + pd.Timedelta("15h59min"), d + pd.Timedelta("15h59min")],
})
print(audit_trade_ordering(good))

bad = good.copy()
bad.loc[0, "signal_close_time"] = bad.loc[0, "entry_open_time"]        # same bar
bad.loc[1, "exit_time"] = d + pd.Timedelta("1D") + pd.Timedelta("15h59min")  # overnight
print()
print(audit_trade_ordering(bad))

# ---------------------------------------------------------------- 3. split boundary
rule("3. Split boundary audit - a 20-day lookback reaching into training")

idx = pd.bdate_range("2025-01-01", periods=365)
train, test = idx[:273], idx[273:]
print(audit_split_boundary(train, test, max_lookback="0D"))
print()
print(audit_split_boundary(train, test, max_lookback="20D"))

# ---------------------------------------------------------------- 4. tiering
rule("4. Tiering a universe with NO real edge")

n_tickers = 279
summary = pd.DataFrame({
    "ticker": [f"T{i:03d}" for i in range(n_tickers)],
    "error": [""] * n_tickers,
    "test_N": rng.integers(8, 60, n_tickers),
    "test_mean": rng.normal(0.0, 25.0, n_tickers),      # bps, zero-mean by construction
    "test_sharpe": rng.normal(0.0, 1.0, n_tickers),
    "test_max_dd": -np.abs(rng.normal(0.12, 0.06, n_tickers)),
}).set_index("ticker")
summary.loc[summary.index[:59], "error"] = "no_robust_candidate"   # training found nothing

tiered = tier_universe(summary, TierRule())
print(survival_report(tiered))

# ---------------------------------------------------------------- 5. two-year intersection
rule("5. Two independent years - survivors vs what independence predicts")

survivors = tiered.index[tiered["tier"] == "A"]
y1 = pd.Series(rng.normal(0.0, 20.0, len(survivors)), index=survivors)
y2 = pd.Series(rng.normal(0.0, 20.0, len(survivors)), index=survivors)
res = both_years_positive(y1, y2)
for k in ("n", "year1_positive", "year2_positive", "both_positive"):
    print(f"  {k:<24} {res[k]}")
print(f"  {'expected_if_independent':<24} {res['expected_if_independent']:.1f}")
print("\nWhen the observed intersection matches the independent prediction, single-year")
print("survival carried no information about the next year.")

print("\nDone.")
