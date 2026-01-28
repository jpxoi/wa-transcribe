import pytest  # noqa: F401
import time
import app.maintenance as maintenance


def test_cleanup_unused_models_no_cache(mocker):
    """Test cleanup_unused_models returns early if cache dir doesn't exist."""
    mocker.patch("os.path.exists", return_value=False)

    # Should not raise exception
    maintenance.cleanup_unused_models("turbo")


def test_cleanup_unused_models_deletes_old(mocker):
    """Test cleanup_unused_models deletes old files."""
    mock_files = ["turbo.pt", "old.pt", "other.pt"]

    # 1. Setup Filesystem Mocks
    mocker.patch("os.path.expanduser", return_value="/cache")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.listdir", return_value=mock_files)
    mocker.patch("os.path.join", side_effect=lambda a, b: f"{a}/{b}")
    mock_remove = mocker.patch("os.remove")

    # 2. Patch Configuration
    # We ensure the files are recognized as valid models
    mocker.patch("app.config.KNOWN_MODELS", ["turbo.pt", "old.pt", "other.pt"])

    # 3. Setup Time Logic
    current_time = time.time()
    old_time = current_time - (8 * 24 * 60 * 60)  # 8 days ago
    new_time = current_time - (1 * 24 * 60 * 60)  # 1 day ago

    # 4. Mock os.stat with conditional logic
    def stat_side_effect(path):
        m = mocker.MagicMock()
        # "old.pt" is the only expired file
        if "old.pt" in path:
            m.st_atime = old_time
        else:
            m.st_atime = new_time
        return m

    mocker.patch("os.stat", side_effect=stat_side_effect)

    # 5. Execute
    maintenance.cleanup_unused_models("turbo")

    # 6. Verify
    # 'turbo.pt' is the current model, so it is skipped (logic: filename != keep_filename)
    # 'other.pt' is new, so it is kept
    # 'old.pt' is old, so it is removed
    mock_remove.assert_called_with("/cache/old.pt")
    assert mock_remove.call_count == 1
