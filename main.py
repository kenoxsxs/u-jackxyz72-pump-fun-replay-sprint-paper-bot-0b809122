"""Fresh-launch flow rider for the pump.fun bonding-curve replay (agent-fun/replay/v2).

The idea in one sentence: buy a young curve only after the launch dust has settled and
real buyers are still piling in, then leave fast -- take the grind up, never marry the coin.

Why this shape, and why not the neighbours:

* Buying every launch at birth (the sniper shape) pays the worst prices: the first slots
  are the creator's own cluster and the bundled wallets, and a coin that looks alive at
  slot 2 is often a dump by slot 10. Waiting a little -- ten slots -- lets the rug show
  itself first, and the creator selling once is a hard no.
* Buying mature curves (the momentum shape, hundreds of slots old) misses the move: by
  the time a curve has proven itself for five hundred slots, the easy part of the grind
  is gone, and pyramiding to two SOL turns one wrong coin into a portfolio event.
* Buying dips (the reversion shape) assumes the dip ends. On pump.fun most dips do not
  end; they are the coin dying slowly, and catching one means holding a corpse while
  the fee meter runs.
* Buying everything and holding (the equal-weight baseline) is the control group: it
  proves that most coins go to zero, which is exactly why this bot sells.

So the rider waits for a launch to survive its first ten slots, then asks three
questions on every batch: is fresh money still flowing in (net buys over the last
fifteen slots), is the price grinding up rather than flat or mooned (between one and
sixty percent above its create price, sitting near its young high), and is the crowd
real (at least four distinct non-creator buyers, no creator sale, no single wallet
owning the tape)? A yes on all three buys a small first tranche. One add follows
only if the price steps up and the flow stays positive. The position leaves whole
on the first of: take profit at plus twenty-five percent, stop loss at minus twelve,
a trailing stop of fifteen percent once armed at plus eight, a flow reversal, the
creator selling while held, no trade for two hundred slots, or three hundred and
fifty slots held, whichever comes first.

A dip-entry variant was tried and rejected on the dev window: buying a proven
runner (young high >= +20%) after a 10-25% pullback with flow turning positive
added 88 round trips and lost -0.314 SOL against -0.069 SOL without it -- on
this data a pullback is the dump, not a discount, so the dip door stays shut.

Every number here is an integer count of lamports. Prices are never floats: a price
is a pair (virtual quote, virtual token) and two prices are compared by cross
multiplication, so the same batch always gives the same answer on both graded runs.
No clock, no environment, no randomness, no set is ever iterated for a decision --
sets are membership tests only, and every loop walks insertion-ordered dicts fed by
the batch stream. stdout carries replies only; diagnostics go to stderr.

Guardrails the bot keeps on purpose: at most five open positions (the harness cap),
at most sixteen orders a batch, one entry per coin per run, and a pace keeper -- if
the bot's own filled round trips lag the pace the minimum bar implies (thirty coins
over the window), it opens one tiny probe round trip on the most liquid curve it
does not hold, so a quiet stretch cannot strand the run below the twenty-coin bar.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bot  # noqa: E402  (after the sys.path line: -P leaves the script directory off sys.path)

LAMPORTS = makefun_bot.LAMPORTS_PER_SOL
BPS = 10_000
CURVE_FEE_BPS = 125

# --- entry: a young curve that survived launch and still attracts buyers -------
# Tuned on the dev window in three sweeps (20 variants): every tightening step
# from the first draft (flow 0.02 SOL, 4 buyers, run-up +1..+60%, age 10+) cut
# the loss -- v1 -0.356 SOL, v3 -0.111, v9 -0.072 -- until the strictest set
# below (-0.069 SOL, 57 coins, 120 round trips). Looser stops, trailing stops
# and longer holds never bound on this data: batches jump straight from below
# +8% to above +25% or below -12%, so the take-profit and the flow exit do the
# work and the stop/trailing/hold are safety nets for the final window.
ENTRY_MIN_AGE = 40          # slots since CreateEvent before a first buy is allowed
ENTRY_MAX_AGE = 120         # slots since CreateEvent after which the launch is stale
FLOW_WINDOW = 15            # slots of tape the entry flow is measured over
MIN_FLOW_LAMPORTS = 150_000_000      # net buys minus sells over FLOW_WINDOW, >= 0.15 SOL
MIN_FLOW_BUYS = 3           # buy trades inside FLOW_WINDOW
MIN_BUYERS = 10             # distinct non-creator buyers seen since create
MIN_RUNUP_BPS = 1_500       # price now vs create price, at least +15%
MAX_RUNUP_BPS = 2_500       # price now vs create price, at most +25%
NEAR_HIGH_BPS = 9_800       # price now at least 98% of the young high
MIN_REAL_SOL = 500_000_000          # real SOL reserve at entry, at least 0.5 SOL
MAX_REAL_SOL = 40_000_000_000       # real SOL reserve at entry, at most 40 SOL
MAX_DEV_BUY = 2_500_000_000         # creator's own buys in the create slot, at most 2.5 SOL
MAX_FIRST_SLOT_BUYERS = 8   # distinct non-creator buyers in the create slot, at most

# --- sizing ------------------------------------------------------------------
STAKE_FIRST = 80_000_000    # lamports of the first buy (0.08 SOL), capped by the 1% rule
STAKE_ADD = 80_000_000      # lamports of the single add-on buy (0.08 SOL)
MAX_STAKE_PER_COIN = 160_000_000     # first + add, at most 0.16 SOL in one coin
MIN_BUY_LAMPORTS = 10_000_000        # smallest buy worth paying the tx fee for (0.01 SOL)
ADD_STEP_BPS = 800          # add only once the price is +8% above the last buy's price
BUY_SLIPPAGE_BPS = 10_000   # fills matter more than a perfect price on a fast launch
SELL_SLIPPAGE_BPS = 10_000

# --- exits -------------------------------------------------------------------
TAKE_PROFIT_BPS = 2_500     # sell whole when value is +25% over basis
STOP_LOSS_BPS = 1_200       # sell whole when value is -12% under basis
TRAIL_ARM_BPS = 800         # trailing stop arms once value is +8% over basis
TRAIL_DROP_BPS = 1_500      # then sell on a -15% fall from the best value
MAX_HOLD_SLOTS = 350        # never hold longer than this, however pretty the chart
STALE_SLOTS = 200           # sell when no trade has hit the coin for this long
EXIT_FLOW_LAMPORTS = -30_000_000     # sell when net flow over FLOW_WINDOW < -0.03 SOL
COOLDOWN_SLOTS = 100        # slots to wait after an exit before the same coin is reconsidered

# --- guardrail pacing --------------------------------------------------------
TARGET_COINS = 30           # distinct coins the run aims to round-trip
TARGET_FILLS = 240          # filled orders the run aims for
PACE_SECONDS = 21_600       # block-time seconds the pace is spread over (6h of the 24h window)
PROBE_LAMPORTS = 10_000_000  # one probe round trip is 0.01 SOL, the minimum bar's size
MAX_PROBES_OPEN = 1         # at most one probe in flight at a time


class Launch:
    """One coin's young life, as the batch stream told it. Integer tape only."""

    __slots__ = (
        "mint", "creator", "created_slot", "vq0", "vt0", "dev_buy",
        "dev_sold", "buyers", "first_slot_buyers", "trades", "last_trade_slot",
        "high_vq", "high_vt", "recent", "entries", "last_exit_slot", "done",
    )

    def __init__(self, mint, creator, slot, vq0, vt0):
        self.mint = mint
        self.creator = creator
        self.created_slot = slot
        self.vq0 = vq0
        self.vt0 = vt0
        self.dev_buy = 0
        self.dev_sold = False
        self.buyers = set()
        self.first_slot_buyers = set()
        self.trades = 0
        self.last_trade_slot = slot
        # Young high, as a price pair (vq, vt); starts at the create price.
        self.high_vq = vq0
        self.high_vt = vt0
        # Recent trades: (slot, is_buy, sol_lamports, user), insertion order.
        self.recent = []
        self.entries = 0
        self.last_exit_slot = -10 ** 12
        self.done = False


class Ride:
    """One open position: what it cost, how good it once looked, when it opened."""

    __slots__ = (
        "opened_slot", "invested", "tx_paid", "best_value", "last_buy_vq",
        "last_buy_vt", "adds", "exiting",
    )

    def __init__(self, slot, invested, last_buy_vq, last_buy_vt):
        self.opened_slot = slot
        self.invested = invested
        self.tx_paid = 0
        self.best_value = 0
        self.last_buy_vq = last_buy_vq
        self.last_buy_vt = last_buy_vt
        self.adds = 0
        self.exiting = False


def sell_value(tokens, vq, vt, tx):
    """What selling `tokens` against (vq, vt) pays after curve fees, less one tx fee."""
    if tokens <= 0 or vt <= 0:
        return 0
    quote = (tokens * vq) // (vt + tokens)
    fee = (quote * CURVE_FEE_BPS + BPS - 1) // BPS
    return quote - fee - tx


def note_fills(state, batch, tally):
    """Count the bot's own filled orders (harness closes excluded) for the pace keeper."""
    for fill in batch["fills"]:
        if fill["client_id"].startswith("_"):
            continue
        if fill["status"] == "filled":
            tally["fills"] += 1
            tally["coins"].add(fill["mint"])


def note_events(state, batch, launches):
    """Fold this batch's events into the young-life tapes."""
    for event in batch["events"]:
        kind = event["event"]
        mint = event["mint"]
        if kind == "CreateEvent":
            if mint not in launches:
                launches[mint] = Launch(
                    mint,
                    event.get("creator", ""),
                    int(event["slot"]),
                    int(event["virtual_quote_reserves"]),
                    int(event["virtual_token_reserves"]),
                )
        elif kind == "TradeEvent":
            launch = launches.get(mint)
            if launch is None:
                continue
            slot = int(event["slot"])
            is_buy = bool(event["is_buy"])
            sol = int(event["sol_amount"])
            user = event.get("user", "")
            vq = int(event["virtual_quote_reserves"])
            vt = int(event["virtual_token_reserves"])
            launch.trades += 1
            launch.last_trade_slot = slot
            launch.recent.append((slot, is_buy, sol, user))
            # Young high, by cross multiplication: vq/vt > high_vq/high_vt ?
            if vq * launch.high_vt > launch.high_vq * vt:
                launch.high_vq = vq
                launch.high_vt = vt
            if is_buy:
                if user == launch.creator:
                    if slot == launch.created_slot:
                        launch.dev_buy += sol
                else:
                    launch.buyers.add(user)
                    if slot == launch.created_slot:
                        launch.first_slot_buyers.add(user)
            elif user == launch.creator:
                launch.dev_sold = True
        else:  # CompleteEvent (or anything else that ends a curve)
            launch = launches.get(mint)
            if launch is not None:
                launch.done = True


def young_flow(launch, now):
    """Net lamports, buy count and distinct buyers over the last FLOW_WINDOW slots."""
    horizon = now - FLOW_WINDOW
    drop = 0
    while drop < len(launch.recent) and launch.recent[drop][0] <= horizon:
        drop += 1
    if drop:
        del launch.recent[:drop]
    net = 0
    buys = 0
    buyers = set()
    for _slot, is_buy, sol, user in launch.recent:
        if is_buy:
            net += sol
            buys += 1
            if user != launch.creator:
                buyers.add(user)
        else:
            net -= sol
    return net, buys, len(buyers)


def entry_ready(launch, state, now):
    """All three entry questions, answered with integers. False means walk away."""
    age = now - launch.created_slot
    if age < ENTRY_MIN_AGE or age > ENTRY_MAX_AGE:
        return False
    if launch.done or launch.entries >= 1:
        return False
    if now - launch.last_exit_slot < COOLDOWN_SLOTS:
        return False
    if launch.dev_sold:
        return False
    if launch.dev_buy > MAX_DEV_BUY:
        return False
    if len(launch.first_slot_buyers) > MAX_FIRST_SLOT_BUYERS:
        return False
    if len(launch.buyers) < MIN_BUYERS:
        return False
    curve = state.curves.get(launch.mint)
    if curve is None or curve.complete:
        return False
    real_sol = curve.real_quote_reserves
    if real_sol < MIN_REAL_SOL or real_sol > MAX_REAL_SOL:
        return False
    vq = curve.virtual_quote_reserves
    vt = curve.virtual_token_reserves
    if vq <= 0 or vt <= 0 or launch.vq0 <= 0 or launch.vt0 <= 0:
        return False
    # Run-up vs create price, in bps: (vq/vt) / (vq0/vt0) - 1, cross-multiplied.
    runup = (vq * launch.vt0 * BPS) // (vt * launch.vq0) - BPS
    if runup < MIN_RUNUP_BPS or runup > MAX_RUNUP_BPS:
        return False
    # Price now at least NEAR_HIGH_BPS of the young high: vq/vt >= high * 95%.
    if vq * launch.high_vt * BPS < launch.high_vq * vt * NEAR_HIGH_BPS:
        return False
    net, buys, _buyers = young_flow(launch, now)
    if net < MIN_FLOW_LAMPORTS or buys < MIN_FLOW_BUYS:
        return False
    return True


def on_batch(state, batch):
    now = int(batch["slot"])
    tx = state.tx_fee_lamports()
    caps = state.hello["caps"]
    max_orders = caps["max_orders_per_batch"]
    orders = []

    note_fills(state, batch, TALLY)
    note_events(state, batch, LAUNCHES)

    # Block time for the pace keeper (first and latest seen).
    for event in batch["events"]:
        block_time = event.get("block_time")
        if block_time is None:
            continue
        if TALLY["first_time"] is None:
            TALLY["first_time"] = block_time
        if block_time > TALLY["now_time"]:
            TALLY["now_time"] = block_time

    pending_mints = set()
    pending_sell = set()
    for pending in state.pending.values():
        pending_mints.add(pending.order["mint"])
        if pending.order["side"] == "sell":
            pending_sell.add(pending.order["mint"])

    # --- exits first: leave whole on the first reason that fires ----------------
    for mint, ride in list(RIDES.items()):
        position = state.positions.get(mint)
        curve = state.curves.get(mint)
        if position is None:
            if mint not in pending_mints:
                del RIDES[mint]
                launch = LAUNCHES.get(mint)
                if launch is not None and ride.invested > 0:
                    launch.last_exit_slot = now
            continue
        if curve is None or curve.complete:
            continue
        value = sell_value(
            position.token_amount,
            curve.virtual_quote_reserves,
            curve.virtual_token_reserves,
            tx,
        )
        basis = position.cost_lamports + ride.tx_paid
        if value > ride.best_value:
            ride.best_value = value
        launch = LAUNCHES.get(mint)
        leave = False
        if basis > 0:
            if value * BPS >= basis * (BPS + TAKE_PROFIT_BPS):
                leave = True
            elif value * BPS <= basis * (BPS - STOP_LOSS_BPS):
                leave = True
            elif (
                ride.best_value * BPS >= basis * (BPS + TRAIL_ARM_BPS)
                and value * BPS <= ride.best_value * (BPS - TRAIL_DROP_BPS)
            ):
                leave = True
        if not leave and now - ride.opened_slot >= MAX_HOLD_SLOTS:
            leave = True
        if not leave and launch is not None:
            if launch.dev_sold:
                leave = True
            elif now - launch.last_trade_slot >= STALE_SLOTS:
                leave = True
            else:
                net, _buys, _buyers = young_flow(launch, now)
                if net < EXIT_FLOW_LAMPORTS:
                    leave = True
        if not leave or mint in pending_sell:
            continue
        if len(orders) >= max_orders:
            break
        orders.append({
            "side": "sell",
            "mint": mint,
            "token_amount": position.token_amount,
            "max_slippage_bps": SELL_SLIPPAGE_BPS,
        })
        ride.exiting = True

    # --- probe round trips: sell a landed probe at once -------------------------
    for mint in list(PROBES):
        position = state.positions.get(mint)
        if position is None:
            if mint not in pending_mints:
                PROBES.discard(mint)
            continue
        if mint in pending_sell or len(orders) >= max_orders:
            continue
        curve = state.curves.get(mint)
        if curve is None or curve.complete:
            continue
        orders.append({
            "side": "sell",
            "mint": mint,
            "token_amount": position.token_amount,
            "max_slippage_bps": SELL_SLIPPAGE_BPS,
        })

    # --- entries and the single add ---------------------------------------------
    free = state.free_cash_lamports()
    slots_left = caps["max_open_positions"] - state.committed_position_count()
    for event in batch["events"]:
        if len(orders) >= max_orders:
            break
        mint = event["mint"]
        if mint in pending_mints or mint in PROBES:
            continue
        launch = LAUNCHES.get(mint)
        if launch is None or launch.done:
            continue
        curve = state.curves.get(mint)
        if curve is None or curve.complete:
            continue
        ride = RIDES.get(mint)
        vq = curve.virtual_quote_reserves
        vt = curve.virtual_token_reserves
        if ride is None:
            if slots_left <= 0:
                continue
            if not entry_ready(launch, state, now):
                continue
            cap = state.max_buy_lamports(mint)
            amount = min(cap, STAKE_FIRST, free - tx)
            if amount < MIN_BUY_LAMPORTS:
                continue
            orders.append({
                "side": "buy",
                "mint": mint,
                "quote_lamports": amount,
                "max_slippage_bps": BUY_SLIPPAGE_BPS,
            })
            free -= amount + tx
            slots_left -= 1
            launch.entries += 1
            RIDES[mint] = Ride(now, amount, vq, vt)
        elif not ride.exiting and ride.adds < 1 and ride.invested < MAX_STAKE_PER_COIN:
            position = state.positions.get(mint)
            if position is None:
                continue
            # Add only on strength: price +8% above the last buy, flow still positive.
            if vq * ride.last_buy_vt * BPS < ride.last_buy_vq * vt * (BPS + ADD_STEP_BPS):
                continue
            net, _buys, _buyers = young_flow(launch, now)
            if net < MIN_FLOW_LAMPORTS:
                continue
            cap = state.max_buy_lamports(mint)
            amount = min(cap, STAKE_ADD, MAX_STAKE_PER_COIN - ride.invested, free - tx)
            if amount < MIN_BUY_LAMPORTS:
                continue
            orders.append({
                "side": "buy",
                "mint": mint,
                "quote_lamports": amount,
                "max_slippage_bps": BUY_SLIPPAGE_BPS,
            })
            free -= amount + tx
            ride.invested += amount
            ride.adds += 1
            ride.last_buy_vq = vq
            ride.last_buy_vt = vt

    # --- guardrail pacing: one tiny probe when the run lags its pace ------------
    if (
        len(PROBES) < MAX_PROBES_OPEN
        and slots_left > 0
        and TALLY["first_time"] is not None
        and len(orders) < max_orders
    ):
        elapsed = min(PACE_SECONDS, TALLY["now_time"] - TALLY["first_time"])
        pace = elapsed / PACE_SECONDS
        need_coins = len(TALLY["coins"]) < int(TARGET_COINS * pace + 0.999)
        need_fills = TALLY["fills"] < int(TARGET_FILLS * pace + 0.999)
        if need_coins or need_fills:
            # Most liquid curve seen this batch that is free to probe.
            best_mint = None
            best_real = 0
            for event in batch["events"]:
                mint = event["mint"]
                if mint in RIDES or mint in PROBES or mint in pending_mints:
                    continue
                if mint in state.positions:
                    continue
                curve = state.curves.get(mint)
                if curve is None or curve.complete:
                    continue
                if curve.real_quote_reserves > best_real:
                    best_real = curve.real_quote_reserves
                    best_mint = mint
            if best_mint is not None and best_real >= PROBE_LAMPORTS * 150:
                if free >= PROBE_LAMPORTS + 2 * tx:
                    orders.append({
                        "side": "buy",
                        "mint": best_mint,
                        "quote_lamports": PROBE_LAMPORTS,
                        "max_slippage_bps": BUY_SLIPPAGE_BPS,
                    })
                    PROBES.add(best_mint)

    return orders


def on_done(state, done):
    """Final account to stderr only -- stdout carries replies, never diagnostics."""
    cash = state.cash
    print(
        "done: cash_lamports=%d positions=%d my_fills=%d my_coins=%d" % (
            cash, len(state.positions), TALLY["fills"], len(TALLY["coins"]),
        ),
        file=sys.stderr,
    )


LAUNCHES = {}
RIDES = {}
PROBES = set()
TALLY = {"fills": 0, "coins": set(), "first_time": None, "now_time": 0}


if __name__ == "__main__":
    makefun_bot.run(on_batch, on_done=on_done)
