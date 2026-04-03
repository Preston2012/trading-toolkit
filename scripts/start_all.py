# Service Orchestrator
# Starts and verifies all 14 systemd services on VPS
# github.com/Preston2012/trading-toolkit

import os
import os
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.environ["VPS_HOST"], username=os.environ.get("VPS_USER", "root"), password=os.environ["VPS_PASSWORD"])

def run(cmd, t=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=t)
    return stdout.read().decode("utf-8", errors="replace").strip()

print("=== Starting all new services ===")
run("systemctl daemon-reload")
svcs = ["morning-briefing","arb-bridge","position-tracker","rss-scraper","weekly-report"]
for s in svcs:
    run(f"systemctl enable {s} 2>/dev/null")
    run(f"systemctl restart {s}")
    st = run(f"systemctl is-active {s}")
    print(f"  {s}: {st}")

print("\n=== FULL SYSTEM CHECK ===")
full = ["polymarket-scanner","replay-engine","execution-monitor","ibit-monitor",
    "trading-alerts","trading-dashboard","dashboard-http","unified-reporter",
    "options-scanner","morning-briefing","arb-bridge","position-tracker",
    "rss-scraper","weekly-report"]
active = 0
for s in full:
    st = run(f"systemctl is-active {s}")
    print(f"  {s}: {st}")
    if st == "active": active += 1

print(f"\n{active}/{len(full)} services active")
print(f"\nDocker: {run('docker ps --format {{.Names}} | wc -l')} containers")
print(f"Memory: {run('free -m | grep Mem')}")
print(f"Scripts: {run('ls /root/scripts/*.py | wc -l')} total")
ssh.close()
