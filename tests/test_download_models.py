"""Tests for download_models.py with config.yml"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import yaml


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_yml(temp_dir):
    """Create sample config.yml file for models"""
    config_file = temp_dir / "config.yml"
    config = {
        "models": [
            {
                "url": "https://example.com/model1.safetensors",
                "destination": "checkpoints"
            },
            {
                "url": "https://example.com/model2.safetensors",
                "destination": "vae",
                "optional": True
            },
            {
                "url": "https://example.com/model3.ckpt",
                "destination": "loras"
            }
        ]
    }
    config_file.write_text(yaml.dump(config))
    return config_file


class TestConfigParser:
    """Tests for ConfigParser class"""

    def test_parse_valid_entries(self, sample_config_yml):
        """Test parsing valid model entries from config.yml"""
        from download_models import ConfigParser

        parser = ConfigParser(sample_config_yml)
        entries = parser.parse()

        assert len(entries) == 3
        assert entries[0].url == "https://example.com/model1.safetensors"
        assert entries[0].destination == "checkpoints"
        assert not entries[0].is_optional

    def test_parse_optional_flag(self, sample_config_yml):
        """Test parsing optional flag from config.yml"""
        from download_models import ConfigParser

        parser = ConfigParser(sample_config_yml)
        entries = parser.parse()

        assert entries[1].is_optional
        assert entries[1].destination == "vae"

    def test_parse_empty_models(self, temp_dir):
        """Test parsing config.yml with empty models list"""
        from download_models import ConfigParser

        config_file = temp_dir / "config.yml"
        config = {"models": []}
        config_file.write_text(yaml.dump(config))

        parser = ConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 0
        assert len(parser.errors) == 0

    def test_invalid_destination(self, temp_dir):
        """Test invalid destination error"""
        from download_models import ConfigParser

        config_file = temp_dir / "config.yml"
        config = {
            "models": [
                {
                    "url": "https://example.com/model.safetensors",
                    "destination": "invalid_dest"
                }
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = ConfigParser(config_file)
        entries = parser.parse()

        assert len(parser.errors) > 0
        assert "invalid_dest" in parser.errors[0].lower()

    def test_missing_required_fields(self, temp_dir):
        """Test error when required fields are missing"""
        from download_models import ConfigParser

        config_file = temp_dir / "config.yml"
        config = {
            "models": [
                {
                    "url": "https://example.com/model.safetensors"
                    # Missing destination
                }
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = ConfigParser(config_file)
        entries = parser.parse()

        assert len(parser.errors) > 0

    def test_file_not_found(self, temp_dir):
        """Test handling of missing config file"""
        from download_models import ConfigParser

        nonexistent = temp_dir / "nonexistent.yml"
        parser = ConfigParser(nonexistent)
        entries = parser.parse()

        assert len(entries) == 0
        assert len(parser.errors) > 0

    def test_invalid_yaml(self, temp_dir):
        """Test handling of invalid YAML"""
        from download_models import ConfigParser

        config_file = temp_dir / "config.yml"
        config_file.write_text("invalid: yaml: content: [")

        parser = ConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 0
        assert len(parser.errors) > 0

    def test_missing_models_key(self, temp_dir):
        """Test handling of config without models key"""
        from download_models import ConfigParser

        config_file = temp_dir / "config.yml"
        config = {"nodes": []}  # Missing models key
        config_file.write_text(yaml.dump(config))

        parser = ConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 0

    def test_multiple_valid_destinations(self, temp_dir):
        """Test all valid model destinations"""
        from download_models import ConfigParser

        valid_destinations = [
            "checkpoints", "vae", "loras", "controlnet", "clip_vision",
            "embeddings", "upscale_models"
        ]

        config_file = temp_dir / "config.yml"
        config = {
            "models": [
                {
                    "url": f"https://example.com/model{i}.safetensors",
                    "destination": dest
                }
                for i, dest in enumerate(valid_destinations)
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = ConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == len(valid_destinations)
        assert len(parser.errors) == 0

        for entry, expected_dest in zip(entries, valid_destinations):
            assert entry.destination == expected_dest


class TestModelDownloader:
    """Tests for ModelDownloader class"""

    @patch('download_models.urllib.request.urlretrieve')
    def test_download_model(self, mock_urlretrieve, temp_dir):
        """Test downloading a model"""
        from download_models import ModelDownloader, ModelEntry

        downloader = ModelDownloader(temp_dir)
        entry = ModelEntry(
            url="https://example.com/model.safetensors",
            destination="checkpoints",
            is_optional=False,
            filename="model.safetensors"
        )

        # Mock successful download
        mock_urlretrieve.return_value = ("path", {})

        result = downloader.download_entry(entry)

        assert result is True
        mock_urlretrieve.assert_called_once()

    def test_skip_existing_file(self, temp_dir):
        """Test skipping existing files"""
        from download_models import ModelDownloader, ModelEntry

        # Create existing file
        checkpoints_dir = temp_dir / "checkpoints"
        checkpoints_dir.mkdir()
        (checkpoints_dir / "model.safetensors").write_text("existing")

        downloader = ModelDownloader(temp_dir, force=False)
        entry = ModelEntry(
            url="https://example.com/model.safetensors",
            destination="checkpoints",
            is_optional=False,
            filename="model.safetensors"
        )

        result = downloader.download_entry(entry)

        # Should skip without downloading
        assert downloader.skipped == 1

    @patch('download_models.urllib.request.urlretrieve')
    def test_force_redownload(self, mock_urlretrieve, temp_dir):
        """Test forcing redownload of existing files"""
        from download_models import ModelDownloader, ModelEntry

        # Create existing file
        checkpoints_dir = temp_dir / "checkpoints"
        checkpoints_dir.mkdir()
        (checkpoints_dir / "model.safetensors").write_text("existing")

        downloader = ModelDownloader(temp_dir, force=True)
        entry = ModelEntry(
            url="https://example.com/model.safetensors",
            destination="checkpoints",
            is_optional=False,
            filename="model.safetensors"
        )

        mock_urlretrieve.return_value = ("path", {})

        result = downloader.download_entry(entry)

        # Should download despite existing file
        mock_urlretrieve.assert_called_once()

    @patch('download_models.urllib.request.urlretrieve')
    def test_optional_model_failure(self, mock_urlretrieve, temp_dir):
        """Test that optional model failures don't stop processing"""
        from download_models import ModelDownloader, ModelEntry

        downloader = ModelDownloader(temp_dir)
        entry = ModelEntry(
            url="https://example.com/model.safetensors",
            destination="checkpoints",
            is_optional=True,
            filename="model.safetensors"
        )

        # Mock failed download
        mock_urlretrieve.side_effect = Exception("Download failed")

        result = downloader.download_entry(entry)

        # Should return True for optional models even on failure
        assert result is True
        assert downloader.failed == 0  # Optional failures don't count as failures


@pytest.mark.integration
class TestDownloadModelsIntegration:
    """Integration tests for download_models script"""

    def test_dry_run_mode(self, sample_config_yml, temp_dir, capsys):
        """Test dry run mode with config.yml"""
        from download_models import main
        import sys

        # Backup argv
        old_argv = sys.argv

        try:
            sys.argv = [
                "download_models.py",
                "--config", str(sample_config_yml),
                "--base-dir", str(temp_dir),
                "--dry-run"
            ]

            result = main()

            captured = capsys.readouterr()
            assert "DRY RUN" in captured.out or "dry run" in captured.out.lower()
            assert result == 0

        finally:
            sys.argv = old_argv

    def test_config_file_argument(self, sample_config_yml, temp_dir):
        """Test using custom config file path"""
        from download_models import main
        import sys

        old_argv = sys.argv

        try:
            sys.argv = [
                "download_models.py",
                "--config", str(sample_config_yml),
                "--base-dir", str(temp_dir),
                "--dry-run"
            ]

            result = main()
            assert result == 0

        finally:
            sys.argv = old_argv

    @patch('download_models.urllib.request.urlretrieve')
    def test_full_download_workflow(self, mock_urlretrieve, sample_config_yml, temp_dir):
        """Test complete download workflow"""
        from download_models import main
        import sys

        mock_urlretrieve.return_value = ("path", {})

        old_argv = sys.argv

        try:
            sys.argv = [
                "download_models.py",
                "--config", str(sample_config_yml),
                "--base-dir", str(temp_dir)
            ]

            result = main()

            # Should succeed
            assert result == 0

            # Should have called download 3 times (one for each model)
            assert mock_urlretrieve.call_count == 3

        finally:
            sys.argv = old_argv


class TestRealWorldScenarios:
    """Test realistic usage scenarios"""

    def test_sdxl_config(self, temp_dir):
        """Test SDXL configuration parsing"""
        from download_models import ConfigParser

        config_file = temp_dir / "config.yml"
        config = {
            "models": [
                {
                    "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
                    "destination": "checkpoints"
                },
                {
                    "url": "https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors",
                    "destination": "vae"
                }
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = ConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 2
        assert len(parser.errors) == 0
        assert entries[0].destination == "checkpoints"
        assert entries[1].destination == "vae"

    def test_mixed_optional_required(self, temp_dir):
        """Test mix of optional and required models"""
        from download_models import ConfigParser

        config_file = temp_dir / "config.yml"
        config = {
            "models": [
                {
                    "url": "https://example.com/required.safetensors",
                    "destination": "checkpoints"
                },
                {
                    "url": "https://example.com/optional.safetensors",
                    "destination": "loras",
                    "optional": True
                }
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = ConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 2
        assert not entries[0].is_optional
        assert entries[1].is_optional


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
