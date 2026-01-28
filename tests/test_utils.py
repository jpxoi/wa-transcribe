from unittest.mock import patch, mock_open
import app.utils as utils


def test_check_command_exists():
    """Test check_command returns True and path when command exists."""
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        exists, path = utils.check_command("ffmpeg")
        assert exists is True
        assert path == "/usr/bin/ffmpeg"


def test_check_command_not_exists():
    """Test check_command returns False and None when command does not exist."""
    with patch("shutil.which", return_value=None):
        exists, path = utils.check_command("unknown_command")
        assert exists is False
        assert path is None


def test_check_import_exists():
    """Test check_import returns True when module is installed."""
    with patch("importlib.util.find_spec", return_value=True):
        assert utils.check_import("os") is True


def test_check_import_not_exists():
    """Test check_import returns False when module is not installed."""
    with patch("importlib.util.find_spec", return_value=None):
        assert utils.check_import("nonexistent_module") is False


def test_get_compute_device_cuda():
    """Test get_compute_device priority: CUDA > MPS > CPU."""
    with patch("torch.cuda.is_available", return_value=True):
        assert utils.get_compute_device() == "cuda"


def test_get_compute_device_mps():
    """Test get_compute_device priority: MPS if no CUDA."""
    with (
        patch("torch.cuda.is_available", return_value=False),
        patch("torch.backends.mps.is_available", return_value=True),
    ):
        assert utils.get_compute_device() == "mps"


def test_get_compute_device_cpu():
    """Test get_compute_device fallback to CPU."""
    with (
        patch("torch.cuda.is_available", return_value=False),
        patch("torch.backends.mps.is_available", return_value=False),
    ):
        assert utils.get_compute_device() == "cpu"


def test_get_memory_info_cuda():
    """Test get_memory_info for CUDA."""
    with (
        patch("torch.cuda.is_available", return_value=True),
        patch("torch.cuda.get_device_properties") as mock_props,
    ):
        mock_props.return_value.total_memory = 8 * 1024**3  # 8 GB
        total_gb, mem_type = utils.get_memory_info()
        assert total_gb == 8.0
        assert mem_type == "vram"


def test_get_memory_info_mac():
    """Test get_memory_info for macOS (Unified Memory)."""
    with (
        patch("torch.cuda.is_available", return_value=False),
        patch("platform.system", return_value="Darwin"),
        patch("subprocess.check_output", return_value=b"17179869184"),
    ):  # 16 GB
        total_gb, mem_type = utils.get_memory_info()
        assert total_gb == 16.0
        assert mem_type == "unified"


def test_get_memory_info_linux():
    """Test get_memory_info for Linux (System RAM)."""
    mock_meminfo = "MemTotal:       16384000 kB\n"
    with (
        patch("torch.cuda.is_available", return_value=False),
        patch("platform.system", return_value="Linux"),
        patch("builtins.open", mock_open(read_data=mock_meminfo)),
    ):
        total_gb, mem_type = utils.get_memory_info()
        # 16384000 KB / 1024 / 1024 = 15.625 GB
        assert abs(total_gb - 15.625) < 0.01
        assert mem_type == "system"


def test_get_memory_info_unknown():
    """Test get_memory_info returns None, None for unknown/error."""
    with (
        patch("torch.cuda.is_available", return_value=False),
        patch("platform.system", return_value="Unknown"),
    ):
        total_gb, mem_type = utils.get_memory_info()
        assert total_gb is None
        assert mem_type is None
