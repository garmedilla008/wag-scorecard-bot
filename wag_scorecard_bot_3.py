"""
WAG Forex Scorecard Bot - Twelve Data Edition
"""

import requests
import schedule
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
BOT_TOKEN    = "8366999615:AAHYwtvRBfqu_fjy5enmirCWHME9Hwa0R0s"
CHAT_ID      = "-1003964887511"
TWELVEDATA_KEY = "5341e7faae4548bb9e1950b652d54e87"

POST_TIMES = ["00:00", "02:00", "04:00", "06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]

# ─────────────────────────────────────────────
# PAIRS
# ─────────────────────────────────────────────
CURRENCIES = ["AUD", "CAD", "EUR", "GBP", "JPY", "NZD", "USD"]

PAIRS = [
    ("AUD", "CAD"), ("AUD", "JPY"), ("AUD", "NZD"), ("AUD", "USD"),
    ("CAD", "JPY"), ("CAD", "NZD"), ("CAD", "USD"),
    ("EUR", "AUD"), ("EUR", "CAD"), ("EUR", "GBP"),
    ("EUR", "JPY"), ("EUR", "NZD"), ("EUR", "USD"),
    ("GBP", "AUD"), ("GBP", "CAD"), ("GBP", "JPY"),
    ("GBP", "NZD"), ("GBP", "USD"),
    ("NZD", "JPY"), ("NZD", "USD"),
    ("USD", "JPY"),
]

TIMEFRAMES = {
    "D1": {"interval": "1day",  "outputsize": 30},
    "H4": {"interval": "4h",    "outputsize": 30},
    "H1": {"interval": "1h",    "outputsize": 30},
}

SMA_PERIOD = 20

# ─────────────────────────────────────────────
# FETCH CANDLES FROM TWELVE DATA
# ─────────────────────────────────────────────
def fetch_candles(base, quote, interval, outputsize):
    symbol = f"{base}/{quote}"
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol":     symbol,
        "interval":   interval,
        "outputsize": outputsize,
        "apikey":     TWELVEDATA_KEY,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if "values" not in data:
            print(f"    API error for {symbol}: {data.get('message', 'unknown')}")
            return None
        values = data["values"]
        closes = [float(v["close"]) for v in reversed(values)]
        opens  = [float(v["open"])  for v in reversed(values)]
        return closes, opens
    except Exception as e:
        print(f"    Error fetching {symbol}: {e}")
        return None

# ─────────────────────────────────────────────
# CALCULATE SMA
# ─────────────────────────────────────────────
def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period

# ─────────────────────────────────────────────
# BIAS ENGINE
# ─────────────────────────────────────────────
def get_bias(base, quote, timeframe):
    cfg = TIMEFRAMES[timeframe]
    result = fetch_candles(base, quote, cfg["interval"], cfg["outputsize"])
    if result is None:
        return 0

    closes, opens = result
    if len(closes) < SMA_PERIOD + 1:
        return 0

    last_close = closes[-1]
    last_open  = opens[-1]
    last_sma   = sma(closes, SMA_PERIOD)

    if last_sma is None:
        return 0

    candle_up   = last_close > last_open
    candle_down = last_close < last_open
    above_sma   = last_close > last_sma
    below_sma   = last_close < last_sma

    if candle_up and above_sma:
        return 1
    elif candle_down and below_sma:
        return -1
    else:
        return 0

# ─────────────────────────────────────────────
# SCORE CALCULATOR
# ─────────────────────────────────────────────
def calculate_scores():
    scores = {c: {"D1": 0, "H4": 0, "H1": 0} for c in CURRENCIES}
    total = len(PAIRS) * 3
    done  = 0

    print(f"\nFetching data for {len(PAIRS)} pairs x 3 timeframes...\n")

    for base, quote in PAIRS:
        for tf in ["D1", "H4", "H1"]:
            done += 1
            print(f"  [{done}/{total}] {base}{quote} {tf}", end=" -> ")
            bias = get_bias(base, quote, tf)
            print({1: "Bullish", -1: "Bearish", 0: "Neutral"}[bias])

            # Add small delay to avoid rate limiting
            time.sleep(8)

            if base in scores:
                scores[base][tf] += bias
            if quote in scores:
                scores[quote][tf] -= bias

    return scores

# ─────────────────────────────────────────────
# MESSAGE FORMATTER
# ─────────────────────────────────────────────
def fmt(val):
    return f"+{val}" if val > 0 else str(val)

def build_message(scores):
    now = datetime.now().strftime("%Y.%m.%d %H:%M")
    lines = ["📊 Score Bias", f"Time: {now}", ""]
    for currency in CURRENCIES:
        tf = scores[currency]
        lines.append(currency)
        lines.append(f"D1: {fmt(tf['D1'])}  |  H4: {fmt(tf['H4'])}  |  H1: {fmt(tf['H1'])}")
        lines.append("")
    lines.append("Bias: +1 Bullish | 0 Neutral | -1 Bearish")
    return "\n".join(lines)

# ─────────────────────────────────────────────
# TELEGRAM SENDER
# ─────────────────────────────────────────────
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=60)
    if r.status_code == 200:
        print("\nScorecard posted to Telegram!")
    else:
        print(f"\nTelegram error {r.status_code}: {r.text}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def run_scorecard():
    print(f"\n{'='*50}")
    print(f"Running at {datetime.now().strftime('%H:%M')}")
    print(f"{'='*50}")
    scores  = calculate_scores()
    message = build_message(scores)
    print("\n" + message)
    send_to_telegram(message)

if __name__ == "__main__":
    print("WAG Forex Scorecard Bot started")
    run_scorecard()
    for t in POST_TIMES:
        schedule.every().day.at(t).do(run_scorecard)
    while True:
        schedule.run_pending()
        time.sleep(30)
