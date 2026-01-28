import sys
import pytest
from unittest.mock import patch, MagicMock
from app import health, config


@pytest.fixture
def mock_utils(mocker):
    mocker.patch("app.utils.print_banner")
    mocker.patch("app.utils.get_compute_device", return_value="cuda")
    mocker.patch("app.utils.get_device_name", return_value="NVIDIA GPU")
    mocker.patch("app.utils.get_memory_info", return_value=(24.0, "vram"))
    mocker.patch("app.utils.check_command", return_value=(True, "/usr/bin/ffmpeg"))
    mocker.patch("app.utils.check_import", return_value=True)
    return mocker


def test_run_diagnostics_all_good(mock_utils, capsys):
    with (
        patch("app.config.WHATSAPP_INTERNAL_PATH", "/valid/path"),
        patch("os.path.exists", return_value=True),
        patch("app.config.MODEL_SIZE", "large"),
    ):  # 24GB VRAM -> Large is optimal?
        # 24GB * 0.7 = 16.8 GB usable. Large(10) fits.
        # health.py logic for suggest: "large" is top.
        # So current=large, rec=large.

        health.run_diagnostics()

        captured = capsys.readouterr()
        assert "System is ready!" in captured.out
        assert "You are using the optimal model" in captured.out


def test_run_diagnostics_failures(mock_utils, capsys):
    # Missing ffmpeg
    with (
        patch("app.utils.check_command", return_value=(False, None)),
        patch("sys.exit") as mock_exit,
    ):
        health.run_diagnostics()

        captured = capsys.readouterr()
        assert "FFmpeg" in captured.out
        assert "MISSING" in captured.out
        mock_exit.assert_called_with(1)


def test_run_diagnostics_model_advice_switch_down(mock_utils, capsys):
    # Low VRAM
    with (
        patch("app.utils.get_memory_info", return_value=(4.0, "vram")),
        patch("app.config.MODEL_SIZE", "large"),
        patch("app.config.WHATSAPP_INTERNAL_PATH", "/valid/path"),
        patch("os.path.exists", return_value=True),
    ):
        # 4GB * 0.7 = 2.8 GB usable. Large(10) too big.
        # Tiny(1) fits.

        health.run_diagnostics()

        captured = capsys.readouterr()
        assert "CRITICAL" in captured.out
        assert "Switch to" in captured.out


def test_run_diagnostics_model_advice_switch_up(mock_utils, capsys):
    # High VRAM
    with (
        patch("app.utils.get_memory_info", return_value=(24.0, "vram")),
        patch("app.config.MODEL_SIZE", "tiny"),
        patch("app.config.WHATSAPP_INTERNAL_PATH", "/valid/path"),
        patch("os.path.exists", return_value=True),
    ):
        health.run_diagnostics()

        captured = capsys.readouterr()
        assert "OPTIMIZATION: Your hardware is under-utilized" in captured.out


def test_run_diagnostics_no_memory_info(mock_utils, capsys):
    with (
        patch("app.utils.get_memory_info", return_value=(None, None)),
        patch("app.config.WHATSAPP_INTERNAL_PATH", "/valid/path"),
        patch("os.path.exists", return_value=True),
    ):
        health.run_diagnostics()

        captured = capsys.readouterr()
        assert "Memory Check" in captured.out
        assert "Skipped" in captured.out


def test_run_diagnostics_path_not_found(mock_utils, capsys):
    with (
        patch("app.config.WHATSAPP_INTERNAL_PATH", "/invalid/path"),
        patch("os.path.exists", return_value=False),
        patch("sys.exit") as mock_exit,
    ):
        health.run_diagnostics()

        captured = capsys.readouterr()
        assert "WhatsApp Path" in captured.out
        assert "NOT FOUND" in captured.out
        mock_exit.assert_called_with(1)
