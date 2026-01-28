from unittest.mock import patch, MagicMock, mock_open
import app.core as core
import time
import queue


def test_cleanup_unused_models_no_cache():
    """Test cleanup_unused_models returns early if cache dir doesn't exist."""
    with patch("os.path.exists", return_value=False):
        # Should not raise exception
        core.cleanup_unused_models("turbo")


def test_cleanup_unused_models_deletes_old():
    """Test cleanup_unused_models deletes old files."""
    mock_files = ["turbo.pt", "old.pt", "other.pt"]

    with (
        patch("os.path.expanduser", return_value="/cache"),
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=mock_files),
        patch("app.config.KNOWN_MODELS", ["turbo.pt", "old.pt", "other.pt"]),
        patch("os.path.join", side_effect=lambda a, b: f"{a}/{b}"),
        patch("os.stat") as mock_stat,
        patch("os.remove") as mock_remove,
    ):
        # Setup timestamps
        current_time = time.time()
        old_time = current_time - (8 * 24 * 60 * 60)  # 8 days ago
        new_time = current_time - (1 * 24 * 60 * 60)  # 1 day ago

        mock_stat.return_value.st_atime = old_time
        # Make safe so turbo.pt doesn't get deleted even if old (logic handles this by name check)

        # We need to control the loop or mock stat for each call
        # Mocking individual file stats is complex with side_effect,
        # so let's simplify: "old.pt" is old, "turbo.pt" is current model.

        def stat_side_effect(path):
            m = MagicMock()
            if "old.pt" in path:
                m.st_atime = old_time
            else:
                m.st_atime = new_time
            return m

        mock_stat.side_effect = stat_side_effect

        core.cleanup_unused_models("turbo")

        # expect old.pt to be removed
        mock_remove.assert_called_with("/cache/old.pt")
        # expect turbo.pt NOT to be removed (it's the current model)
        assert mock_remove.call_count == 1


def test_save_to_log():
    """Test save_to_log appends to file."""
    with patch("os.makedirs"), patch("builtins.open", mock_open()) as mock_file:
        core.save_to_log("Transcription text", "/path/audio.mp3", "1m 30s", 5.5)

        mock_file.assert_called()
        handle = mock_file()
        handle.write.assert_called()
        args = handle.write.call_args[0][0]
        assert "Transcription text" in args
        assert "audio.mp3" in args


def test_get_processed_history():
    """Test get_processed_history parsing."""
    mock_log_content = "─── INFO ───\naudio.mp3  |  ⏳ 1m 30s  |  ⏱ done\n\nText\n\n"

    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=mock_log_content)),
    ):
        history = core.get_processed_history(days_to_check=1)
        assert "audio.mp3" in history


def test_internal_audio_handler():
    """Test InternalAudioHandler queues new files."""
    q = queue.Queue()
    handler = core.InternalAudioHandler(q)

    event = MagicMock()
    event.is_directory = False
    event.src_path = "/path/new_audio.mp3"

    handler.on_created(event)

    assert q.qsize() == 1
    assert q.get() == "/path/new_audio.mp3"


def test_internal_audio_handler_ignore_dup():
    """Test InternalAudioHandler ignores duplicate events."""
    q = queue.Queue()
    handler = core.InternalAudioHandler(q)

    event = MagicMock()
    event.is_directory = False
    event.src_path = "/path/audio.mp3"

    handler.on_created(event)
    handler.on_created(event)  # Duplicate

    assert q.qsize() == 1  # Only one added
