import pytest
import queue
from unittest.mock import MagicMock, patch
import app.transcriber as transcriber
from app import config

# --- Mocks & Fixtures ---


@pytest.fixture
def mock_model():
    model = MagicMock()
    # Default behavior for device property
    model.device.type = "cpu"
    # Default behavior for transcribe
    model.transcribe.return_value = {"text": "This is a test transcription."}
    return model


@pytest.fixture
def worker(mock_model):
    """Creates a worker instance with a mocked model and queue."""
    audio_queue = queue.Queue()
    # Patch threading.Thread.start to prevent the thread from actually starting
    with patch("threading.Thread.start"):
        worker = transcriber.TranscriptionWorker(mock_model, audio_queue)
    return worker


# --- Tests ---


def test_save_to_log(mocker):
    """Test save_to_log appends to file correctly."""
    mocker.patch("os.makedirs")
    mock_file = mocker.patch("builtins.open", mocker.mock_open())

    # We mock datetime.datetime within the module usage, but since it's imported as 'datetime'
    # and used as datetime.datetime.now(), we need to patch 'app.transcriber.datetime.datetime'
    # However, since it is a builtin type, it's safer/easier to mock the formatted strings or accept dynamic values.
    # Here we verify the arguments passed contain the key info.

    transcriber.save_to_log("Transcription text", "/path/audio.mp3", "1m 30s", 5.5)

    mock_file.assert_called()
    handle = mock_file()
    handle.write.assert_called()

    args = handle.write.call_args[0][0]
    assert "Transcription text" in args
    assert "audio.mp3" in args
    assert "1m 30s" in args
    assert "5.5s" in args  # .1f format


def test_save_to_log_exception_no_write(mocker):
    """Test save_to_log handles exceptions gracefully."""
    mocker.patch("os.makedirs")
    m = mocker.mock_open()
    mock_open = mocker.patch("app.transcriber.open", m)

    # Make write() fail with IOError
    m().write.side_effect = IOError("Write failed")

    transcriber.save_to_log(
        "Transcription text",
        "/path/audio.mp3",
        "1m 30s",
        5.5,
    )

    mock_open.assert_called()
    m().write.assert_called_once()  # write attempted


def test_worker_initialization(worker, mock_model):
    """Test worker initializes effectively."""
    assert worker.model == mock_model
    assert isinstance(worker.queue, queue.Queue)
    assert worker.daemon is True


@patch("app.transcriber.whisper.load_audio")
@patch("app.transcriber.utils.format_duration")
@patch("app.transcriber.save_to_log")
@patch("app.db.add_processed_file")
@patch("app.transcriber.pyperclip.copy")
def test_process_file_success(
    mock_copy, mock_add_db, mock_save_log, mock_fmt_dur, mock_load_audio, worker
):
    """Test successful processing of a file."""
    # Setup mocks
    mock_load_audio.return_value = [0.0] * 16000 * 10  # 10 seconds of dummy audio
    mock_fmt_dur.return_value = "10s"

    # Ensure file ready check passes immediately
    with patch.object(worker, "wait_for_file_ready", return_value=True):
        worker.process_file("/tmp/test_audio.ogg")

    # Check interactions
    mock_load_audio.assert_called_with("/tmp/test_audio.ogg")
    worker.model.transcribe.assert_called()
    call_args = worker.model.transcribe.call_args
    assert call_args[0][0] == "/tmp/test_audio.ogg"

    # Should copy to clipboard
    mock_copy.assert_called_with("This is a test transcription.")

    # Should save to log
    mock_save_log.assert_called()
    args = mock_save_log.call_args[0]
    assert args[0] == "This is a test transcription."
    assert args[1] == "/tmp/test_audio.ogg"

    # Should add to DB
    mock_add_db.assert_called_with("test_audio.ogg", "/tmp/test_audio.ogg")


@patch("app.transcriber.whisper.load_audio")
@patch("app.transcriber.save_to_log")
@patch("app.db.add_processed_file")
@patch("app.transcriber.pyperclip.copy")
def test_process_file_unknown_duration(
    mock_copy,
    mock_add_db,
    mock_save_log,
    mock_load_audio,
    worker,
    capsys,
):
    """Test process_file falls back to 'Unknown duration' and still transcribes."""

    # Force duration calculation to fail
    mock_load_audio.side_effect = Exception("decode failed")

    with patch.object(worker, "wait_for_file_ready", return_value=True):
        worker.process_file("/tmp/test_audio.ogg")

    # Transcription should still happen
    worker.model.transcribe.assert_called_once()

    captured = capsys.readouterr()
    assert "Unknown duration" in captured.out


@patch("app.transcriber.whisper.load_audio")
def test_process_file_exception(mock_load_audio, worker, capsys):
    """Test process_file handles transcription exceptions gracefully."""

    # Make duration succeed
    mock_load_audio.return_value = [0.0] * 16000

    # Force transcription to fail
    worker.model.transcribe.side_effect = Exception("Model failure")

    with patch.object(worker, "wait_for_file_ready", return_value=True):
        worker.process_file("/tmp/test_audio.ogg")

    captured = capsys.readouterr()
    assert "✗ [ERROR]" in captured.out
    assert "Model failure" in captured.out


@patch("app.transcriber.whisper.load_audio")
@patch("app.transcriber.pyperclip.copy")
@patch("app.transcriber.save_to_log")
@patch("app.db.add_processed_file")
def test_process_file_clipboard_exception(
    mock_add_db,
    mock_save_log,
    mock_copy,
    mock_load_audio,
    worker,
    capsys,
):
    """Test clipboard failure does not break processing."""

    mock_load_audio.return_value = [0.0] * 16000
    mock_copy.side_effect = Exception("Clipboard unavailable")

    with patch.object(worker, "wait_for_file_ready", return_value=True):
        worker.process_file("/tmp/test_audio.ogg")

    # Transcription still happens
    worker.model.transcribe.assert_called_once()

    # Log + DB still happen
    mock_save_log.assert_called_once()
    mock_add_db.assert_called_once()

    captured = capsys.readouterr()
    assert (
        "Clipboard unavailable" in captured.out
        or "⚠ Clipboard unavailable" in captured.out
    )


def test_process_file_not_ready(worker):
    """Test processing aborts if file is not ready."""
    with patch.object(worker, "wait_for_file_ready", return_value=False):
        # We also create a mock print checking if timeout message appears,
        # but return value is None, just ensures no crash.
        worker.process_file("/tmp/missing.ogg")

        # Verify no transcription happened
        worker.model.transcribe.assert_not_called()


@patch("os.path.getsize")
@patch("time.sleep")
def test_wait_for_file_ready_success(mock_sleep, mock_getsize, worker):
    """Test file ready check returns True when size stabilizes."""
    # Sequence of sizes: 100, 100 (stable)
    mock_getsize.side_effect = [100, 100]

    ready = worker.wait_for_file_ready("/tmp/file", timeout=5)
    assert ready is True
    assert mock_getsize.call_count == 2


@patch("os.path.getsize")
@patch("time.sleep")
@patch("time.time")
def test_wait_for_file_ready_timeout(mock_time, mock_sleep, mock_getsize, worker):
    """Test file ready check returns False on timeout."""
    # Prepare time to simulate timeout
    # time.time() is called:
    # 1. start_time assignment
    # 2. while check 1 (ok)
    # 3. while check 2 (timeout)
    # We want to loop at least once.
    # Let's say inputs are: 0, 1, 100 (where 100 > timeout=10)
    mock_time.side_effect = [0, 1, 11]

    # File size always changing
    mock_getsize.side_effect = [10, 20, 30]

    ready = worker.wait_for_file_ready("/tmp/file", timeout=10)
    assert ready is False


def test_fp16_logic_cuda(worker):
    """Test that CUDA device triggers fp16=True."""
    worker.model.device.type = "cuda"
    with (
        patch.object(worker, "wait_for_file_ready", return_value=True),
        patch("app.transcriber.whisper.load_audio"),
        patch("app.transcriber.pyperclip.copy"),
        patch("app.transcriber.save_to_log"),
        patch("app.db.add_processed_file"),
    ):
        worker.process_file("dummies.mp3")

        args = worker.model.transcribe.call_args[1]
        assert args.get("fp16") is True


def test_fp16_logic_mps_disabled(worker):
    """Test that MPS device triggers fp16=False by default (or if config says so)."""
    worker.model.device.type = "mps"
    # Assuming default is False or not set in config yet
    # We can patch config to be sure
    with (
        patch.object(config, "ENABLE_MPS_FP16", False),
        patch.object(worker, "wait_for_file_ready", return_value=True),
        patch("app.transcriber.whisper.load_audio"),
        patch("app.transcriber.pyperclip.copy"),
        patch("app.transcriber.save_to_log"),
        patch("app.db.add_processed_file"),
    ):
        worker.process_file("dummies.mp3")

        args = worker.model.transcribe.call_args[1]
        assert args.get("fp16") is False


def test_fp16_logic_mps_enabled(worker):
    """Test that MPS device triggers fp16=True if config enabled."""
    worker.model.device.type = "mps"
    with (
        patch.object(config, "ENABLE_MPS_FP16", True),
        patch.object(worker, "wait_for_file_ready", return_value=True),
        patch("app.transcriber.whisper.load_audio"),
        patch("app.transcriber.pyperclip.copy"),
        patch("app.transcriber.save_to_log"),
        patch("app.db.add_processed_file"),
    ):
        worker.process_file("dummies.mp3")

        args = worker.model.transcribe.call_args[1]
        assert args.get("fp16") is True
