from typer.testing import CliRunner
from app.cli import app

runner = CliRunner()


def test_health_command(mocker):
    mock_health = mocker.patch("app.health.run_diagnostics")
    mocker.patch("app.config.load_configuration")
    mocker.patch("app.config.detect_whatsapp_path")

    result = runner.invoke(app, ["health"])

    assert result.exit_code == 0
    mock_health.assert_called_once()


def test_config_command(mocker):
    mock_show = mocker.patch("app.config.show_config")
    mocker.patch("app.config.load_configuration")
    mocker.patch("app.config.detect_whatsapp_path")

    result = runner.invoke(app, ["config"])

    assert result.exit_code == 0
    mock_show.assert_called_once()


def test_setup_command(mocker):
    mock_setup = mocker.patch("app.setup.run_interactive_wizard")

    result = runner.invoke(app, ["setup"])

    assert result.exit_code == 0
    mock_setup.assert_called_once()


def test_reset_command_interactive(mocker):
    mock_reset = mocker.patch("app.setup.reset_application")

    result = runner.invoke(app, ["reset"], input="y\n")

    assert result.exit_code == 0
    mock_reset.assert_called_with(interactive=True)


def test_reset_command_force(mocker):
    mock_reset = mocker.patch("app.setup.reset_application")

    result = runner.invoke(app, ["reset", "--yes"])

    assert result.exit_code == 0
    mock_reset.assert_called_with(interactive=False)


def test_logs_command_app(mocker):
    mock_logs = mocker.patch("app.utils.show_logs")

    result = runner.invoke(app, ["logs", "app"])

    assert result.exit_code == 0
    mock_logs.assert_called_with("app")


def test_logs_command_audio(mocker):
    mock_logs = mocker.patch("app.utils.show_logs")

    result = runner.invoke(app, ["logs", "audio"])

    assert result.exit_code == 0
    mock_logs.assert_called_with("transcribed_audio")


def test_logs_command_invalid(mocker):
    mock_logs = mocker.patch("app.utils.show_logs")

    result = runner.invoke(app, ["logs", "invalid_type"])

    assert result.exit_code != 0
    mock_logs.assert_not_called()


def test_main_invocation_callback(mocker):
    """Invoking app without commands runs the transcriber."""
    mock_run = mocker.patch("app.core.run_transcriber")
    mocker.patch("app.config.load_configuration", return_value=True)
    mocker.patch("app.config.detect_whatsapp_path")

    result = runner.invoke(app)

    assert result.exit_code == 0
    mock_run.assert_called_once()


def test_main_invocation_needs_setup(mocker):
    """Unconfigured app runs setup, then transcriber."""
    mock_run = mocker.patch("app.core.run_transcriber")
    mock_setup = mocker.patch("app.setup.run_interactive_wizard")

    mocker.patch(
        "app.config.load_configuration",
        side_effect=[False, True],
    )
    mocker.patch("app.config.detect_whatsapp_path")

    result = runner.invoke(app)

    assert result.exit_code == 0
    mock_setup.assert_called_once()
    mock_run.assert_called_once()


def test_main_invocation_load_config_exception(mocker):
    """Test main invocation handles load_configuration exceptions."""
    mock_run = mocker.patch("app.core.run_transcriber")
    mock_setup = mocker.patch("app.setup.run_interactive_wizard")

    mocker.patch(
        "app.config.load_configuration",
        side_effect=Exception("Config error"),
    )
    mocker.patch("app.config.detect_whatsapp_path")

    result = runner.invoke(app)

    assert result.exit_code != 0
    mock_setup.assert_not_called()
    mock_run.assert_not_called()


def test_main_invocation_detect_whatsapp_exception(mocker):
    """Test main invocation handles detect_whatsapp_path exceptions."""
    mock_run = mocker.patch("app.core.run_transcriber")
    mock_setup = mocker.patch("app.setup.run_interactive_wizard")

    mocker.patch(
        "app.config.load_configuration",
        return_value=True,
    )
    mocker.patch(
        "app.config.detect_whatsapp_path",
        side_effect=Exception("Detect error"),
    )

    result = runner.invoke(app)

    assert result.exit_code != 0
    mock_setup.assert_not_called()
    mock_run.assert_not_called()


def test_main_invocation_setup_exception(mocker):
    """Test main invocation handles setup exceptions."""
    mock_run = mocker.patch("app.core.run_transcriber")
    mock_setup = mocker.patch("app.setup.run_interactive_wizard")

    mocker.patch(
        "app.config.load_configuration",
        side_effect=[False, False],
    )
    mocker.patch("app.config.detect_whatsapp_path")

    result = runner.invoke(app)

    assert result.exit_code != 0
    mock_setup.assert_called_once()
    mock_run.assert_not_called()


def test_main_invocation_run_transcriber_exception(mocker):
    """Test main invocation handles run_transcriber exceptions."""
    mock_run = mocker.patch("app.core.run_transcriber")
    mock_setup = mocker.patch("app.setup.run_interactive_wizard")

    mocker.patch(
        "app.config.load_configuration",
        return_value=True,
    )
    mocker.patch("app.config.detect_whatsapp_path")
    mock_run.side_effect = Exception("Run error")

    result = runner.invoke(app)

    assert result.exit_code != 0
    mock_setup.assert_not_called()
    mock_run.assert_called_once()
