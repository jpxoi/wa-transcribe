import pytest
from unittest.mock import patch, MagicMock
from app import setup, config


def test_wizard_happy_path(mocker, capsys):
    # Mock dependencies
    mocker.patch("app.utils.print_banner")
    mocker.patch("app.utils.clear_screen")
    mocker.patch("app.config.save_configuration")
    mocker.patch("app.setup.suggest_best_model", return_value="turbo")
    mocker.patch(
        "app.config.find_default_whatsapp_path", return_value="/default/whatsapp"
    )

    # Mock Questionary
    mock_select = mocker.patch("questionary.select")
    mock_text = mocker.patch("questionary.text")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_path = mocker.patch("questionary.path")

    # Setup Returns for Happy Path
    # 1. Model Size: "turbo" (default)
    mock_select.return_value.ask.return_value = "turbo"

    # 2. Language: "" (empty for auto)
    mock_text.return_value.ask.return_value = ""

    # 3. Path Detected: Confirm Yes
    # 3.1. Advanced Settings: No
    # 3.2. Save: Yes
    mock_confirm.return_value.ask.side_effect = [
        True,  # Is /default/whatsapp correct?
        False,  # Configure advanced?
        True,  # Save?
    ]

    setup.run_interactive_wizard()

    # Assertions
    # Check if save_configuration was called with expected values
    app_config_save = config.save_configuration
    app_config_save.assert_called_once()
    saved_config = app_config_save.call_args[0][0]

    assert saved_config["MODEL_SIZE"] == "turbo"
    assert saved_config["TRANSCRIPTION_LANGUAGE"] is None
    assert saved_config["MANUAL_PATH_OVERRIDE"] is None  # Because we accepted default


def test_wizard_manual_path_and_advanced(mocker):
    # Mock dependencies
    mocker.patch("app.utils.print_banner")
    mocker.patch("app.utils.clear_screen")
    mocker.patch("app.config.save_configuration")
    mocker.patch("app.setup.suggest_best_model", return_value="turbo")
    mocker.patch(
        "app.config.find_default_whatsapp_path", return_value=None
    )  # Not found

    # Mock Questionary
    mock_select = mocker.patch("questionary.select")
    mock_text = mocker.patch("questionary.text")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_path = mocker.patch("questionary.path")

    # Returns
    # 1. Model: "small"
    #    (Later) System Mem: 0.9
    #    (Later) VRAM: 0.9
    mock_select.return_value.ask.side_effect = ["small", "0.9", "0.9"]

    # 2. Language: "es"
    #    (Later) Lookback hours: "5"
    #    (Later) Retention days: "10"
    mock_text.return_value.ask.side_effect = ["es", "5", "10"]

    # 3. Manual Path Entry
    mock_path.return_value.ask.return_value = "/manual/path"

    # 4. Confirms:
    #    Advanced? Yes
    #    Enable Lookback? Yes
    #    Enable Cleanup? Yes
    #    Save? Yes
    mock_confirm.return_value.ask.side_effect = [True, True, True, True]

    setup.run_interactive_wizard()

    app_config_save = config.save_configuration
    saved_config = app_config_save.call_args[0][0]

    assert saved_config["MODEL_SIZE"] == "small"
    assert saved_config["TRANSCRIPTION_LANGUAGE"] == "es"
    assert saved_config["MANUAL_PATH_OVERRIDE"] == "/manual/path"
    assert saved_config["SCAN_LOOKBACK_HOURS"] == 5
    assert saved_config["MODEL_RETENTION_DAYS"] == 10
    assert saved_config["SYSTEM_MEMORY_LIMIT_FACTOR"] == 0.9
