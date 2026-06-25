"""
Cloud gold-signal bot (GitHub Actions, every 15 min).
Pushes your phone ONLY when the hourly trend CONFIRMS a full conversion
(SELL -> BUY or BUY -> SELL), held CONFIRM_N consecutive checks to filter whipsaw.
"""
import json, urllib.request, os

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
STATE = "trend_state.json"
CONFIRM_N = 2            # consecutive 15-min checks in the new direction before it counts as "confirmed"

def fetch(interval, rng):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval={interval}&range={rng}"
    err = None
    for _ in range(3):                          # retry transient network errors
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            res = json.load(urllib.request.urlopen(req, timeout=25))["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            return [q["close"][i] for i in range(len(res["timestamp"])) if q["close"][i] is not None]
        except Exception as e:
            err = e
    raise err

def ema(v, n):
    k = 2/(n+1); e = v[0]; out = []
    for x in v: e = x*k + e*(1-k); out.append(e)
    return out

def push_phone(title, msg):
    if not NTFY_TOPIC:
        print("WARNING: NTFY_TOPIC not set"); return
    req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}",
        data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": "high", "Tags": "rotating_light"})
    urllib.request.urlopen(req, timeout=20)

# --- current raw hourly trend ---
closes = fetch("60m", "3mo")
e20, e50 = ema(closes, 20), ema(closes, 50)
gap = (e20[-1] - e50[-1]) / e50[-1] * 100
price = closes[-1]
raw = "WAIT" if abs(gap) < 0.10 else ("BUY" if gap > 0 else "SELL")

# --- confirmed-conversion state machine ---
if os.path.exists(STATE):
    st = json.load(open(STATE))
else:
    # seed with the current direction (no alert on first run)
    st = {"confirmed": raw if raw in ("BUY", "SELL") else "SELL", "cand": None, "streak": 0}

confirmed = st["confirmed"]
alerted = False

if raw == "WAIT" or raw == confirmed:
    st["cand"], st["streak"] = None, 0          # nothing building toward a flip
else:
    # raw is the OPPOSITE direction — building confirmation
    st["streak"] = st["streak"] + 1 if raw == st.get("cand") else 1
    st["cand"] = raw
    if st["streak"] >= CONFIRM_N:
        if raw == "BUY":          # ONLY ping the SELL -> BUY reversal up. Nothing else.
            push_phone("GOLD REVERSAL: SELL -> BUY",
                       f"Confirmed reversal up - the downtrend has flipped to BUY "
                       f"(held {CONFIRM_N} checks). Gold ${price:.0f}.")
            alerted = True
        st["confirmed"], st["cand"], st["streak"] = raw, None, 0   # BUY->SELL updates silently

json.dump(st, open(STATE, "w"))
print(f"raw={raw}  confirmed={st['confirmed']}  building={st['cand']}  streak={st['streak']}  "
      f"price={price:.2f}  alerted={alerted}")
