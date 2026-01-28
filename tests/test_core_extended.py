import os
import queue
import time
from unittest.mock import patch, MagicMock
from app import core, config


def test_queue_recent_files_disabled():
    q = queue.Queue()
    with patch("app.config.SCAN_LOOKBACK_ENABLED", False):
        core.queue_recent_files(q)
        assert q.empty()


def test_queue_recent_files_no_dir():
    q = queue.Queue()
    with (
        patch("app.config.SCAN_LOOKBACK_ENABLED", True),
        patch("app.config.WHATSAPP_INTERNAL_PATH", None),
    ):
        core.queue_recent_files(q)
        assert q.empty()


def test_queue_recent_files_found():
    q = queue.Queue()
    mock_files = [("root", [], ["file1.opus", "file2.txt", "file3.opus"])]

    with (
        patch("app.config.SCAN_LOOKBACK_ENABLED", True),
        patch("app.config.WHATSAPP_INTERNAL_PATH", "/mock/path"),
        patch("os.path.exists", return_value=True),
        patch("os.walk", return_value=mock_files),
        patch("os.path.getmtime", side_effect=[time.time(), time.time()]),
        patch("app.db.is_file_processed", return_value=False),
    ):
        core.queue_recent_files(q)

        # file1.opus and file3.opus should be queued
        # file2.txt ignored
        assert q.qsize() == 2


def test_queue_recent_files_already_processed():
    q = queue.Queue()
    mock_files = [("root", [], ["file1.opus"])]

    with (
        patch("app.config.SCAN_LOOKBACK_ENABLED", True),
        patch("app.config.WHATSAPP_INTERNAL_PATH", "/mock/path"),
        patch("os.path.exists", return_value=True),
        patch("os.walk", return_value=mock_files),
        patch("os.path.getmtime", return_value=time.time()),
        patch("app.db.is_file_processed", return_value=True),
    ):
        core.queue_recent_files(q)
        assert q.empty()
