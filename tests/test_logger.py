"""Unit tests for screamsheet_dispatch.logger."""
from pathlib import Path

import pytest
import sqlalchemy as sa

from screamsheet_dispatch.logger import log_delivery, write_run_log


# ---------------------------------------------------------------------------
# log_delivery
# ---------------------------------------------------------------------------

class TestLogDelivery:
    def test_creates_delivery_log_table_on_first_call(self, tmp_path):
        db_path = tmp_path / "dispatch.db"
        log_delivery(
            db_path=db_path,
            guid="g1",
            run_date="20260506",
            sheet_type="nhl",
            pdf_path="/tmp/nhl.pdf",
            email_address="a@b.com",
            outcome="success",
        )
        engine = sa.create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            tables = sa.inspect(engine).get_table_names()
        assert "delivery_log" in tables

    def test_records_outcome_success(self, tmp_path):
        db_path = tmp_path / "dispatch.db"
        log_delivery(
            db_path=db_path,
            guid="g1",
            run_date="20260506",
            sheet_type="nhl",
            pdf_path="/tmp/nhl.pdf",
            email_address="a@b.com",
            outcome="success",
        )
        engine = sa.create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            row = conn.execute(sa.text("SELECT outcome FROM delivery_log")).fetchone()
        assert row[0] == "success"

    def test_records_error_detail_on_failure(self, tmp_path):
        db_path = tmp_path / "dispatch.db"
        log_delivery(
            db_path=db_path,
            guid="g1",
            run_date="20260506",
            sheet_type="nhl",
            pdf_path="/tmp/nhl.pdf",
            email_address="a@b.com",
            outcome="failure",
            error_detail="SMTP timeout",
        )
        engine = sa.create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            row = conn.execute(sa.text("SELECT error_detail FROM delivery_log")).fetchone()
        assert row[0] == "SMTP timeout"

    def test_records_guid(self, tmp_path):
        db_path = tmp_path / "dispatch.db"
        log_delivery(
            db_path=db_path,
            guid="abc-123",
            run_date="20260506",
            sheet_type="mlb",
            pdf_path="/tmp/mlb.pdf",
            email_address="a@b.com",
            outcome="success",
        )
        engine = sa.create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            row = conn.execute(sa.text("SELECT guid FROM delivery_log")).fetchone()
        assert row[0] == "abc-123"

    def test_multiple_calls_insert_multiple_rows(self, tmp_path):
        db_path = tmp_path / "dispatch.db"
        for sheet in ("nhl", "mlb"):
            log_delivery(
                db_path=db_path,
                guid="g1",
                run_date="20260506",
                sheet_type=sheet,
                pdf_path=f"/tmp/{sheet}.pdf",
                email_address="a@b.com",
                outcome="success",
            )
        engine = sa.create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            count = conn.execute(sa.text("SELECT COUNT(*) FROM delivery_log")).scalar()
        assert count == 2


# ---------------------------------------------------------------------------
# write_run_log
# ---------------------------------------------------------------------------

class TestWriteRunLog:
    def test_creates_log_file(self, tmp_path):
        log_path = write_run_log(tmp_path / "logs", "test content")
        assert log_path.exists()

    def test_file_contains_content(self, tmp_path):
        log_path = write_run_log(tmp_path / "logs", "hello world")
        assert "hello world" in log_path.read_text(encoding="utf-8")

    def test_creates_log_dir_if_missing(self, tmp_path):
        new_dir = tmp_path / "new" / "logs"
        write_run_log(new_dir, "content")
        assert new_dir.is_dir()

    def test_log_filename_has_timestamp_format(self, tmp_path):
        log_path = write_run_log(tmp_path / "logs", "content")
        # Filename should be YYYYMMDD_HHMMSS.log
        assert log_path.suffix == ".log"
        assert len(log_path.stem) == 15  # YYYYMMDD_HHMMSS
