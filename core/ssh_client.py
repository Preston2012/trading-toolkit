"""SSH client for remote VPS management.

Provides a shared client with retry logic, timeout handling,
structured command output, and context manager support.
Replaces duplicated SSH boilerplate across all scripts.
"""

import logging
import time
from dataclasses import dataclass

import paramiko

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Structured result from a remote command execution."""

    stdout: str
    stderr: str
    exit_code: int

    @property
    def ok(self) -> bool:
        """True if command exited successfully."""
        return self.exit_code == 0

    @property
    def output(self) -> str:
        """Combined stdout and stderr."""
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)


class VPSClient:
    """SSH client for remote VPS management with retry and structured output."""

    def __init__(
        self,
        host: str,
        user: str = "root",
        password: str = "",
        timeout: int = 30,
        retries: int = 3,
    ) -> None:
        self.host = host
        self.user = user
        self.password = password
        self.timeout = timeout
        self.retries = retries
        self._client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        """Establish SSH connection with retry logic."""
        for attempt in range(1, self.retries + 1):
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    self.host,
                    username=self.user,
                    password=self.password,
                    timeout=self.timeout,
                )
                self._client = client
                return
            except paramiko.SSHException as exc:
                logger.warning("SSH connect attempt %d/%d failed: %s", attempt, self.retries, exc)
                if attempt == self.retries:
                    raise
                time.sleep(2 ** attempt)

    def close(self) -> None:
        """Close the SSH connection."""
        if self._client:
            self._client.close()
            self._client = None

    def run(self, command: str, timeout: int = 30) -> CommandResult:
        """Execute a command and return structured result."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
        stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        return CommandResult(stdout=out, stderr=err, exit_code=exit_code)

    def get_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from the VPS."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
        sftp = self._client.open_sftp()
        try:
            sftp.get(remote_path, local_path)
        finally:
            sftp.close()

    def put_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file to the VPS."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
        sftp = self._client.open_sftp()
        try:
            sftp.put(local_path, remote_path)
        finally:
            sftp.close()

    def __enter__(self) -> "VPSClient":
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
