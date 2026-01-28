import pytest
from unittest.mock import patch, MagicMock
from app import utils, config


def test_format_duration_error():
    assert utils.format_duration("string") == "Unknown duration"
    assert utils.format_duration(-1) == "Unknown duration"


def test_get_device_name(mocker):
    mocker.patch("torch.cuda.is_available", return_value=True)
    mocker.patch("torch.cuda.get_device_name", return_value="RTX 4090")
    assert utils.get_device_name() == "NVIDIA CUDA (RTX 4090)"

    mocker.patch("torch.cuda.is_available", return_value=False)
    mocker.patch("torch.backends.mps.is_available", return_value=True)
    assert utils.get_device_name() == "Apple Silicon (MPS)"

    mocker.patch("torch.backends.mps.is_available", return_value=False)
    assert utils.get_device_name() == "CPU Only"


def test_show_logs_app(mocker, capsys):
    # Mock banner
    mocker.patch("app.utils.print_banner")
    mocker.patch("app.utils.clear_screen")

    # Mock glob
    mock_log_dir = mocker.MagicMock()
    # Need to patch the actual import in utils or the config attribute
    mocker.patch("app.config.APP_LOGS_DIR", mock_log_dir)

    mock_file = mocker.MagicMock()
    mock_file.name = "log_daily.log"
    # mtime
    mocker.patch("os.path.getmtime", return_value=12345)

    # glob returns a list of Paths
    mock_log_dir.glob.return_value = [mock_file]

    # Mock open and file content
    mocker.patch("builtins.open", mocker.mock_open(read_data="Line 1\nLine 2\n"))

    utils.show_logs("app")

    captured = capsys.readouterr()
    assert "Line 1" in captured.out


def test_show_logs_empty(mocker, capsys):
    mocker.patch("app.utils.print_banner")
    mock_log_dir = mocker.MagicMock()
    mocker.patch("app.config.APP_LOGS_DIR", mock_log_dir)
    mock_log_dir.glob.return_value = []

    utils.show_logs("app")
    captured = capsys.readouterr()
    assert "No log files found" in captured.out


def test_show_logs_invalid_type():
    with pytest.raises(ValueError):
        utils.show_logs("invalid")
