"""Tests for ADF floppy image creation."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from amipython.adf import ADF_SIZE, ADF_USABLE, create_adf
from amipython.errors import BuildError


def _has_xdftool():
    return shutil.which("xdftool") is not None


@pytest.fixture
def fake_binary(tmp_path):
    """Create a small fake Amiga binary for testing."""
    binary = tmp_path / "game"
    binary.write_bytes(b"\x00\x00\x03\xf3" + b"\x00" * 100)  # Hunk header
    return binary


class TestCreateAdfValidation:
    def test_missing_binary(self, tmp_path):
        with pytest.raises(BuildError, match="not found"):
            create_adf(tmp_path / "nonexistent", tmp_path / "out.adf")

    def test_binary_too_large(self, tmp_path):
        big = tmp_path / "big"
        big.write_bytes(b"\x00" * (ADF_USABLE + 1))
        with pytest.raises(BuildError, match="too large"):
            create_adf(big, tmp_path / "out.adf")

    def test_xdftool_not_found(self, fake_binary, tmp_path):
        with patch("shutil.which", return_value=None):
            with pytest.raises(BuildError, match="xdftool not found"):
                create_adf(fake_binary, tmp_path / "out.adf")

    def test_default_label(self, fake_binary, tmp_path):
        """Label defaults to binary stem."""
        assert fake_binary.stem == "game"


@pytest.mark.skipif(not _has_xdftool(), reason="xdftool not available")
class TestCreateAdfIntegration:
    def test_bootable_adf(self, fake_binary, tmp_path):
        output = tmp_path / "game.adf"
        result = create_adf(fake_binary, output, label="TestGame")
        assert result.exists()
        assert result.stat().st_size == ADF_SIZE

        # Verify contents with xdftool list
        proc = subprocess.run(
            ["xdftool", str(result), "list"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0
        assert "Startup-Sequence" in proc.stdout
        assert "game" in proc.stdout

    def test_non_bootable_adf(self, fake_binary, tmp_path):
        output = tmp_path / "game.adf"
        result = create_adf(fake_binary, output, bootable=False)
        assert result.exists()
        assert result.stat().st_size == ADF_SIZE

    def test_custom_label(self, fake_binary, tmp_path):
        output = tmp_path / "game.adf"
        create_adf(fake_binary, output, label="MyGame")
        proc = subprocess.run(
            ["xdftool", str(output), "root", "show"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0
        assert "MyGame" in proc.stdout
