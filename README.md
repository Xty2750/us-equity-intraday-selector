# US Equity Intraday Opening-Range Selector

A cross-sectional experiment on a question most intraday research answers by accident:

> If you optimize a simple intraday rule separately for every ticker in a large universe,
> how many of those optimized configurations actually survive out-of-sample?

**Answer, on 279 S&P 500 and Nasdaq-100 names: 25. Nine percent.**

The strategy is deliberately simple. The point of this repository is not the strategy — it
is the measurement of how badly per-ticker parameter selection overfits, and the protocol
built to make that measurement trustworthy.

---

## Design

**Universe.** 518 S&P 500 and Nasdaq-100 constituents, screened for coverage and liquidity.

**Data.** One-minute bars, regular session only — 09:30–15:59 ET, exactly 390 bars per full
session. 4.4 GB. Pre-market and after-hours bars are not merely filtered at use time; they
are never stored. A filter can be forgotten. A missing column cannot.

**Rule.** An opening benchmark bar sets a direction, an optional momentum filter gates the
entry, entry is at the next bar's open, an optional trailing stop manages the position, and
any remaining position exits at the close. At most one trade per ticker per day.

**Per-ticker parameters.** Benchmark bar length, direction (follow or fade), momentum filter
threshold, trailing stop multiple. Chosen independently for each ticker.

**Split.** A rolling 365-day window: the first 273 days (three quarters) are training, the
last 92 days (one quarter) are test. **The test quarter is touched exactly once, after every
parameter is frozen.**

## The leakage protocol

Intraday backtests leak through small holes, so the rules are written down and audited
rather than assumed. Full text in [docs/LEAKAGE_PROTOCOL.md](docs/LEAKAGE_PROTOCOL.md).

- Signals use only bars completed up to and including the benchmark bar.
- Entry uses the **next** bar's open; exits use bars strictly after entry.
- Same-day volume filters are permitted only when the statistic is knowable at signal time.
- The current day's close is never used before it occurs.
- Universe membership is fixed as of the start of each period — no survivorship.
- Corporate actions are applied at the correct ex-date, never retroactively.
- Short availability is evaluated from prior-day data only.

Two of these are audited mechanically on every trade, not reviewed by eye:

```
for every trade:   signal_close_time < entry_open_time
for every session: exactly 390 bars
```

Implemented in [`tools/audit.py`](tools/audit.py).

## Result

Every ticker with a candidate configuration was assigned a tier from its single-use test
quarter:

| Tier | Tickers | Share |
|---|---:|---:|
| A — survived | 25 | 9.0% |
| B — marginal | 28 | 10.0% |
| WATCH — inconclusive | 34 | 12.2% |
| REJECT — failed out-of-sample | 132 | 47.3% |
| NO_TRADE — no robust candidate in training | 59 | 21.1% |
| NO_TEST — insufficient test observations | 1 | 0.4% |
| **Total evaluated** | **279** | |

**132 rejected against 25 survivors.** Training-window performance was, for the large
majority of tickers, not informative about the next quarter.

That ratio *is* the finding. Search 279 tickers × a parameter grid each and a handful of
impressive-looking configurations is the guaranteed outcome, not evidence. Reporting only
the 25 survivors — the standard presentation — would have made a multiple-testing artifact
look like a stock-selection result.

## Second-year validation

The 25 survivors were then required to survive an **independent year of history** with the
same frozen procedure:

| Stage | Period | Used for |
|---|---|---|
| Base selection | 9 months | direction, benchmark length, filter, trailing stop |
| Base test | 3 months | single-use test |
| Filter-variant selection | earlier 12 months | per-ticker volatility filter |
| Filter-variant validation | following 12 months | single-use validation |
| **Forward validation** | subsequent data | **untouched** |

Across filter variants, the count of tickers positive in *both* independent years never
exceeded 7 of 25. Nine names cleared the full pipeline and were frozen for forward
validation, which is running and has not been read back into any selection step.

A candidate that fails forward validation is marked excluded. It is not re-fitted.

## What this repository does not contain

- Per-ticker frozen parameters and configuration files
- Trade-level logs and equity curves
- Raw or derived market data (licensing)
- The ticker list of the nine frozen names

The protocol, the audit tooling and the tier distribution are the transferable parts.

## Layout

```
docs/
  LEAKAGE_PROTOCOL.md    the rules, and which are machine-audited
  SELECTION_RESULTS.md   tier distribution, second-year narrowing, interpretation
tools/
  audit.py               session-completeness and signal-before-entry audits
  tiering.py             the single-use test-quarter tiering rule
examples/demo.py         both tools on synthetic session data
```

## License

MIT — see [LICENSE](LICENSE).
