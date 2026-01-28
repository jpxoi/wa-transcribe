import queue
import time
from app import core


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


def test_queue_recent_files_disabled(mocker):
    q = queue.Queue()
    mocker.patch("app.config.SCAN_LOOKBACK_ENABLED", False)
    core.queue_recent_files(q)
    assert q.empty()


def test_queue_recent_files_no_dir(mocker):
    q = queue.Queue()
    mocker.patch("app.config.SCAN_LOOKBACK_ENABLED", True)
    mocker.patch("app.config.WHATSAPP_INTERNAL_PATH", None)

    core.queue_recent_files(q)
    assert q.empty()


def test_queue_recent_files_found(mocker):
    q = queue.Queue()
    mock_files = [("root", [], ["file1.opus", "file2.txt", "file3.opus"])]

    mocker.patch("app.config.SCAN_LOOKBACK_ENABLED", True)
    mocker.patch("app.config.WHATSAPP_INTERNAL_PATH", "/mock/path")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.walk", return_value=mock_files)
    mocker.patch("os.path.getmtime", side_effect=[time.time(), time.time()])
    mocker.patch("app.db.is_file_processed", return_value=False)

    core.queue_recent_files(q)

    # file1.opus and file3.opus should be queued
    # file2.txt ignored
    assert q.qsize() == 2


def test_queue_recent_files_already_processed(mocker):
    q = queue.Queue()
    mock_files = [("root", [], ["file1.opus"])]

    mocker.patch("app.config.SCAN_LOOKBACK_ENABLED", True)
    mocker.patch("app.config.WHATSAPP_INTERNAL_PATH", "/mock/path")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.walk", return_value=mock_files)
    mocker.patch("os.path.getmtime", return_value=time.time())
    mocker.patch("app.db.is_file_processed", return_value=True)

    core.queue_recent_files(q)
    assert q.empty()


def test_run_transcriber_no_whatsapp_path(mocker, capsys):
    mocker.patch("app.core.utils.print_banner")
    mocker.patch("app.core.db.init_db")
    mocker.patch("app.core.db.migrate_from_logs")

    # Invalid WhatsApp path
    mocker.patch("app.config.WHATSAPP_INTERNAL_PATH", None)

    core.run_transcriber()

    captured = capsys.readouterr()
    assert "Could not find WhatsApp Media folder" in captured.out


def test_run_transcriber_model_cleanup_called(mocker):
    mocker.patch("app.core.utils.print_banner")
    mocker.patch("app.core.db.init_db")
    mocker.patch("app.core.db.migrate_from_logs")

    # Valid path so we get past guard
    mocker.patch("app.config.WHATSAPP_INTERNAL_PATH", "/mock/path")
    mocker.patch("os.path.exists", return_value=True)

    mocker.patch("app.config.MODEL_CLEANUP_ENABLED", True)
    cleanup = mocker.patch("app.core.maintenance.cleanup_unused_models")

    # Stop execution before infinite loop
    mocker.patch("app.core.whisper.load_model", side_effect=RuntimeError("stop"))
    mocker.patch("app.core.utils.get_compute_device", return_value="cpu")

    try:
        core.run_transcriber()
    except RuntimeError:
        pass

    cleanup.assert_called_once()


def test_show_logs(capsys):
    core.show_logs()
    captured = capsys.readouterr()
    assert "Logs saved to" in captured.out
