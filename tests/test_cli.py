from typer.testing import CliRunner
from unittest.mock import patch
from app.cli import app

runner = CliRunner()


def test_health_command():
    with (
        patch("app.health.run_diagnostics") as mock_health,
        patch("app.config.load_configuration"),
        patch("app.config.detect_whatsapp_path"),
    ):
        result = runner.invoke(app, ["health"])

        assert result.exit_code == 0
        mock_health.assert_called_once()


def test_config_command():
    with (
        patch("app.config.show_config") as mock_show,
        patch("app.config.load_configuration"),
        patch("app.config.detect_whatsapp_path"),
    ):
        result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        mock_show.assert_called_once()


def test_setup_command():
    with patch("app.setup.run_interactive_wizard") as mock_setup:
        result = runner.invoke(app, ["setup"])
        assert result.exit_code == 0
        mock_setup.assert_called_once()


def test_reset_command_interactive():
    # If interactive (default), force false (no yes flag), it might prompt
    # Typer runner input=... helps simulate user input.
    # But reset usually takes --yes to skip.

    with patch("app.setup.reset_application") as mock_reset:
        # We need to simulate "y" or confirm if it asks
        # reset(interactive=True) is called.

        # We simulate user input "y" just in case
        result = runner.invoke(app, ["reset"], input="y\n")

        # If the command successfully runs reset_application
        assert result.exit_code == 0
        mock_reset.assert_called_with(interactive=True)


def test_reset_command_force():
    with patch("app.setup.reset_application") as mock_reset:
        result = runner.invoke(app, ["reset", "--yes"])

        assert result.exit_code == 0
        # When force is True, interactive is False
        mock_reset.assert_called_with(interactive=False)


def test_logs_command_app():
    with patch("app.utils.show_logs") as mock_logs:
        result = runner.invoke(app, ["logs", "app"])
        assert result.exit_code == 0
        mock_logs.assert_called_with("app")


def test_logs_command_audio():
    with patch("app.utils.show_logs") as mock_logs:
        result = runner.invoke(app, ["logs", "audio"])
        assert result.exit_code == 0
        mock_logs.assert_called_with("transcribed_audio")


def test_logs_command_invalid():
    with patch("app.utils.show_logs") as mock_logs:
        result = runner.invoke(app, ["logs", "invalid_type"])
        # Typer validation should fail
        assert result.exit_code != 0
        mock_logs.assert_not_called()


def test_main_invocation_callback():
    """Test that invoking app without commands calls run_transcriber."""
    with (
        patch("app.core.run_transcriber") as mock_run,
        patch("app.config.load_configuration", return_value=True),
        patch("app.config.detect_whatsapp_path"),
    ):
        result = runner.invoke(app)
        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_main_invocation_needs_setup():
    """Test that unconfigured app runs setup then transcriber."""
    # First load_configuration returns False (not configured)
    # Then we run setup
    # Then load_config returns True (configured)
    with (
        patch("app.core.run_transcriber") as mock_run,
        patch("app.config.load_configuration", side_effect=[False, True]),
        patch("app.config.detect_whatsapp_path"),
        patch("app.setup.run_interactive_wizard") as mock_setup,
    ):
        result = runner.invoke(app)

        assert result.exit_code == 0
        mock_setup.assert_called_once()
        mock_run.assert_called_once()
