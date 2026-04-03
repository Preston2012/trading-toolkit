# Freqtrade Bot Health Check
# Checks 3 Docker containers running algorithmic trading bots
# github.com/Preston2012/trading-toolkit

import os
import os
import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.environ["VPS_HOST"], username=os.environ.get("VPS_USER", "root"), password=os.environ["VPS_PASSWORD"])
def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    return stdout.read().decode() + stderr.read().decode()
print("=== CONTAINER STATUS ===")
print(run("docker ps -a"))
print("=== SNIPER (NFIX7) ===")
print(run("docker logs ft-sniper --tail 15 2>&1"))
print("=== HUNTER (NFIX4) ===")
print(run("docker logs ft-hunter --tail 10 2>&1"))
print("=== SCOUT (NFIX5) ===")
print(run("docker logs ft-scout --tail 10 2>&1"))
print("=== MEMORY ===")
print(run("free -m"))
ssh.close()
