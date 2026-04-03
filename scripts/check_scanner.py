# Scanner Log Checker
# Checks options scanner output, Trump signal data, and scan results
# github.com/Preston2012/trading-toolkit

import os
import os
import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.environ["VPS_HOST"], username=os.environ.get("VPS_USER", "root"), password=os.environ["VPS_PASSWORD"])
time.sleep(30)
print("=== LOG ===")
print(ssh.exec_command("tail -15 /root/logs/options-scanner.log 2>/dev/null")[1].read().decode())
print("=== DATA ===")
print(ssh.exec_command("cat /root/data/options_scan.json 2>/dev/null | head -80")[1].read().decode())
print("=== TRUMP SEEN ===")
print(ssh.exec_command("cat /root/data/seen_headlines.json 2>/dev/null | head -5")[1].read().decode())
ssh.close()
