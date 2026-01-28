import pytest
from app import utils


@pytest.mark.parametrize(
    "os_name, expected_call",
    [
        ("nt", ("title Test Title",)),
        ("posix", ("\x1b]2;Test Title\x07",)),
    ],
)
def test_set_window_title(mocker, os_name, expected_call):
    mocker.patch("app.utils.os.name", os_name)

    mock_run = mocker.patch("app.utils.subprocess.run")
    mock_write = mocker.patch("app.utils.sys.stdout.write")

    utils.set_window_title("Test Title")

    if os_name == "nt":
        mock_run.assert_called_once_with("title Test Title", shell=True)
        mock_write.assert_not_called()
    else:
        mock_write.assert_called_once_with("\x1b]2;Test Title\x07")
        mock_run.assert_not_called()


def test_format_duration_error():
    # Type checking ignores passed for running the code logic test
    # The actual code handles exceptions
    assert utils.format_duration("string") == "Unknown duration"  # type: ignore
    assert utils.format_duration(-1) == "Unknown duration"


def test_check_command_exists(mocker):
    """Test check_command returns True and path when command exists."""
    mocker.patch("shutil.which", return_value="/usr/bin/ffmpeg")

    exists, path = utils.check_command("ffmpeg")
    assert exists is True
    assert path == "/usr/bin/ffmpeg"


def test_check_command_not_exists(mocker):
    """Test check_command returns False and None when command does not exist."""
    mocker.patch("shutil.which", return_value=None)

    exists, path = utils.check_command("unknown_command")
    assert exists is False
    assert path is None


def test_check_import_exists(mocker):
    """Test check_import returns True when module is installed."""
    mocker.patch("importlib.util.find_spec", return_value=True)
    assert utils.check_import("os") is True


def test_check_import_not_exists(mocker):
    """Test check_import returns False when module is not installed."""
    mocker.patch("importlib.util.find_spec", return_value=None)
    assert utils.check_import("nonexistent_module") is False


def test_get_compute_device_cuda(mocker):
    """Test get_compute_device priority: CUDA > MPS > CPU."""
    mocker.patch("torch.cuda.is_available", return_value=True)
    assert utils.get_compute_device() == "cuda"


def test_get_compute_device_mps(mocker):
    """Test get_compute_device priority: MPS if no CUDA."""
    mocker.patch("torch.cuda.is_available", return_value=False)
    mocker.patch("torch.backends.mps.is_available", return_value=True)

    assert utils.get_compute_device() == "mps"


def test_get_compute_device_cpu(mocker):
    """Test get_compute_device fallback to CPU."""
    mocker.patch("torch.cuda.is_available", return_value=False)
    mocker.patch("torch.backends.mps.is_available", return_value=False)

    assert utils.get_compute_device() == "cpu"


def test_get_memory_info_cuda(mocker):
    """Test get_memory_info for CUDA."""
    mocker.patch("torch.cuda.is_available", return_value=True)

    # Mock property access on the return value
    mock_props = mocker.patch("torch.cuda.get_device_properties")
    mock_props.return_value.total_memory = 8 * 1024**3  # 8 GB

    total_gb, mem_type = utils.get_memory_info()
    assert total_gb == 8.0
    assert mem_type == "vram"


def test_get_memory_info_mac(mocker):
    """Test get_memory_info for macOS (Unified Memory)."""
    mocker.patch("torch.cuda.is_available", return_value=False)
    mocker.patch("platform.system", return_value="Darwin")

    # sysctl returns bytes (16 GB)
    mocker.patch("subprocess.check_output", return_value=b"17179869184")

    total_gb, mem_type = utils.get_memory_info()
    assert total_gb == 16.0
    assert mem_type == "unified"


def test_get_memory_info_linux(mocker):
    """Test get_memory_info for Linux (System RAM)."""
    mocker.patch("torch.cuda.is_available", return_value=False)
    mocker.patch("platform.system", return_value="Linux")

    # Mock /proc/meminfo content
    mock_meminfo = "MemTotal:       16384000 kB\n"
    mocker.patch("builtins.open", mocker.mock_open(read_data=mock_meminfo))

    total_gb, mem_type = utils.get_memory_info()

    assert total_gb is not None, "Memory info should not be None"
    # 16384000 KB / 1024 / 1024 = 15.625 GB
    assert abs(total_gb - 15.625) < 0.01
    assert mem_type == "system"


def test_get_memory_info_unknown(mocker):
    """Test get_memory_info returns None, None for unknown/error."""
    mocker.patch("torch.cuda.is_available", return_value=False)
    mocker.patch("platform.system", return_value="Unknown")

    total_gb, mem_type = utils.get_memory_info()
    assert total_gb is None
    assert mem_type is None


def test_get_memory_info_exception(mocker):
    """Test get_memory_info returns None, None for unknown/error."""
    mocker.patch("torch.cuda.is_available", return_value=True)
    mocker.patch("torch.cuda.get_device_properties", side_effect=Exception)

    total_gb, mem_type = utils.get_memory_info()
    assert total_gb is None
    assert mem_type is None


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


def test_show_logs_transcribed_audio(mocker, capsys):
    # Mock banner
    mocker.patch("app.utils.print_banner")
    mocker.patch("app.utils.clear_screen")

    # Mock glob
    mock_log_dir = mocker.MagicMock()
    mocker.patch("app.config.TRANSCRIBED_AUDIO_LOGS_DIR", mock_log_dir)

    mock_file = mocker.MagicMock()
    mock_file.name = "log_daily.log"
    # mtime
    mocker.patch("os.path.getmtime", return_value=12345)

    # glob returns a list of Paths
    mock_log_dir.glob.return_value = [mock_file]

    # Mock open and file content
    mocker.patch("builtins.open", mocker.mock_open(read_data="Line 1\nLine 2\n"))

    utils.show_logs("transcribed_audio")

    captured = capsys.readouterr()
    assert "Line 1" in captured.out


def test_show_logs_app_folder_no_logs(mocker, capsys):
    mocker.patch("app.utils.print_banner")
    mock_log_dir = mocker.MagicMock()
    mocker.patch("app.config.APP_LOGS_DIR", mock_log_dir)
    mock_log_dir.glob.return_value = []

    utils.show_logs("app")
    captured = capsys.readouterr()
    assert "No log files found" in captured.out


def test_show_logs_transcribed_audio_folder_no_logs(mocker, capsys):
    mocker.patch("app.utils.print_banner")
    mock_log_dir = mocker.MagicMock()
    mocker.patch("app.config.TRANSCRIBED_AUDIO_LOGS_DIR", mock_log_dir)
    mock_log_dir.glob.return_value = []

    utils.show_logs("transcribed_audio")
    captured = capsys.readouterr()
    assert "No log files found" in captured.out


def test_show_logs_app_folder_empty_file(mocker, capsys):
    mocker.patch("app.utils.print_banner")
    mock_log_dir = mocker.MagicMock()
    mocker.patch("app.config.APP_LOGS_DIR", mock_log_dir)
    mock_file = mocker.MagicMock()
    mock_file.name = "log_daily.log"
    mocker.patch("os.path.getmtime", return_value=12345)
    mock_log_dir.glob.return_value = [mock_file]
    mocker.patch("builtins.open", mocker.mock_open(read_data=""))
    utils.show_logs("app")
    captured = capsys.readouterr()
    assert "(Log file is empty)" in captured.out


def test_show_logs_transcribed_audio_folder_empty_file(mocker, capsys):
    mocker.patch("app.utils.print_banner")
    mock_log_dir = mocker.MagicMock()
    mocker.patch("app.config.TRANSCRIBED_AUDIO_LOGS_DIR", mock_log_dir)
    mock_file = mocker.MagicMock()
    mock_file.name = "log_daily.log"
    mocker.patch("os.path.getmtime", return_value=12345)
    mock_log_dir.glob.return_value = [mock_file]
    mocker.patch("builtins.open", mocker.mock_open(read_data=""))
    utils.show_logs("transcribed_audio")
    captured = capsys.readouterr()
    assert "(Log file is empty)" in captured.out


def test_show_logs_invalid_type():
    with pytest.raises(ValueError):
        utils.show_logs("invalid")  # type: ignore


def test_show_logs_app_file_read_exception(mocker, capsys):
    mocker.patch("app.utils.print_banner")
    mock_log_dir = mocker.MagicMock()
    mocker.patch("app.config.APP_LOGS_DIR", mock_log_dir)
    mock_file = mocker.MagicMock()
    mock_file.name = "log_daily.log"
    mock_log_dir.glob.return_value = [mock_file]
    mocker.patch("os.path.getmtime", return_value=12345)
    mocker.patch(
        "builtins.open",
        side_effect=OSError("Permission denied"),
    )

    utils.show_logs("app")

    captured = capsys.readouterr()
    assert "Error reading log file" in captured.out
    assert "Permission denied" in captured.out
