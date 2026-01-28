import pytest  # noqa: F401
import app.transcriber as transcriber


def test_save_to_log(mocker):
    """Test save_to_log appends to file."""
    mocker.patch("os.makedirs")

    # mocker.mock_open is a helper provided by pytest-mock
    mock_file = mocker.patch("builtins.open", mocker.mock_open())

    transcriber.save_to_log("Transcription text", "/path/audio.mp3", "1m 30s", 5.5)

    # Verify file operations
    mock_file.assert_called()
    handle = mock_file()
    handle.write.assert_called()

    # Check the content of the write
    args = handle.write.call_args[0][0]
    assert "Transcription text" in args
    assert "audio.mp3" in args
