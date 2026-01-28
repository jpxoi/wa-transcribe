import os
import io
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from app import config

# Helper to mock Path properly if needed, but we can relies on patching return values
# of where these paths are constructed if possible.


def test_get_app_data_dir_windows():
    with (
        patch("app.config.SYSTEM", "Windows"),
        patch("app.config.HOME_DIR", Path("C:/Users/User")),
        patch("os.getenv", return_value="C:\\Local"),
        patch("pathlib.Path.mkdir"),
    ):
        path = config.get_app_data_dir()
        # On Windows it uses os.getenv for LOCALAPPDATA, effectively ignoring HOME_DIR
        # path is C:\Local\wa-transcriber
        assert str(path) == os.path.join("C:\\Local", "wa-transcriber")


def test_get_app_data_dir_darwin():
    with (
        patch("app.config.SYSTEM", "Darwin"),
        patch("app.config.HOME_DIR", Path("/Users/mock")),
        patch("pathlib.Path.mkdir"),
    ):
        path = config.get_app_data_dir()
        # Darwin logic: HOME_DIR / "Library" / "Application Support"
        assert str(path) == "/Users/mock/Library/Application Support/wa-transcriber"


def test_get_app_data_dir_linux():
    # Linux uses XDG_CONFIG_HOME or HOME_DIR/.config

    # helper for side_effect
    def getenv_sf(key, default=None):
        if key == "XDG_CONFIG_HOME":
            return "/home/user/.config"
        return default

    with (
        patch("app.config.SYSTEM", "Linux"),
        patch("app.config.HOME_DIR", Path("/home/user")),
        patch("os.getenv", side_effect=getenv_sf),
        patch("pathlib.Path.mkdir"),
    ):
        path = config.get_app_data_dir()
        assert str(path) == "/home/user/.config/wa-transcriber"


def test_load_configuration_defaults():
    # Patch exists to True, open returns empty json -> defaults
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("builtins.open", new_callable=MagicMock) as mock_open,
    ):
        mock_file = io.StringIO("{}")
        mock_file.close = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # We need to ensure globals are reset or updated.
        assert config.load_configuration() is True
        # Check defaults
        assert config.MODEL_SIZE == "turbo"


def test_load_configuration_error():
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("builtins.open", side_effect=Exception("Read error")),
    ):
        assert config.load_configuration() is False


def test_save_configuration():
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        config.save_configuration({"key": "value"})
        mock_open.assert_called_once()


def test_find_default_whatsapp_path_mac():
    # Patch SYSTEM to Darwin
    # Ensure HOME_DIR is used in find_default_whatsapp_path

    with (
        patch("app.config.SYSTEM", "Darwin"),
        patch("app.config.HOME_DIR", Path("/Users/mock")),
        patch("pathlib.Path.exists", side_effect=[True, False]),
    ):  # first path exists
        path = config.find_default_whatsapp_path()
        assert path is not None
        assert "Group Containers" in path


def test_find_default_whatsapp_path_windows():
    # On Windows it mostly uses os.getenv
    with (
        patch("app.config.SYSTEM", "Windows"),
        patch("os.getenv", return_value="C:\\Users\\User\\AppData\\Local"),
        patch("os.path.exists", side_effect=[True, False]),
    ):
        path = config.find_default_whatsapp_path()
        assert path is not None
        assert "Packages" in path


def test_detect_whatsapp_path_manual():
    with (
        patch("app.config.MANUAL_PATH_OVERRIDE", "/manual/path"),
        patch("os.path.exists", return_value=True),
    ):
        config.detect_whatsapp_path()
        assert config.WHATSAPP_INTERNAL_PATH == "/manual/path"
