# Selection Results

What happens when a simple intraday rule is optimized per ticker across a large universe,
and then tested once.

---

## Tier distribution

279 tickers evaluated. Tier assigned from the single-use 92-day test quarter.

| Tier | Definition | Count | Share |
|---|---|---:|---:|
| A | positive test-quarter mean and Sharpe, drawdown within tolerance | 25 | 9.0% |
| B | positive but marginal on at least one criterion | 28 | 10.0% |
| WATCH | near zero — neither confirmed nor rejected | 34 | 12.2% |
| REJECT | negative test quarter | 132 | 47.3% |
| NO_TRADE | no robust candidate found in training | 59 | 21.1% |
| NO_TEST | too few test-quarter observations to judge | 1 | 0.4% |

## Reading the table

**Training performance was not informative.** Every one of the 220 tickers that produced a
candidate had an attractive training window — that is what "candidate" means. One quarter
later, 132 were negative and 25 were clearly positive.

**A 9% survival rate is what a null result looks like** when you search hard enough. With
279 tickers and a parameter grid each, the search space is large enough that some
configurations will look good on 273 days of data by chance alone. The survivors are not
obviously distinguishable from that.

**The 59 NO_TRADE tickers are a feature.** The selection step is allowed to return nothing.
A procedure that always produces a candidate has no way to express "there is nothing here,"
and will therefore manufacture one.

**Reporting only the 25 would have been the standard presentation** — a list of names with
attractive out-of-sample statistics, one per ticker, each individually defensible. It would
also have been a multiple-testing artifact dressed as a stock-selection result. The
denominator is the finding.

## Second-year narrowing

The survivors were required to hold up across an independent year, using the same frozen
procedure on a completely separate period. Across roughly a dozen filter variants
(fixed threshold, and dynamic volatility moving-average filters at several lookbacks), the
count positive in **both** independent years:

| Filter variant | Year 1 positive | Year 2 positive | Both |
|---|---:|---:|---:|
| dynamic open-MA, long lookback | 21 | 27 | 7 |
| combined, long lookback | 21 | 26 | 7 |
| dynamic open-MA, medium lookback | 23 | 26 | 6 |
| fixed threshold | 14 | 23 | 6 |
| dynamic overall-MA, long lookback | 21 | 25 | 6 |
| *(remaining variants)* | 17–24 | 20–28 | 4–5 |

**No variant exceeded 7 of 25.** Roughly 20–27 tickers were positive in each year
individually, and only a quarter of those were the same tickers.

That gap is the cleanest number in the project. Single-year survival is roughly what you
would expect from a coin-weighting exercise; two-year survival is close to the intersection
of two independent random draws from the same pool.

Note also that the best variant by "both years" is not the best by either year alone —
selecting a filter variant on its two-year intersection is itself a selection step, which
is why the winner was frozen and pushed to forward validation rather than reported as a
result.

## Frozen set

Nine tickers cleared the full pipeline and were frozen for forward validation on data that
has participated in no selection step. Two additional names that had performed well in the
original single-year pass were **excluded** from the clean set for procedural reasons — one
lacked Year 1 history, the other produced no positive robust Year 1 filter candidate —
rather than being waived through on their headline numbers.

Forward validation is running. Checkpoints at 20, 40 and 60 completed trades. A candidate
that fails is marked excluded, not re-fitted.

## What would change the conclusion

An honest statement of what would make this look different:

- **A larger effective sample.** One year of one-minute data per ticker is roughly 250
  independent daily decisions. That is not many to fit four parameters against.
- **A mechanism.** These parameters were selected, not derived. A rule with an economic
  reason to work — a known flow, a structural constraint — would deserve a different prior
  than a grid search.
- **Forward validation results.** The nine frozen names are the only part of this that can
  still produce evidence, precisely because nothing about them has been tuned since.

Until then the honest summary is: per-ticker intraday parameter optimization on this
universe did not generalize, and the 9% survival rate is the measurement of that.
