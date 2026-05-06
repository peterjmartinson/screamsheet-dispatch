"""SQLite delivery logging and run log file writing."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import sqlalchemy as sa

logger = logging.getLogger(__name__)

_METADATA = sa.MetaData()

_DELIVERY_LOG_TABLE = sa.Table(
    "delivery_log",
    _METADATA,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("run_date", sa.Text, nullable=False),
    sa.Column("guid", sa.Text, nullable=False),
    sa.Column("sheet_type", sa.Text, nullable=False),
    sa.Column("pdf_path", sa.Text, nullable=False),
    sa.Column("email_address", sa.Text, nullable=False),
    sa.Column("outcome", sa.Text, nullable=False),
    sa.Column("error_detail", sa.Text, nullable=True),
    sa.Column("timestamp", sa.Text, nullable=False),
)


def _get_engine(db_path: Path) -> sa.engine.Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sa.create_engine(f"sqlite:///{db_path}")


def log_delivery(
    db_path: Path,
    guid: str,
    run_date: str,
    sheet_type: str,
    pdf_path: str,
    email_address: str,
    outcome: str,
    error_detail: Optional[str] = None,
) -> None:
    """Insert one row into the delivery_log table, creating it if needed.

    Args:
        db_path:       Path to the SQLite database file.
        guid:          Subscriber GUID.
        run_date:      YYYYMMDD run date string.
        sheet_type:    Sheet type key (e.g. "nhl", "mlb").
        pdf_path:      Absolute path to the generated PDF.
        email_address: Subscriber's email address.
        outcome:       "success" or "failure".
        error_detail:  Error message if outcome is "failure"; None otherwise.
    """
    engine = _get_engine(db_path)
    _METADATA.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            _DELIVERY_LOG_TABLE.insert().values(
                run_date=run_date,
                guid=guid,
                sheet_type=sheet_type,
                pdf_path=pdf_path,
                email_address=email_address,
                outcome=outcome,
                error_detail=error_detail,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )


def write_run_log(log_dir: Path, content: str) -> Path:
    """Write ``content`` to a timestamped log file in ``log_dir``.

    Args:
        log_dir: Directory in which to write the log (created if needed).
        content: Plain-text log content.

    Returns:
        Path of the written log file.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"{timestamp}.log"
    log_path.write_text(content, encoding="utf-8")
    return log_path
