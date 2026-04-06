#!/usr/bin/env python3
import json
import os
import subprocess
import time

import requests

from core.telegram import send_tg

STATE_FILE = "/root/scripts/regime_state.json"
CTRL_STATE = "/root/data/regime_ctrl_state.json"


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
        docker_cmd("cd /root/freqtrade-sniper && docker-compose stop")
        send_tg("<b>REGIME CONTROLLER</b>\nRISK_OFF: Stopped Sniper — no bots running")
    elif regime in ("RISK_ON", "NEUTRAL"):
        docker_cmd("cd /root/freqtrade-sniper && docker-compose start")
        send_tg(f"<b>REGIME CONTROLLER</b>\n{regime}: Sniper active")
    save_action(regime)


if __name__ == "__main__":
    control_bots()
