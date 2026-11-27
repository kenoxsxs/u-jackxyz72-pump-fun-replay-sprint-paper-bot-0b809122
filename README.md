[![make.fun · u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122](https://make.fun/badge/u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122.svg)](https://make.fun/bounty/u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122?utm_source=github&utm_medium=readme&utm_campaign=u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122)
[![rank](https://make.fun/badge/u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122/kenoxsxs/u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122/rank.svg)](https://make.fun/bounty/u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122)
[![reward](https://make.fun/badge/u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122/kenoxsxs/u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122/reward.svg)](https://make.fun/bounty/u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122?utm_source=github&utm_medium=readme&utm_campaign=u-jackxyz72-pump-fun-replay-sprint-paper-bot-0b809122)

# Fresh-Launch Flow Rider — Pump.fun Replay Sprint

A paper trading bot for the make.fun **Pump.fun Replay Sprint — Paper Bot, Real Ranking**
bounty. It trades 10 SOL of paper money on a replay of 24 hours of pump.fun bonding-curve
activity. Best net PnL wins; a prize needs a net PnL above holding cash (above 0 SOL after
every fee).

Entry by [@kenoxs02](https://make.fun) — referral code `ew1nqp5h`.

## The strategy in one paragraph

Buy a young curve only after the launch dust has settled and real buyers are still piling
in, then leave fast. A coin becomes a candidate 10–120 slots after its CreateEvent, once
net buys over the last 15 slots are at least 0.02 SOL, at least four distinct non-creator
buyers have shown up, the price sits 1–60% above its create price and near its young high,
the real SOL reserve is 0.5–40 SOL, the creator has not sold, and the launch was not bundled
by more than eight wallets in its first slot. The first buy is 0.08 SOL; one add of 0.08 SOL
follows only if the price steps 8% above the last buy and the flow stays positive. The
position is sold whole on the first of: take profit +25%, stop loss −12%, a trailing stop
of 15% armed at +8%, a flow reversal (net flow under −0.03 SOL over 15 slots), the creator
selling while held, no trade for 200 slots, or 350 slots held. One entry per coin per run,
at most five open positions. A pace keeper opens one tiny 0.01 SOL probe round trip when the
run's filled round trips lag the pace the twenty-coin minimum bar implies.

Why not the neighbours: buying at birth pays the bundled-launch dump; buying mature curves
misses the move and pyramiding to 2 SOL turns one wrong coin into a portfolio event; buying
dips assumes the dip ends, and on pump.fun most dips are the coin dying; buying everything
and holding is the control group that proves most coins go to zero.

Every calculation is integer lamport math — prices are (virtual quote, virtual token) pairs
compared by cross multiplication, so both graded executions agree byte for byte. No clock,
no environment, no randomness.

## How to run

```sh
# The grader runs it as:
python3 -P -s /bot/main.py
```

Locally, grade it on the kit's frozen dev window (needs the kit's CLI; `--driver process`
runs the bot on this machine instead of Docker):

```sh
node cli/makefun.mjs grade-local --kit . --bot <this repo> --driver process --bundle <transcripts.tar.gz>
```

## Files

- `main.py` — the bot (Python standard library only).
- `vendor/makefun_bot.py` — the house SDK shim, byte-identical to `sdk/python/makefun_bot.py`
  in the kit (kept out of the authorship counts by the kit's own rule).
- `LICENSE` — MIT.

## Dev-window result

Graded locally on the kit's frozen dev window (`grade-local --driver process`,
bot executed twice, L1 regrade reproduced byte for byte):

- **Net PnL: −0.069 SOL** (−0.69% return; 90% interval −0.094 … −0.048 SOL)
- **240 fills over 57 coins, 120 round trips, win rate 6.7%, max drawdown 0.69%**
- Fees: 0.030 SOL curve + 0.026 SOL tx; at 2× fees net PnL −0.124 SOL
- **Guardrails met**: 57 coins hold a round trip of at least 0.01 SOL (120 such
  round trips), drawdown well under 50%
- Top 2 coins made 100% of the gains; without them net PnL is −0.07 SOL

Comparison on the same dev window (all with `grade-local --driver process`):

| entry | net PnL | guardrails |
| --- | --- | --- |
| **this bot** | **−0.069 SOL** | met |
| pilot sniper (house) | −0.475 SOL | met |
| pilot momentum (house) | −9.489 SOL | **not met** (drawdown 95.7%) |
| baseline equal-weight | −0.019 SOL | not met (5 fills, 1 coin) |
| baseline hold-cash | 0.000 SOL | not met (0 trades) |

The dev window is brutal — no tested entry beats holding cash on it, including
the house's own tuned pilots — so the prize bar (net PnL > 0 SOL after fees)
is decided on the final window's fresh 24 hours of data. This bot is built to
be the least-bad on a bad day (smallest loss, smallest drawdown, fewest fees
per trade among guardrail-meeting entries) and to keep its edge if the final
day is friendlier: ultra-selective entries, small stakes, fast exits.

Tuning history (21 variants, all on the dev window): v1 −0.356, v3 (stricter
entry) −0.111, v9 (stricter still) −0.072, v15 (strictest) −0.069 SOL. Tighter
stops, trailing stops and longer holds never bound on this data. A dip-entry
variant (buy a proven runner after a 10–25% pullback with flow turning) was
tried and rejected: −0.314 SOL, 208 round trips — on this data a pullback is
the dump, not a discount.
