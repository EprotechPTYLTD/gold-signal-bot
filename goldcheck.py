"""
Cloud gold-signal bot — runs on GitHub Actions every 15 min.
Reads gold's hourly trend, pushes to the ntfy phone channel ONLY on a flip.
State (last signal) is committed back to the repo by the workflow.
"""
import json, urllib.request, os

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")   # injected from GitHub secret
STATE = ".last_signal"

def fetch(interval, rng):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval={interval}&range={rng}"
    last_err = None
    for _ in range(3):                          # retry transient network hiccups
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            res = json.load(urllib.request.urlopen(req, timeout=25))["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            return [q["close"][i] for i in range(len(res["timestamp"])) if q["close"][i] is not None]
        except Exception as e:
            last_err = e
    raise last_err

def ema(v, n):
    k = 2/(n+1); e = v[0]; out = []
    for x in v: e = x*k + e*(1-k); out.append(e)
    return out

def push_phone(title, msg):
    if not NTFY_TOPIC:
        print("WARNING: NTFY_TOPIC not set — skipping push"); return
    req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}",
        data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": "high", "Tags": "rotating_light"})
    urllib.request.urlopen(req, timeout=20)

closes = fetch("60m", "3mo")
e20, e50 = ema(closes, 20), ema(closes, 50)
gap = (e20[-1] - e50[-1]) / e50[-1] * 100
price = closes[-1]
sig = "WAIT" if abs(gap) < 0.10 else ("BUY" if gap > 0 else "SELL")

last = open(STATE).read().strip() if os.path.exists(STATE) else ""

if sig != last:
    if last == "":
        title, msg = f"GOLD: {sig}", f"Cloud bot is live. Signal is {sig}  (gold ${price:.0f})"
    else:
        title, msg = f"GOLD FLIP: {sig}", f"{last} changed to {sig}  (gold ${price:.0f})"
    push_phone(title, msg)
    open(STATE, "w").write(sig)
    print(f"CHANGED: {last or 'none'} -> {sig}  (${price:.2f})  [pushed to phone]")
else:
    print(f"no change: {sig}  (${price:.2f})")

# --- position-aware exit alert: ping to CLOSE if the trend turns against an open trade ---
POS = "position.json"
if os.path.exists(POS):
    try:
        pos = json.load(open(POS))
    except Exception:
        pos = {}
    d = pos.get("dir")
    if d and not pos.get("exit_alerted"):
        opposite = (d == "SELL" and sig == "BUY") or (d == "BUY" and sig == "SELL")
        if opposite:
            push_phone(f"CLOSE YOUR {d}",
                       f"Trend flipped to {sig}. Your {d} from {pos.get('entry')} is now against the trend - time to get out.")
            pos["exit_alerted"] = True
            json.dump(pos, open(POS, "w"))
            print(f"EXIT ALERT: close {d} (signal now {sig})")
        else:
            print(f"position {d} still aligned with signal {sig} - holding")
