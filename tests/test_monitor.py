import pytest  # noqa: F401
import queue
import app.monitor as monitor


def test_internal_audio_handler(mocker):
    """Test InternalAudioHandler queues new files."""
    q = queue.Queue()
    handler = monitor.InternalAudioHandler(q)

    # Use mocker.MagicMock for data objects
    event = mocker.MagicMock()
    event.is_directory = False
    event.src_path = "/path/new_audio.mp3"

    handler.on_created(event)

    assert q.qsize() == 1
    assert q.get() == "/path/new_audio.mp3"


def test_internal_audio_handler_ignore_dup(mocker):
    """Test InternalAudioHandler ignores duplicate events."""
    q = queue.Queue()
    handler = monitor.InternalAudioHandler(q)

    event = mocker.MagicMock()
    event.is_directory = False
    event.src_path = "/path/audio.mp3"

    # Fire event twice
    handler.on_created(event)
    handler.on_created(event)

    # Should only be queued once
    assert q.qsize() == 1


def test_internal_audio_handler_ignore_non_audio(mocker):
    """Test InternalAudioHandler ignores non-audio files."""
    q = queue.Queue()
    handler = monitor.InternalAudioHandler(q)

    event = mocker.MagicMock()
    event.is_directory = False
    event.src_path = "/path/document.txt"

    handler.on_created(event)

    assert q.qsize() == 0
