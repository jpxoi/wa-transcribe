import pytest
from app import health


@pytest.fixture
def mock_utils(mocker):
    mocker.patch("app.utils.print_banner")
    mocker.patch("app.utils.get_compute_device", return_value="cuda")
    mocker.patch("app.utils.get_device_name", return_value="NVIDIA GPU")
    mocker.patch("app.utils.get_memory_info", return_value=(24.0, "vram"))
    mocker.patch("app.utils.check_command", return_value=(True, "/usr/bin/ffmpeg"))
    mocker.patch("app.utils.check_import", return_value=True)
    return mocker


def test_draw_bar_0_percent():
    """Test draw_bar with 0%."""
    bar = health.draw_bar(0)
    assert "■" * 0 in bar
    assert "0%" in bar


def test_draw_bar_50_percent():
    """Test draw_bar with 50%."""
    bar = health.draw_bar(50, width=20)
    # 50% of 20 is 10
    assert "■" * 10 in bar
    assert "50%" in bar


def test_draw_bar_100_percent():
    """Test draw_bar with 100%."""
    bar = health.draw_bar(100, width=20)
    assert "■" * 20 in bar
    assert "100%" in bar


def test_suggest_model_none():
    """Test suggest_model with None inputs."""
    model, gb, desc, usage = health.suggest_model(None, None)
    assert model == "base"
    assert gb == 0.0
    assert desc == "Unknown"


def test_suggest_model_vram_low():
    """Test suggest_model with low VRAM."""
    model, gb, desc, usage = health.suggest_model(4.0, "vram")
    assert model == "base"
    assert gb == 2.0


def test_suggest_model_vram_high():
    """Test suggest_model with high VRAM."""
    model, gb, desc, usage = health.suggest_model(24.0, "vram")
    assert model == "large"
    assert gb == pytest.approx(16.8)


def test_suggest_model_system_ram():
    """Test suggest_model with System RAM."""
    model, gb, desc, usage = health.suggest_model(16.0, "system")
    assert model == "medium"
    assert gb == 8.0


def test_run_diagnostics_all_good(mock_utils, capsys, mocker):
    mocker.patch("app.config.WHATSAPP_INTERNAL_PATH", "/valid/path")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("app.config.MODEL_SIZE", "large")  # 24GB VRAM -> Large is optimal?

    # 24GB * 0.7 = 16.8 GB usable. Large(10) fits.
    # health.py logic for suggest: "large" is top.
    # So current=large, rec=large.

    health.run_diagnostics()

    captured = capsys.readouterr()
    assert "System is ready!" in captured.out
    assert "You are using the optimal model" in captured.out


def test_run_diagnostics_failures(mock_utils, capsys, mocker):
    # Missing ffmpeg
    mocker.patch("app.utils.check_command", return_value=(False, None))
    mock_exit = mocker.patch("sys.exit")

    health.run_diagnostics()

    captured = capsys.readouterr()
    assert "FFmpeg" in captured.out
    assert "MISSING" in captured.out
    mock_exit.assert_called_with(1)


def test_run_diagnostics_model_advice_switch_down(mock_utils, capsys, mocker):
    # Low VRAM
    mocker.patch("app.utils.get_memory_info", return_value=(4.0, "vram"))
    mocker.patch("app.config.MODEL_SIZE", "large")
    mocker.patch("app.config.WHATSAPP_INTERNAL_PATH", "/valid/path")
    mocker.patch("os.path.exists", return_value=True)

    # 4GB * 0.7 = 2.8 GB usable. Large(10) too big.
    # Tiny(1) fits.

    health.run_diagnostics()

    captured = capsys.readouterr()
    assert "CRITICAL" in captured.out
    assert "Switch to" in captured.out


def test_run_diagnostics_model_advice_switch_up(mock_utils, capsys, mocker):
    # High VRAM
    mocker.patch("app.utils.get_memory_info", return_value=(24.0, "vram"))
    mocker.patch("app.config.MODEL_SIZE", "tiny")
    mocker.patch("app.config.WHATSAPP_INTERNAL_PATH", "/valid/path")
    mocker.patch("os.path.exists", return_value=True)

    health.run_diagnostics()

    captured = capsys.readouterr()
    assert "OPTIMIZATION: Your hardware is under-utilized" in captured.out


def test_run_diagnostics_no_memory_info(mock_utils, capsys, mocker):
    mocker.patch("app.utils.get_memory_info", return_value=(None, None))
    mocker.patch("app.config.WHATSAPP_INTERNAL_PATH", "/valid/path")
    mocker.patch("os.path.exists", return_value=True)

    health.run_diagnostics()

    captured = capsys.readouterr()
    assert "Memory Check" in captured.out
    assert "Skipped" in captured.out


def test_run_diagnostics_path_not_found(mock_utils, capsys, mocker):
    mocker.patch("app.config.WHATSAPP_INTERNAL_PATH", "/invalid/path")
    mocker.patch("os.path.exists", return_value=False)
    mock_exit = mocker.patch("sys.exit")

    health.run_diagnostics()

    captured = capsys.readouterr()
    assert "WhatsApp Path" in captured.out
    assert "NOT FOUND" in captured.out
    mock_exit.assert_called_with(1)
