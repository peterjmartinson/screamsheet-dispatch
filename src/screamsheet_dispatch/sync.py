"""Sync subscriber data from Google Sheets to local GUID-named YAML config files."""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

import gspread
import yaml
from google.oauth2.service_account import Credentials

from .config import DispatchConfig

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Outcome of a subscriber sync run."""
    success: bool
    subscribers_updated: int = 0
    subscribers_removed: int = 0
    error: Optional[str] = None
    used_fallback: bool = False


def write_subscriber_config(guid: str, data: dict, config_store: Path) -> None:
    """Write a single subscriber's config as a GUID-named YAML file.

    Args:
        guid:         Subscriber GUID (becomes the filename stem).
        data:         Dict to serialise as YAML.
        config_store: Directory in which to write the file.
    """
    config_store.mkdir(parents=True, exist_ok=True)
    file_path = config_store / f"{guid}.yaml"
    with open(file_path, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False, allow_unicode=True)


def remove_stale_configs(current_guids: Set[str], config_store: Path) -> int:
    """Remove any GUID YAML files whose GUID is not in ``current_guids``.

    Returns:
        Number of files removed.
    """
    removed = 0
    for yaml_file in config_store.glob("*.yaml"):
        if yaml_file.stem not in current_guids:
            yaml_file.unlink()
            logger.info("Removed stale config: %s", yaml_file)
            removed += 1
    return removed


def _git_commit_push(config_store: Path, message: str) -> None:
    """Stage all changes, commit, and push in ``config_store``."""
    subprocess.run(["git", "add", "."], cwd=str(config_store), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message], cwd=str(config_store), check=True, capture_output=True
    )
    subprocess.run(["git", "push"], cwd=str(config_store), check=True, capture_output=True)


def sync_subscribers(config: DispatchConfig) -> SyncResult:
    """Pull subscribers from Google Sheets and write local YAML configs.

    On any Google Sheets API failure, returns a ``SyncResult`` with
    ``used_fallback=True``; the caller continues using existing config files.

    Returns:
        SyncResult describing the outcome.
    """
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds = Credentials.from_service_account_file(
            config.google_sheets.credentials_file, scopes=scopes
        )
        gc = gspread.authorize(creds)
        rows = gc.open_by_key(config.google_sheets.spreadsheet_id).sheet1.get_all_records()
    except Exception as exc:
        logger.error("Google Sheets sync failed: %s", exc)
        return SyncResult(success=False, error=str(exc), used_fallback=True)

    config_store = Path(config.paths.config_store)
    current_guids: Set[str] = set()
    updated = 0

    for row in rows:
        guid = str(row.get("guid", "")).strip()
        if not guid:
            continue
        subscriber_data = {
            "guid": guid,
            "name": str(row.get("name", "")),
            "email": str(row.get("email", "")),
            "sheets": _parse_sheet_list(row),
        }
        write_subscriber_config(guid, subscriber_data, config_store)
        current_guids.add(guid)
        updated += 1

    removed = remove_stale_configs(current_guids, config_store)

    try:
        _git_commit_push(
            config_store,
            f"sync: update {updated} subscribers, remove {removed}",
        )
    except subprocess.CalledProcessError as exc:
        logger.warning("git commit/push failed (non-fatal): %s", exc)

    return SyncResult(
        success=True,
        subscribers_updated=updated,
        subscribers_removed=removed,
    )


def _parse_sheet_list(row: dict) -> List[str]:
    """Extract the comma-separated sheet type list from a subscriber row."""
    raw = str(row.get("sheets", ""))
    return [s.strip() for s in raw.split(",") if s.strip()]
