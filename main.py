"""btc-race-24h bot: selective dip-buyer on cbBTC 1-minute bars.

Strategy (long only, one position, full size): buy the sharp, oversold dip
and sell the bounce; sit in cash the rest of the day.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
LOOKBACK = 50          # bars for the drop that marks the dip
DROP_BPS = 100         # the close must be this far below LOOKBACK bars ago
RSI_BARS = 14
RSI_MAX = 30           # oversold
TAKE_BPS = 100         # take profit, from the entry close
STOP_BPS = 50          # stop loss, from the entry close
MAX_SLIPPAGE_BPS = 500

closes = []
_changes = []  # last RSI_BARS closes-to-close changes
_entry_close = 0


def _rsi():
    """RSI(14) as a plain average of the last 14 changes: mean gain over
    (mean gain + mean loss), 50 when nothing moved."""
    if len(_changes) < RSI_BARS:
        return None
    gain = sum(x for x in _changes if x > 0) / RSI_BARS
    loss = sum(-x for x in _changes if x < 0) / RSI_BARS
    moved = gain + loss
    return 50.0 if moved == 0 else 100.0 * gain / moved


def _push(close):
    if closes:
        _changes.append(close - closes[-1])
        if len(_changes) > RSI_BARS:
            _changes.pop(0)
    closes.append(close)


def on_batch(state, batch):
    global _entry_close
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            _push(int(bar["c"]))
    if len(closes) < LOOKBACK + 1:
        return []
    held = state.positions.get(SYMBOL)
    close = closes[-1]
    if held is not None:
        if close * 10000 >= _entry_close * (10000 + TAKE_BPS):
            _entry_close = 0
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        if close * 10000 <= _entry_close * (10000 - STOP_BPS):
            _entry_close = 0
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    rsi = _rsi()
    if (rsi is not None and rsi < RSI_MAX
            and closes[-1] * 10000 < closes[-1 - LOOKBACK] * (10000 - DROP_BPS)
            and closes[-1] > closes[-2] and closes[-2] > closes[-3]):
        _entry_close = close
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": state.cash,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
