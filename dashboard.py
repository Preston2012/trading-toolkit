#!/usr/bin/env python3
import sqlite3, json, os, time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

from config.settings import BOTS as _BOT_CONFIGS

# Build (name, strategy, db_path) tuples from centralized config
BOTS = [(b["name"], b["container"], f"/root/freqtrade-{b['container'].split('-')[-1]}/user_data/tradesv3.sqlite")
        for b in _BOT_CONFIGS]
HTML_PATH = "/root/dashboard/index.html"
os.makedirs("/root/dashboard", exist_ok=True)

def get_stats(db_path):
    if not os.path.exists(db_path):
        return {"trades":0,"open":0,"wins":0,"losses":0,"profit":0}
    try:
        conn = sqlite3.connect(db_path)
        total = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        opn = conn.execute("SELECT COUNT(*) FROM trades WHERE close_date IS NULL").fetchone()[0]
        closed = conn.execute("SELECT COUNT(*) FROM trades WHERE close_date IS NOT NULL").fetchone()[0]
        wins = conn.execute("SELECT COUNT(*) FROM trades WHERE close_profit > 0").fetchone()[0]
        losses = conn.execute("SELECT COUNT(*) FROM trades WHERE close_profit <= 0 AND close_date IS NOT NULL").fetchone()[0]
        profit = conn.execute("SELECT COALESCE(SUM(close_profit),0) FROM trades WHERE close_date IS NOT NULL").fetchone()[0]
        conn.close()
        wr = (wins/closed*100) if closed > 0 else 0
        return {"trades":total,"open":opn,"closed":closed,"wins":wins,"losses":losses,"profit":round(profit*100,2),"winrate":round(wr,1)}
    except:
        return {"trades":0,"open":0,"wins":0,"losses":0,"profit":0,"winrate":0}

def generate_html():
    regime = "UNKNOWN"
    rf = "/root/scripts/regime_state.json"
    if os.path.exists(rf):
        with open(rf) as f:
            regime = json.load(f).get("regime","UNKNOWN")
    rows = ""
    for name, strat, db in BOTS:
        s = get_stats(db)
        color = "#4CAF50" if s.get("profit",0)>0 else "#f44336" if s.get("profit",0)<0 else "#fff"
        rows += f"<tr><td>{name}</td><td>{strat}</td><td>{s.get('trades',0)}</td><td>{s.get('open',0)}</td>"
        rows += f"<td>{s.get('closed',0)}</td><td>{s.get('wins',0)}/{s.get('losses',0)}</td>"
        rows += f"<td>{s.get('winrate',0)}%</td><td style='color:{color}'>{s.get('profit',0)}%</td></tr>"
    html = f"""<!DOCTYPE html><html><head><title>Trading Dashboard</title>
<meta http-equiv="refresh" content="60">
<style>body{{background:#1a1a2e;color:#e0e0e0;font-family:monospace;padding:20px}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #333;padding:10px;text-align:center}}
th{{background:#16213e}}h1{{color:#0f3460}}h2{{color:#e94560}}.regime{{font-size:24px;padding:10px;
background:#16213e;display:inline-block;border-radius:8px;margin:10px 0}}</style></head>
<body><h1>ASYMMETRIC TRADING MACHINE</h1>
<div class="regime">REGIME: {regime}</div>
<p>Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
<h2>Bot Performance</h2>
<table><tr><th>Bot</th><th>Strategy</th><th>Total</th><th>Open</th><th>Closed</th><th>W/L</th><th>Win Rate</th><th>Profit</th></tr>{rows}</table>
</body></html>"""
    with open(HTML_PATH, "w") as f:
        f.write(html)

if __name__ == "__main__":
    while True:
        generate_html()
        time.sleep(60)
