from app import setup


def test_suggest_best_model_vram(mocker):
    mock_mem = mocker.patch("app.utils.get_memory_info")
    # 24GB VRAM. Usable = 24 * 0.7 = 16.8 (or 24-2=22). Min is 16.8.
    # Large(10) / 16.8 = 0.59 <= 0.7 -> "large"
    mock_mem.return_value = (24.0, "vram")
    assert setup.suggest_best_model() == "large"


def test_suggest_best_model_system_ram(mocker):
    mock_mem = mocker.patch("app.utils.get_memory_info")
    # 32GB RAM. Type "ram"
    mock_mem.return_value = (32.0, "ram")
    assert setup.suggest_best_model() == "large"


def test_suggest_best_model_fallback(mocker):
    mock_mem = mocker.patch("app.utils.get_memory_info")
    mock_mem.return_value = (None, None)
    assert setup.suggest_best_model() == "turbo"


def test_reset_application_interactive_no(mocker):
    mock_confirm = mocker.patch("questionary.confirm")
    mock_confirm.return_value.ask.return_value = False
    mock_rm = mocker.patch("shutil.rmtree")

    setup.reset_application(interactive=True)
    mock_rm.assert_not_called()


def test_reset_application_interactive_yes(mocker):
    mock_confirm = mocker.patch("questionary.confirm")
    mock_confirm.return_value.ask.return_value = True
    mock_rm = mocker.patch("shutil.rmtree")
    mocker.patch("os.path.exists", return_value=True)

    setup.reset_application(interactive=True)
    mock_rm.assert_called_once()


def test_reset_application_non_interactive(mocker):
    mock_rm = mocker.patch("shutil.rmtree")
    mocker.patch("os.path.exists", return_value=True)

    setup.reset_application(interactive=False)
    mock_rm.assert_called_once()


def test_reset_application_non_interactive_no_data(mocker):
    mock_rm = mocker.patch("shutil.rmtree")
    mocker.patch("os.path.exists", return_value=False)

    setup.reset_application(interactive=False)
    mock_rm.assert_not_called()


def test_reset_application_interactive_no_data(mocker):
    mock_confirm = mocker.patch("questionary.confirm")
    mock_confirm.return_value.ask.return_value = False
    mock_rm = mocker.patch("shutil.rmtree")
    mocker.patch("os.path.exists", return_value=False)

    setup.reset_application(interactive=True)
    mock_rm.assert_not_called()


def test_reset_application_exception(mocker):
    mock_rm = mocker.patch("shutil.rmtree")
    mocker.patch("os.path.exists", return_value=True)
    mock_rm.side_effect = Exception("Test exception")

    setup.reset_application(interactive=False)
    mock_rm.assert_called_once()


def test_wizard_happy_path(mocker, capsys):
    # Mock dependencies
    mocker.patch("app.utils.print_banner")
    mocker.patch("app.utils.clear_screen")
    mock_save = mocker.patch("app.config.save_configuration")
    mocker.patch("app.setup.suggest_best_model", return_value="turbo")
    mocker.patch(
        "app.config.find_default_whatsapp_path", return_value="/default/whatsapp"
    )

    # Mock Questionary
    mock_select = mocker.patch("questionary.select")
    mock_text = mocker.patch("questionary.text")
    mock_confirm = mocker.patch("questionary.confirm")
    mocker.patch("questionary.path")

    # Setup Returns for Happy Path
    mock_select.return_value.ask.return_value = "turbo"
    mock_text.return_value.ask.return_value = ""
    mock_confirm.return_value.ask.side_effect = [True, False, True]

    setup.run_interactive_wizard()

    # Assertions
    mock_save.assert_called_once()
    saved_config = mock_save.call_args[0][0]

    assert saved_config["MODEL_SIZE"] == "turbo"
    assert saved_config["TRANSCRIPTION_LANGUAGE"] is None
    assert saved_config["MANUAL_PATH_OVERRIDE"] is None


def test_wizard_manual_path_and_advanced(mocker):
    # Mock dependencies
    mocker.patch("app.utils.print_banner")
    mocker.patch("app.utils.clear_screen")
    mock_save = mocker.patch("app.config.save_configuration")
    mocker.patch("app.setup.suggest_best_model", return_value="turbo")
    mocker.patch("app.config.find_default_whatsapp_path", return_value=None)

    # Mock Questionary
    mock_select = mocker.patch("questionary.select")
    mock_text = mocker.patch("questionary.text")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_path = mocker.patch("questionary.path")

    mock_select.return_value.ask.side_effect = ["small", "0.9", "0.9"]
    mock_text.return_value.ask.side_effect = ["es", "5", "10"]
    mock_path.return_value.ask.return_value = "/manual/path"
    mock_confirm.return_value.ask.side_effect = [True, True, True, True]

    setup.run_interactive_wizard()

    saved_config = mock_save.call_args[0][0]

    assert saved_config["MODEL_SIZE"] == "small"
    assert saved_config["TRANSCRIPTION_LANGUAGE"] == "es"
    assert saved_config["MANUAL_PATH_OVERRIDE"] == "/manual/path"
    assert saved_config["SCAN_LOOKBACK_HOURS"] == 5
    assert saved_config["MODEL_RETENTION_DAYS"] == 10
    assert saved_config["SYSTEM_MEMORY_LIMIT_FACTOR"] == 0.9
