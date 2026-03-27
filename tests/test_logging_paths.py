from __future__ import annotations

import pathlib

from dragonglass import log


def test_setup_logging_creates_log_dir(tmp_path: pathlib.Path) -> None:
    original_data_dir = log.paths.DATA_DIR
    original_log_dir = log.paths.LOG_DIR
    original_log_file = log.LOG_FILE

    try:
        data_dir = tmp_path / "data"
        log.paths.DATA_DIR = data_dir
        log.paths.LOG_DIR = data_dir
        log.LOG_FILE = data_dir / "dragonglass.log"

        log.setup_logging(rollover=False)

        assert data_dir.exists()
        assert (data_dir / "dragonglass.log").exists()
    finally:
        log.paths.DATA_DIR = original_data_dir
        log.paths.LOG_DIR = original_log_dir
        log.LOG_FILE = original_log_file
