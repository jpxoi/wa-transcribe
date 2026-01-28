import pytest  # noqa: F401
import queue
import time
import app.core as core


def test_queue_recent_files(mocker):
    """Test queue_recent_files adds files to queue."""
    mock_files = ["recent.mp3", "old.mp3", "processed.mp3"]

    # 1. Setup Config & DB Mocks
    mocker.patch("app.config.WHATSAPP_INTERNAL_PATH", "/whatsapp")
    mocker.patch("app.config.SCAN_LOOKBACK_ENABLED", True)
    mocker.patch("app.config.SCAN_LOOKBACK_HOURS", 24)

    mock_db = mocker.patch("app.db.is_file_processed")
    # processed.mp3 is processed, others are not
    mock_db.side_effect = lambda x: x == "processed.mp3"

    # 2. Setup Filesystem Mocks
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.walk", return_value=[("/whatsapp", [], mock_files)])

    current_time = time.time()
    recent_time = current_time - 3600  # 1 hour ago
    old_time = current_time - (48 * 3600)  # 48 hours ago

    def mtime_side_effect(path):
        if "recent.mp3" in path or "processed.mp3" in path:
            return recent_time
        return old_time

    mocker.patch("os.path.getmtime", side_effect=mtime_side_effect)

    # 3. Execute
    q = queue.Queue()
    core.queue_recent_files(q)

    # 4. Verify
    # recent.mp3: recent (pass time), not processed (pass db) -> QUEUED
    # processed.mp3: recent (pass time), processed (fail db) -> SKIPPED
    # old.mp3: old (fail time) -> SKIPPED

    assert q.qsize() == 1
    assert q.get() == "/whatsapp/recent.mp3"
