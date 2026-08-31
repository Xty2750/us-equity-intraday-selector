"""Single-use test-quarter tiering.

The rule that turns one test pass into a verdict per ticker. Two properties matter more
than the thresholds:

* **It can return nothing.** `NO_TRADE` exists so the training step can say "there is no
  robust candidate here." A procedure that always produces a candidate cannot express
  absence, and will manufacture one for all 279 tickers.
* **It is applied once.** Re-running it after adjusting a threshold makes the test quarter a
  validation set.

Dependencies: numpy, pandas.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TierRule:
    min_test_trades: int = 10
    a_min_mean_bps: float = 5.0
    a_min_sharpe: float = 0.30
    a_max_drawdown: float = 0.25
    b_min_mean_bps: float = 0.0
    watch_band_bps: float = 15.0


def assign_tier(row: pd.Series, rule: TierRule = TierRule()) -> str:
    """Assign one ticker's tier from its frozen-config test-quarter statistics.

    Expected fields: test_N, test_mean (bps), test_sharpe, test_max_dd (negative fraction),
    and optionally `error` set when training found no robust candidate.
    """
    if str(row.get("error", "") or "").strip():
        return "NO_TRADE"

    n = row.get("test_N", 0)
    if not np.isfinite(n) or n == 0:
        return "NO_TEST"
    if n < rule.min_test_trades:
        return "NO_TEST"

    mean = float(row["test_mean"])
    sharpe = float(row["test_sharpe"])
    dd = abs(float(row["test_max_dd"]))

    if mean >= rule.a_min_mean_bps and sharpe >= rule.a_min_sharpe and dd <= rule.a_max_drawdown:
        return "A"
    if mean > rule.b_min_mean_bps:
        return "B"
    if abs(mean) <= rule.watch_band_bps:
        return "WATCH"
    return "REJECT"


def tier_universe(summary: pd.DataFrame, rule: TierRule = TierRule()) -> pd.DataFrame:
    out = summary.copy()
    out["tier"] = out.apply(assign_tier, axis=1, rule=rule)
    return out


def survival_report(tiered: pd.DataFrame) -> str:
    """The denominator, stated first.

    Reporting the survivors without the population is how a multiple-testing artifact gets
    presented as a stock-selection result.
    """
    counts = tiered["tier"].value_counts()
    total = len(tiered)
    order = ["A", "B", "WATCH", "REJECT", "NO_TRADE", "NO_TEST"]
    lines = [f"{total} tickers evaluated"]
    for t in order:
        n = int(counts.get(t, 0))
        if n:
            lines.append(f"  {t:<9} {n:>4}  {n / total:6.1%}")
    a = int(counts.get("A", 0))
    rej = int(counts.get("REJECT", 0))
    lines.append(f"\nsurvival rate: {a}/{total} = {a / total:.1%}"
                 f"   (rejected: {rej})")
    if a and rej > a:
        lines.append("note: rejections outnumber survivors - treat the survivor list as a "
                     "multiple-testing artifact until it clears an independent period.")
    return "\n".join(lines)


def both_years_positive(year1: pd.Series, year2: pd.Series) -> dict:
    """Intersection of two independent years, with the honest comparison alongside it.

    Each Series maps ticker -> mean return for that year. The number that matters is not
    how many were positive in each year, but how many were the *same* tickers - and how
    that compares to what independence alone would produce.
    """
    common = year1.index.intersection(year2.index)
    y1, y2 = year1.loc[common], year2.loc[common]
    p1, p2 = y1 > 0, y2 > 0
    both = p1 & p2
    n = len(common)
    expected_if_independent = float(p1.mean() * p2.mean() * n) if n else float("nan")
    return {
        "n": n,
        "year1_positive": int(p1.sum()),
        "year2_positive": int(p2.sum()),
        "both_positive": int(both.sum()),
        "expected_if_independent": expected_if_independent,
        "tickers": sorted(common[both].tolist()),
    }
