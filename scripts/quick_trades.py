# Quick Trade Viewer
# Pulls recent trades from 3 Freqtrade bot APIs
# github.com/Preston2012/trading-toolkit

import os
import os
import requests
for name, port in [("Sniper",8080),("Hunter",8081),("Scout",8082)]:
    r = requests.get(f"http://" + VPS_HOST + ":{port}/api/v1/trades", auth=(os.environ["FT_USER"], os.environ["FT_PASS"]), params={"limit":5})
    data = r.json()
    print(f"{name}: {data.get('trades_count',0)} trades total, {len(data.get('trades',[]))} shown")
    for t in data.get("trades",[]):
        print(f"  {t.get('pair')} | {t.get('open_date')} | profit: {t.get('close_profit','open')}")
