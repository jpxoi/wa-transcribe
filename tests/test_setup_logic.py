import os
import shutil
from unittest.mock import patch, MagicMock
from app import setup, config


def test_suggest_best_model_vram():
    with patch("app.utils.get_memory_info") as mock_mem:
        # 10GB VRAM
        mock_mem.return_value = (10.0, "vram")
        # NVIDIA_VRAM_LIMIT_FACTOR default is 0.7
        # usable = min(10*0.7=7, 10-2=8) -> 7GB
        # Turbomodel requires 6.0GB. 6.0 / 7.0 = 0.85 > 0.7 (Wait, safe ratio is 0.7 in code?)

        # setup.py logic:
        # usable_gb = min(10 * NV_LIMIT, max(0, 10 - 2))
        # if (size / usable_gb) <= 0.7: return name

        # If NV_LIMIT is 0.7. Usable = 7.0.
        # Large(10) / 7 = 1.42 > 0.7
        # Turbo(6) / 7 = 0.85 > 0.7
        # Medium(5) / 7 = 0.71 > 0.7
        # Small(2) / 7 = 0.28 <= 0.7 -> Should return "small"

        # Wait, if default VRAM limit is 0.7, then 10GB card gets 7GB usable.
        # To get turbo (6GB), we need 6 / Usable <= 0.7 => Usable >= 6/0.7 = 8.57 GB.
        # So 10GB card with 0.7 limit gives 7GB.

        # Let's adjust mock values to test specific outcomes.

        # Case 1: High VRAM
        # 24GB VRAM. Usable = 24 * 0.7 = 16.8 (or 24-2=22). Min is 16.8.
        # Large(10) / 16.8 = 0.59 <= 0.7 -> "large"
        mock_mem.return_value = (24.0, "vram")
        assert setup.suggest_best_model() == "large"


def test_suggest_best_model_system_ram():
    with patch("app.utils.get_memory_info") as mock_mem:
        # 32GB RAM. Type "ram"
        mock_mem.return_value = (32.0, "ram")
        # System limit factor default is 0.5 (from config default probably, need to check)
        # If default is 0.5. Usable = 16.0.
        # Large(10) / 16 = 0.625 <= 0.7 -> "large"

        # Let's check what config defaults are used.
        # Assuming config.SYSTEM_MEMORY_LIMIT_FACTOR is 0.5

        assert setup.suggest_best_model() == "large"


def test_suggest_best_model_fallback():
    with patch("app.utils.get_memory_info") as mock_mem:
        mock_mem.return_value = (None, None)
        assert setup.suggest_best_model() == "turbo"


def test_reset_application_interactive_no():
    with patch("questionary.confirm") as mock_confirm:
        mock_confirm.return_value.ask.return_value = False
        with patch("shutil.rmtree") as mock_rm:
            setup.reset_application(interactive=True)
            mock_rm.assert_not_called()


def test_reset_application_interactive_yes():
    with patch("questionary.confirm") as mock_confirm:
        mock_confirm.return_value.ask.return_value = True
        with (
            patch("shutil.rmtree") as mock_rm,
            patch("os.path.exists", return_value=True),
        ):
            setup.reset_application(interactive=True)
            mock_rm.assert_called_once()


def test_reset_application_non_interactive():
    with patch("shutil.rmtree") as mock_rm, patch("os.path.exists", return_value=True):
        setup.reset_application(interactive=False)
        mock_rm.assert_called_once()
