# Copyright (C) 2026 Jean Paul Fernandez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import typer
from typing_extensions import Annotated
from enum import Enum
from app import core, config, utils, health, setup

# Initialize the Typer app
app = typer.Typer(
    help="Automatically transcribe WhatsApp voice notes to your clipboard using OpenAI Whisper.",
    add_completion=False,
)


class LogType(str, Enum):
    app = "app"
    audio = "audio"


@app.command(name="health")
def health_check():
    """Run system diagnostics to verify dependencies and folder access."""
    config.load_configuration()
    config.detect_whatsapp_path()
    health.run_diagnostics()


@app.command(name="config")
def show_config():
    """Shows the current configuration of the application."""
    config.load_configuration()
    config.detect_whatsapp_path()
    config.show_config()


@app.command(name="setup")
def setup_app():
    """Run interactive setup to configure the application."""
    setup.run_interactive_wizard()


@app.command()
def reset(
    force: Annotated[
        bool, typer.Option("--yes", "-y", help="Skip confirmation prompts.")
    ] = False,
):
    """Resets the application by removing all user data and configuration."""
    setup.reset_application(interactive=not force)


@app.command()
def logs(
    log_type: Annotated[
        LogType, typer.Argument(help="Which logs to view: 'app' or 'audio'")
    ],
):
    """Print the last 50 lines of the specified log file."""
    target = "transcribed_audio" if log_type == LogType.audio else "app"
    utils.show_logs(target)


# --- MAIN LOGIC (Renamed to avoid conflict) ---


@app.callback(invoke_without_command=True)
def app_startup(ctx: typer.Context):
    """
    This runs implicitly when the app starts.
    If no specific command (like 'reset') is used, it runs the transcriber.
    """
    # If a subcommand (like 'reset') is being run, stop here.
    if ctx.invoked_subcommand is not None:
        return

    # --- DEFAULT BEHAVIOR (Run Transcriber) ---
    is_configured = config.load_configuration()
    config.detect_whatsapp_path()

    if not is_configured:
        setup.run_interactive_wizard()
        # Reload to ensure variables are updated
        if not config.load_configuration():
            raise typer.Exit(code=1)

    core.run_transcriber()


# --- ENTRY POINT ---


def main():
    """
    This function matches the entry point defined in your setup.py / pyproject.toml.
    It simply tells Typer to run the application.
    """
    app()


if __name__ == "__main__":
    main()
