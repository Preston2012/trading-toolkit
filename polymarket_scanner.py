#!/usr/bin/env python3
import requests, json, time, os, schedule

TG_TOKEN = "REDACTED_TG_TOKEN"
TG_CHAT = "REDACTED_TG_CHAT"

def send_tg(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"})

def scan_polymarket():
    try:
        url = "https://gamma-api.polymarket.com/events?closed=false&limit=50"
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return
        events = r.json()
        keywords = ["iran", "ceasefire", "oil", "crude", "hormuz", "war", "trump"]
        state_file = "/root/data/poly_state.json"
        prev = {}
        if os.path.exists(state_file):
            with open(state_file) as f:
                prev = json.load(f)
        for ev in events:
            title = ev.get("title", "")
            if not any(kw in title.lower() for kw in keywords):
                continue
            slug = ev.get("slug", title[:30])
            markets = ev.get("markets", [])
            for m in markets:
                q = m.get("question", "")
                prob = float(m.get("outcomePrices", "[0.5]").strip("[]").split(",")[0])
                key = f"{slug}_{q[:20]}"
                old_prob = prev.get(key, prob)
                shift = abs(prob - old_prob)
                if shift > 0.10:
                    direction = "UP" if prob > old_prob else "DOWN"
                    send_tg(f"<b>POLYMARKET SHIFT</b>\n{q}\n{direction}: {old_prob:.0%} -> {prob:.0%} ({shift:.0%} move)")
                prev[key] = prob
        with open(state_file, "w") as f:
            json.dump(prev, f)
    except Exception as e:
        print(f"Polymarket error: {e}")

if __name__ == "__main__":
    print("Polymarket scanner started")
    scan_polymarket()
    schedule.every(5).minutes.do(scan_polymarket)
    while True:
        schedule.run_pending()
        time.sleep(30)
