"""Freqtrade API client and config adjustment logic for the adaptive brain."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 10


def ft_auth(base_url: str, username: str, password: str) -> str:
    """Authenticate with Freqtrade API and return JWT access token."""
    resp = requests.post(
        f"{base_url}/api/v1/token/login",
        json={"username": username, "password": password},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def ft_get(base_url: str, token: str, endpoint: str, params: dict | None = None) -> dict:
    """Authenticated GET request to Freqtrade API."""
    resp = requests.get(
        f"{base_url}/api/v1/{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def ft_post(base_url: str, token: str, endpoint: str, data: dict | None = None) -> dict:
    """Authenticated POST request to Freqtrade API."""
    resp = requests.post(
        f"{base_url}/api/v1/{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        json=data or {},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def ft_delete(base_url: str, token: str, endpoint: str) -> dict:
    """Authenticated DELETE request to Freqtrade API."""
    resp = requests.delete(
        f"{base_url}/api/v1/{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_trades(base_url: str, token: str, limit: int = 200) -> list[dict]:
    """Fetch recent trades from a bot."""
    data = ft_get(base_url, token, "trades", params={"limit": limit})
    return data.get("trades", [])


def get_performance(base_url: str, token: str) -> list[dict]:
    """Fetch pair performance summary."""
    return ft_get(base_url, token, "performance")


def get_blacklist(base_url: str, token: str) -> list[str]:
    """Fetch current blacklist."""
    data = ft_get(base_url, token, "blacklist")
    return data.get("blacklist", [])


def build_blacklist_update(
    underperformers: list[str],
    current_blacklist: list[str],
) -> dict[str, list[str]]:
    """Determine which pairs to add/remove from blacklist.

    Returns:
        Dict with 'add' and 'remove' lists.
    """
    to_add = [p for p in underperformers if p not in current_blacklist]
    return {"add": to_add, "remove": []}


def apply_adjustments(
    base_url: str,
    token: str,
    adjustments: dict,
    dry_run: bool = True,
) -> list[str]:
    """Apply recommended adjustments to a bot via API.

    Args:
        base_url: Bot API base URL (e.g. http://localhost:8080).
        token: JWT access token.
        adjustments: Output of recommend_adjustments().
        dry_run: If True, only log what would be done.

    Returns:
        List of action log strings.
    """
    actions: list[str] = []
    current_bl = get_blacklist(base_url, token)
    bl_update = build_blacklist_update(adjustments.get("blacklist_add", []), current_bl)

    for pair in bl_update["add"]:
        if dry_run:
            actions.append(f"[DRY RUN] Would blacklist {pair}")
        else:
            ft_post(base_url, token, "blacklist", {"blacklist": [pair]})
            actions.append(f"Blacklisted {pair}")

    for pair in bl_update["remove"]:
        if dry_run:
            actions.append(f"[DRY RUN] Would un-blacklist {pair}")
        else:
            ft_delete(base_url, token, f"blacklist/{pair}")
            actions.append(f"Un-blacklisted {pair}")

    if bl_update["add"] or bl_update["remove"]:
        if not dry_run:
            ft_post(base_url, token, "reload_config")
            actions.append("Reloaded bot config")

    return actions
