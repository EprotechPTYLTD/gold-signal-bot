# gold-signal-bot

Always-on gold (XAU) trend signal. Runs on GitHub Actions every 15 minutes — no
laptop required — and pushes a phone notification **only when the hourly trend flips**
(BUY ⇄ SELL ⇄ WAIT).

- `goldcheck.py` — fetches gold, computes the hourly EMA20/EMA50 trend, pushes to ntfy on a flip
- `.github/workflows/gold.yml` — the 15-min scheduler + commits the signal state back
- `.last_signal` — the current state (auto-managed)

Phone alerts go to an ntfy channel stored as the repo secret `NTFY_TOPIC`.
Subscribe in the **ntfy** app to receive them.

Not financial advice — a trend gauge to avoid trading against the trend.
