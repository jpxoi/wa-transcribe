import pytest
import sqlite3
from contextlib import contextmanager
import app.db as db

# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_db_connection(mocker):
    """
    Creates an in-memory SQLite database and mocks the app.db.get_db_connection
    context manager using the pytest-mock 'mocker' fixture.
    """
    # 1. Create in-memory DB
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # 2. Define the replacement Context Manager
    @contextmanager
    def mock_ctx_manager():
        yield conn

    # 3. Patch using mocker (Auto-cleanup is handled by pytest)
    mocker.patch("app.db.get_db_connection", side_effect=mock_ctx_manager)

    yield conn

    conn.close()


# -----------------------------------------------------------------------------
# TESTS (Using mocker)
# -----------------------------------------------------------------------------


def test_init_db(mock_db_connection, mocker):
    """Ensure tables are created correctly."""
    # Setup mocks inline - clearer than decorators
    mocker.patch("os.chmod")
    mocker.patch("os.path.exists", return_value=True)

    db.init_db()

    cursor = mock_db_connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='processed_files';"
    )
    assert cursor.fetchone() is not None


def test_add_and_check_processed_file(mock_db_connection, mocker):
    # We patch init_db dependencies just to run the init
    mocker.patch("os.chmod")
    mocker.patch("os.path.exists", return_value=True)
    db.init_db()

    filename = "test_audio.mp3"
    filepath = "/tmp/test_audio.mp3"

    assert db.is_file_processed(filename) is False
    db.add_processed_file(filename, filepath)
    assert db.is_file_processed(filename) is True


def test_get_all_processed_filenames(mock_db_connection, mocker):
    mocker.patch("os.chmod")
    mocker.patch("os.path.exists", return_value=True)
    db.init_db()

    db.add_processed_file("file1.mp3", "/path/1")
    db.add_processed_file("file2.mp3", "/path/2")

    processed = db.get_all_processed_filenames()

    assert len(processed) == 2
    assert "file1.mp3" in processed


def test_migrate_from_logs(mock_db_connection, mocker):
    """Test parsing of log files into database records."""
    mocker.patch("os.chmod")
    db.init_db()

    # 1. Setup Mocks
    # Notice how we don't need to pass these as arguments to the function anymore
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.listdir", return_value=["2023-01-01_daily.log"])

    # 2. Mock File Content
    mock_file_handle = mocker.MagicMock()
    mock_file_handle.__enter__.return_value = [
        "Ignored Header Line",
        "valid_file_1.mp3 | ⏳ 1m 20s | ⏱ done in 5.0s",
        "  valid_file_2.wav  | ⏳ 0m 30s | ⏱ done in 2.0s",
    ]
    mocker.patch("builtins.open", return_value=mock_file_handle)

    # 3. Run Migration
    db.migrate_from_logs()

    # 4. Verify Results
    processed = db.get_all_processed_filenames()
    assert "valid_file_1.mp3" in processed
    assert "valid_file_2.wav" in processed


def test_get_db_connection_closes_connection(mocker):
    mock_conn = mocker.MagicMock()
    mocker.patch("sqlite3.connect", return_value=mock_conn)

    with db.get_db_connection() as conn:
        assert conn is mock_conn

    mock_conn.close.assert_called_once()


def test_init_db_chmod_os_error(mock_db_connection, mocker, capsys):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.chmod", side_effect=OSError("Permission denied"))

    db.init_db()

    captured = capsys.readouterr()
    assert "Could not set secure permissions on DB" in captured.out


def test_is_file_processed_sqlite_error(mocker, capsys):
    mocker.patch(
        "app.db.get_db_connection",
        side_effect=sqlite3.Error("DB failure"),
    )

    result = db.is_file_processed("file.mp3")

    assert result is False
    captured = capsys.readouterr()
    assert "Failed to check file" in captured.out


def test_add_processed_file_sqlite_error(mocker, capsys):
    mocker.patch(
        "app.db.get_db_connection",
        side_effect=sqlite3.Error("Insert failed"),
    )

    db.add_processed_file("file.mp3", "/tmp/file.mp3")

    captured = capsys.readouterr()
    assert "Failed to mark file as processed" in captured.out


def test_get_all_processed_filenames_sqlite_error(mocker, capsys):
    mocker.patch(
        "app.db.get_db_connection",
        side_effect=sqlite3.Error("Select failed"),
    )

    result = db.get_all_processed_filenames()

    assert result == set()
    captured = capsys.readouterr()
    assert "Failed to fetch processed filenames" in captured.out


def test_migrate_from_logs_no_log_dir(mocker):
    mocker.patch("os.path.exists", return_value=False)

    # Should simply return without error
    db.migrate_from_logs()


def test_migrate_from_logs_db_already_has_data(mock_db_connection, mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.listdir", return_value=["dummy.log"])
    mocker.patch("os.chmod")

    # Initialize schema
    db.init_db()

    # Seed DB with one record
    mock_db_connection.execute(
        "INSERT INTO processed_files (filename) VALUES ('existing.mp3')"
    )
    mock_db_connection.commit()

    db.migrate_from_logs()

    # Nothing new should be added
    rows = mock_db_connection.execute(
        "SELECT COUNT(*) FROM processed_files"
    ).fetchone()[0]

    assert rows == 1


def test_migrate_from_logs_log_file_os_error(mock_db_connection, mocker, capsys):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.listdir", return_value=["bad_daily.log"])
    mocker.patch("os.chmod")

    # Initialize schema so migration proceeds
    db.init_db()

    # Force log file open to fail
    mocker.patch("builtins.open", side_effect=OSError("Cannot open"))

    db.migrate_from_logs()

    captured = capsys.readouterr()
    assert "Could not read log file" in captured.out
