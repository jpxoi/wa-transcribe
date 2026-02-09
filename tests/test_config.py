import pytest  # noqa: F401
from pathlib import Path
from app import config


def test_whatsapp_path_override():
    """Test that MANUAL_PATH_OVERRIDE takes precedence."""
    assert config.WHATSAPP_INTERNAL_PATH is None or isinstance(
        config.WHATSAPP_INTERNAL_PATH, str
    )


def test_known_models():
    """Test that KNOWN_MODELS list is populated."""
    assert "turbo.pt" in config.KNOWN_MODELS
    assert "tiny.pt" in config.KNOWN_MODELS


def test_get_app_data_dir_windows(mocker):
    mocker.patch("app.config.SYSTEM", "Windows")
    mocker.patch("app.config.HOME_DIR", Path("C:/Users/User"))
    mocker.patch("os.getenv", return_value="C:\\Local")
    mocker.patch("pathlib.Path.mkdir")

    path = config.get_app_data_dir()
    assert str(path) == "C:\\Local\\.wa-transcriber"


def test_get_app_data_dir_darwin(mocker):
    mocker.patch("app.config.SYSTEM", "Darwin")
    mocker.patch("app.config.HOME_DIR", Path("/Users/mock"))
    mocker.patch("pathlib.Path.mkdir")

    path = config.get_app_data_dir()
    assert str(path) == "/Users/mock/.wa-transcriber"


def test_get_app_data_dir_linux(mocker):
    def getenv_sf(key, default=None):
        if key == "XDG_CONFIG_HOME":
            return "/home/user/.config"
        return default

    mocker.patch("app.config.SYSTEM", "Linux")
    mocker.patch("app.config.HOME_DIR", Path("/home/user"))
    mocker.patch("os.getenv", side_effect=getenv_sf)
    mocker.patch("pathlib.Path.mkdir")

    path = config.get_app_data_dir()
    assert str(path) == "/home/user/.wa-transcriber"


def test_load_configuration_defaults(mocker):
    mocker.patch("pathlib.Path.exists", return_value=True)

    mock_open = mocker.mock_open(read_data="{}")
    mocker.patch("builtins.open", mock_open)

    assert config.load_configuration() is True
    assert config.MODEL_SIZE == "turbo"


def test_load_configuration_error(mocker):
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("builtins.open", side_effect=Exception("Read error"))

    assert config.load_configuration() is False


def test_save_configuration(mocker):
    mock_open = mocker.mock_open()
    mocker.patch("builtins.open", mock_open)

    config.save_configuration({"key": "value"})
    mock_open.assert_called_once()


def test_find_default_whatsapp_path_mac(mocker):
    mocker.patch("app.config.SYSTEM", "Darwin")
    mocker.patch("app.config.HOME_DIR", Path("/Users/mock"))
    mocker.patch("pathlib.Path.exists", side_effect=[True, False])

    path = config.find_default_whatsapp_path()
    assert path is not None
    assert "Group Containers" in path


def test_find_default_whatsapp_path_windows(mocker):
    mocker.patch("app.config.SYSTEM", "Windows")
    mocker.patch("os.getenv", return_value="C:\\Users\\User\\AppData\\Local")
    mocker.patch("os.path.exists", side_effect=[True, False])

    path = config.find_default_whatsapp_path()
    assert path is not None
    assert "Packages" in path


def test_detect_whatsapp_path_manual(mocker):
    mocker.patch("app.config.MANUAL_PATH_OVERRIDE", "/manual/path")
    mocker.patch("os.path.exists", return_value=True)

    config.detect_whatsapp_path()
    assert config.WHATSAPP_INTERNAL_PATH == "/manual/path"


def test_show_config_with_disabled_features(mocker, capsys):
    mocker.patch("app.config.SCAN_LOOKBACK_ENABLED", False)
    mocker.patch("app.config.MODEL_CLEANUP_ENABLED", False)
    mocker.patch("app.config.TRANSCRIPTION_LANGUAGE", None)
    mocker.patch("app.config.MANUAL_PATH_OVERRIDE", None)
    mocker.patch("app.config.utils.print_banner")

    config.show_config()

    captured = capsys.readouterr()
    assert "Disabled" in captured.out
    assert "Auto / None" in captured.out


def test_load_configuration_overrides_defaults(mocker):
    mocker.patch("pathlib.Path.exists", return_value=True)

    mock_open = mocker.mock_open(
        read_data='{"MODEL_SIZE": "base", "FILE_READY_TIMEOUT": 20}'
    )
    mocker.patch("builtins.open", mock_open)

    assert config.load_configuration() is True
    assert config.MODEL_SIZE == "base"
    assert config.FILE_READY_TIMEOUT == 20


def test_save_configuration_error(mocker, capsys):
    mocker.patch("builtins.open", side_effect=Exception("Disk full"))

    config.save_configuration({"a": 1})

    captured = capsys.readouterr()
    assert "Error saving config" in captured.out


def test_find_default_whatsapp_path_mac_direct(mocker):
    mocker.patch("app.config.SYSTEM", "Darwin")
    mocker.patch("app.config.HOME_DIR", Path("/Users/mock"))

    # First path missing, second exists
    mocker.patch("pathlib.Path.exists", side_effect=[False, True])

    path = config.find_default_whatsapp_path()
    assert path is not None
    assert path.endswith("WhatsApp/Media")


def test_detect_whatsapp_path_auto_detect(mocker):
    mocker.patch("app.config.MANUAL_PATH_OVERRIDE", None)
    mocker.patch("app.config.find_default_whatsapp_path", return_value="/auto/path")

    config.detect_whatsapp_path()

    assert config.WHATSAPP_INTERNAL_PATH == "/auto/path"
