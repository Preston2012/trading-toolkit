#!/usr/bin/env python3
import json, os, subprocess, time, requests

TG_TOKEN = "REDACTED_TG_TOKEN"
TG_CHAT = "REDACTED_TG_CHAT"
STATE_FILE = "/root/scripts/regime_state.json"
CTRL_STATE = "/root/data/regime_ctrl_state.json"

def send_tg(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"})

def docker_cmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

def get_regime():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f).get("regime", "NEUTRAL")
    return "NEUTRAL"

def get_prev_action():
    if os.path.exists(CTRL_STATE):
        with open(CTRL_STATE) as f:
            return json.load(f).get("last_action", "NONE")
    return "NONE"

def save_action(action):
    with open(CTRL_STATE, "w") as f:
        json.dump({"last_action": action, "timestamp": time.time()}, f)

def control_bots():
    regime = get_regime()
    prev = get_prev_action()
    if regime == prev:
        return
    if regime == "RISK_OFF":
        docker_cmd("cd /root/freqtrade-hunter && docker-compose stop")
        docker_cmd("cd /root/freqtrade-scout && docker-compose stop")
        send_tg(f"<b>REGIME CONTROLLER</b>\nRISK_OFF: Stopped Hunter + Scout\nOnly Sniper (conservative) running")
    elif regime == "RISK_ON":
        docker_cmd("cd /root/freqtrade-hunter && docker-compose start")
        docker_cmd("cd /root/freqtrade-scout && docker-compose start")
        send_tg(f"<b>REGIME CONTROLLER</b>\nRISK_ON: All 3 bots active")
    elif regime == "NEUTRAL":
        docker_cmd("cd /root/freqtrade-hunter && docker-compose start")
        docker_cmd("cd /root/freqtrade-scout && docker-compose start")
        send_tg(f"<b>REGIME CONTROLLER</b>\nNEUTRAL: All 3 bots active (normal mode)")
    save_action(regime)

if __name__ == "__main__":
    control_bots()
