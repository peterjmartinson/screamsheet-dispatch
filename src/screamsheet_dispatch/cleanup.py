"""Outbox folder cleanup — remove daily folders older than the retention period."""
from __future__ import annotations

import logging
import shutil
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def cleanup_outbox(outbox_path: Path, retention_days: int) -> int:
    """Delete daily outbox folders whose date is older than ``retention_days``.

    Daily folders are named YYYYMMDD.  Any folder whose name cannot be parsed
    as a date is left untouched.

    Args:
        outbox_path:    Root outbox directory to scan.
        retention_days: Folders older than this many days are removed.

    Returns:
        Number of folders deleted.
    """
    if not outbox_path.exists():
        return 0

    cutoff = date.today() - timedelta(days=retention_days)
    deleted = 0

    for folder in outbox_path.iterdir():
        if not folder.is_dir():
            continue
        try:
            name = folder.name
            folder_date = date(int(name[:4]), int(name[4:6]), int(name[6:8]))
        except (ValueError, IndexError):
            continue
        if folder_date < cutoff:
            shutil.rmtree(folder)
            logger.info("Removed outbox folder: %s", folder)
            deleted += 1

    return deleted
