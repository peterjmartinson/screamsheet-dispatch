"""Run the screamsheet generator as a subprocess for each subscriber."""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def run_for_subscriber(
    guid: str,
    config_yaml_path: Path,
    output_dir: Path,
    screamsheet_dir: Optional[Path] = None,
) -> List[dict]:
    """Invoke ``screamsheet-service`` for one subscriber and return parsed results.

    The generator is called as:
        uv run screamsheet-service --config <path> --output-dir <dir>

    It is expected to write PDFs into ``output_dir`` and print a JSON array of
    ``GenerationResult`` dicts to stdout.

    Returns:
        Parsed list of GenerationResult dicts.  Returns an empty list on
        non-zero exit code or if stdout cannot be parsed as JSON.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["uv"]
    if screamsheet_dir is not None:
        cmd += ["--directory", str(screamsheet_dir)]
    cmd += ["run", "screamsheet-service", "--config", str(config_yaml_path), "--output-dir", str(output_dir)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error(
            "screamsheet-service failed for %s (exit %d): %s",
            guid,
            result.returncode,
            result.stderr,
        )
        return []

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse generator output for %s: %s", guid, exc)
        return []
