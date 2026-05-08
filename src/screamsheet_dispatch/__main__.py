"""Entry point: orchestrate the full sync → generate → deliver → log → alert cycle."""
from __future__ import annotations

import logging
import time
from datetime import date
from pathlib import Path

import yaml

from .cleanup import cleanup_outbox
from .config import load_dispatch_config
from .delivery import send_admin_alert, send_subscriber_email
from .logger import log_delivery, write_run_log
from .runner import run_for_subscriber
from .sync import sync_subscribers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_CONFIG_PATH = Path("dispatch_config.yaml")


def main() -> None:
    """Run the full dispatch cycle."""
    config = load_dispatch_config(_CONFIG_PATH)
    today = date.today().strftime("%Y%m%d")
    run_log_lines: list[str] = [f"=== Scream Sheet Dispatch — {today} ==="]

    outbox_root = Path(config.paths.outbox)
    config_store = Path(config.paths.config_store)

    # --- Cleanup old outbox folders ---
    removed = cleanup_outbox(outbox_root, config.retention.outbox_days)
    run_log_lines.append(f"Cleanup: removed {removed} old outbox folder(s)")

    # --- Sync subscribers from Google Sheets ---
    sync_result = sync_subscribers(config)
    if sync_result.used_fallback:
        run_log_lines.append(
            f"WARN Sync failed: {sync_result.error} — using existing local configs"
        )
    else:
        run_log_lines.append(
            f"Sync: {sync_result.subscribers_updated} updated, "
            f"{sync_result.subscribers_removed} removed"
        )

    # --- Generate and deliver for each subscriber ---
    db_path = outbox_root / "dispatch.db"
    for config_file in sorted(config_store.glob("*.yaml")):
        guid = config_file.stem
        subscriber_outbox = outbox_root / today / guid

        # Load subscriber metadata
        with open(config_file, encoding="utf-8") as fh:
            subscriber = yaml.safe_load(fh) or {}
        email_address = subscriber.get("email", "")
        name = subscriber.get("name", guid)

        # Generate
        screamsheet_dir = Path(config.paths.screamsheet_dir) if config.paths.screamsheet_dir else None
        results = run_for_subscriber(guid, config_file, subscriber_outbox, screamsheet_dir=screamsheet_dir)
        if not results:
            run_log_lines.append(
                f"  {guid} ({name}): generation FAILED — no PDFs produced; skipping delivery"
            )
            continue

        for r in results:
            for issue in r.get("issues", []):
                run_log_lines.append(f"  {guid} ({name}): layout warning — {issue}")

        pdf_paths = [
            Path(r["pdf_path"]) for r in results if r.get("pdf_path")
        ]
        pdf_paths = [p for p in pdf_paths if p.exists()]

        if not pdf_paths:
            run_log_lines.append(
                f"  {guid} ({name}): no valid PDF files found; skipping delivery"
            )
            continue

        if not email_address:
            run_log_lines.append(
                f"  {guid} ({name}): no email address configured; skipping delivery"
            )
            continue

        # Deliver
        try:
            send_subscriber_email(email_address, pdf_paths, today, config.smtp)
            outcome = "success"
            error_detail = None
            run_log_lines.append(
                f"  {guid} ({name}): delivered {len(pdf_paths)} PDF(s) to {email_address}"
            )
        except Exception as exc:
            outcome = "failure"
            error_detail = str(exc)
            run_log_lines.append(f"  {guid} ({name}): delivery FAILED — {exc}")

        for r in results:
            log_delivery(
                db_path=db_path,
                guid=guid,
                run_date=today,
                sheet_type=r.get("sheet_type", ""),
                pdf_path=r.get("pdf_path", ""),
                email_address=email_address,
                outcome=outcome,
                error_detail=error_detail,
            )

        time.sleep(config.smtp.send_delay_seconds)

    # --- Write run log ---
    log_content = "\n".join(run_log_lines)
    log_path = write_run_log(Path("logs"), log_content)
    logger.info("Run log written to: %s", log_path)

    # --- Send admin summary ---
    try:
        send_admin_alert(log_content, config.smtp, config.admin.alert_email)
    except Exception as exc:
        logger.error("Failed to send admin alert: %s", exc)


if __name__ == "__main__":
    main()
