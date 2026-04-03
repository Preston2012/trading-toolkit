# VPS Full System Audit
# Audits all services, scripts, data dirs, cron, and memory on Hetzner VPS
# github.com/Preston2012/trading-toolkit

import os
import os
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.environ["VPS_HOST"], username=os.environ.get("VPS_USER", "root"), password=os.environ["VPS_PASSWORD"])
def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    return stdout.read().decode() + stderr.read().decode()
print("=== SCRIPTS ===")
print(run("ls -la /root/scripts/"))
print("=== TRADING-INFRA ===")
print(run("ls -la /root/trading-infra/ 2>/dev/null || echo 'NO DIR'"))
print("=== DATA DIR ===")
print(run("ls -la /root/data/ 2>/dev/null || echo 'NO DIR'"))
print("=== DASHBOARD ===")
print(run("ls -la /root/dashboard/ 2>/dev/null || echo 'NO DIR'"))
print("=== SERVICES ===")
print(run("systemctl list-units --type=service --state=active | grep -E 'trading|poly|replay|exec|ibit|dash'"))
print("=== TMUX ===")
print(run("tmux list-sessions 2>&1"))
print("=== CRON ===")
print(run("crontab -l"))
print("=== KRAKEN DATA ===")
print(run("ls -lh /root/freqtrade-sniper/user_data/data/kraken/ 2>/dev/null || echo 'NO DATA'"))
print("=== ENV FILE ===")
print(run("cat /root/.env 2>/dev/null || echo 'NO .env'"))
print("=== PORT 8083 ===")
print(run("ss -tlnp | grep 8083 || echo 'Dashboard not serving'"))
ssh.close()
