# Train/Test and Leakage Protocol

Written before the experiment, applied without exception. Rules that can be checked by a
machine are checked by a machine.

---

## Fixed split

- Rolling 365-day period.
- First 273 days (three quarters) = **TRAIN**.
- Last 92 days (one quarter) = **TEST**.
- Test data is used exactly once, after all decisions are frozen.

## What may happen during training

Everything that involves a choice:

- Universe membership screening
- Liquidity screening
- Parameter grid search
- Strategy ranking
- Portfolio weighting
- Cost and short-borrow assumption calibration

## What happens after freezing

1. Freeze a JSON config per selected ticker.
2. Run one pass over the test quarter.
3. Write results.
4. **No parameter changes after seeing test results.**

Point 4 is the entire protocol. Everything else is bookkeeping in support of it. A test set
looked at twice is a validation set, and a validation set optimized against is a training
set.

## Per-bar rules

1. Signals use only completed bars, up to and including the benchmark bar.
2. Entry uses the **next** bar's open.
3. Exits use bars strictly after entry.
4. Same-day volume filters are allowed only if the required statistic is knowable at signal
   time.
5. The current day's close is never used before it occurs.
6. No pre-market or after-hours bars are stored or used.
7. Corporate actions are applied at the correct ex-date, never retroactively for earlier
   signals.
8. Short availability is evaluated before entry, from prior-day or otherwise known data.

Rule 6 is enforced at the storage layer rather than at use time. Storing only regular-session
bars makes the error unrepresentable; filtering at use time makes it a thing you have to
remember in every script.

## Machine-audited checks

| Check | Rule |
|---|---|
| `signal_close_time < entry_open_time` on every trade | 1, 2 |
| exactly 390 bars on every full session | 6 |
| no bar timestamp outside 09:30–15:59 ET | 6 |
| universe membership as-of date vs trade date | survivorship |
| no rolling window spans the train/test boundary | split integrity |

Implemented in [`tools/audit.py`](../tools/audit.py). These run as a gate, not a review:
a non-empty violation table blocks reporting.

## Why 390

A full US equity regular session is 09:30–15:59 inclusive at one-minute resolution: 390
bars. Any full session with a different count means one of

- pre/post-market contamination (usually more),
- a data gap (fewer),
- a half day, which must be listed explicitly rather than silently accepted,
- a timezone or DST handling error.

It is the cheapest single integrity check available on intraday equity data, and it catches
all four.

## Cost and borrow assumptions

Costs are calibrated on training data and held fixed through the test pass. Short trades
carry a borrow-cost model and are only permitted where borrow availability was known before
entry. Long and short cost formulas are written separately — folding direction into a sign
multiplier inverts the short-side cost.

## Forward validation

After the frozen candidates pass both independent years, they enter forward validation on
data that has participated in no selection step. Rules:

- No parameter or filter changes once forward validation starts.
- Results are appended to a running log; checkpoints at 20, 40 and 60 completed trades.
- A candidate that fails is marked **excluded**, not re-fitted.

That last rule is the one that costs something. It is also the only thing that makes the
forward result mean anything.
