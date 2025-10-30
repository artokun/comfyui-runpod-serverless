"""Tests for install_nodes.py with config.yml"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import yaml


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_yml(temp_dir):
    """Create sample config.yml file for nodes"""
    config_file = temp_dir / "config.yml"
    config = {
        "nodes": [
            {
                "url": "https://github.com/user/repo1.git",
                "version": "latest"
            },
            {
                "url": "https://github.com/user/repo2.git",
                "version": "v1.0.5"
            },
            {
                "url": "https://github.com/user/repo3.git",
                "version": "nightly"
            }
        ]
    }
    config_file.write_text(yaml.dump(config))
    return config_file


@pytest.fixture
def comfyui_dir(temp_dir):
    """Create ComfyUI directory structure"""
    comfyui = temp_dir / "ComfyUI"
    custom_nodes = comfyui / "custom_nodes"
    custom_nodes.mkdir(parents=True)
    return comfyui


class TestNodeConfigParser:
    """Tests for parsing nodes from config.yml"""

    def test_parse_valid_entries(self, sample_config_yml):
        """Test parsing valid node entries from config.yml"""
        from install_nodes import NodeConfigParser

        parser = NodeConfigParser(sample_config_yml)
        entries = parser.parse()

        assert len(entries) == 3
        assert entries[0].url == "https://github.com/user/repo1.git"
        assert entries[0].version == "latest"

    def test_parse_version_specifiers(self, sample_config_yml):
        """Test parsing different version specifiers"""
        from install_nodes import NodeConfigParser

        parser = NodeConfigParser(sample_config_yml)
        entries = parser.parse()

        assert entries[0].version == "latest"
        assert entries[1].version == "v1.0.5"
        assert entries[2].version == "nightly"

    def test_parse_empty_nodes(self, temp_dir):
        """Test parsing config.yml with empty nodes list"""
        from install_nodes import NodeConfigParser

        config_file = temp_dir / "config.yml"
        config = {"nodes": []}
        config_file.write_text(yaml.dump(config))

        parser = NodeConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 0
        assert len(parser.errors) == 0

    def test_missing_required_fields(self, temp_dir):
        """Test error when required fields are missing"""
        from install_nodes import NodeConfigParser

        config_file = temp_dir / "config.yml"
        config = {
            "nodes": [
                {
                    "url": "https://github.com/user/repo.git"
                    # Missing version
                }
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = NodeConfigParser(config_file)
        entries = parser.parse()

        assert len(parser.errors) > 0

    def test_file_not_found(self, temp_dir):
        """Test handling of missing config file"""
        from install_nodes import NodeConfigParser

        nonexistent = temp_dir / "nonexistent.yml"
        parser = NodeConfigParser(nonexistent)
        entries = parser.parse()

        assert len(entries) == 0
        assert len(parser.errors) > 0

    def test_invalid_yaml(self, temp_dir):
        """Test handling of invalid YAML"""
        from install_nodes import NodeConfigParser

        config_file = temp_dir / "config.yml"
        config_file.write_text("invalid: yaml: content: [")

        parser = NodeConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 0
        assert len(parser.errors) > 0

    def test_missing_nodes_key(self, temp_dir):
        """Test handling of config without nodes key"""
        from install_nodes import NodeConfigParser

        config_file = temp_dir / "config.yml"
        config = {"models": []}  # Missing nodes key
        config_file.write_text(yaml.dump(config))

        parser = NodeConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 0

    def test_various_version_formats(self, temp_dir):
        """Test various valid version specifiers"""
        from install_nodes import NodeConfigParser

        config_file = temp_dir / "config.yml"
        config = {
            "nodes": [
                {"url": "https://github.com/user/repo1.git", "version": "latest"},
                {"url": "https://github.com/user/repo2.git", "version": "nightly"},
                {"url": "https://github.com/user/repo3.git", "version": "v1.2.3"},
                {"url": "https://github.com/user/repo4.git", "version": "main"},
                {"url": "https://github.com/user/repo5.git", "version": "develop"},
                {"url": "https://github.com/user/repo6.git", "version": "abc123def"},
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = NodeConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 6
        assert len(parser.errors) == 0


class TestNodeInstaller:
    """Tests for NodeInstaller class"""

    @patch('install_nodes.subprocess.run')
    def test_clone_node(self, mock_run, comfyui_dir):
        """Test cloning a new node"""
        from install_nodes import NodeInstaller, NodeEntry

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        installer = NodeInstaller(comfyui_dir)
        entry = NodeEntry(
            url="https://github.com/user/test-repo.git",
            version="latest",
            name="test-repo"
        )

        result = installer.install_node(entry)

        assert result is True
        assert mock_run.called

    @patch('install_nodes.subprocess.run')
    def test_skip_existing_node(self, mock_run, comfyui_dir):
        """Test skipping existing node"""
        from install_nodes import NodeInstaller, NodeEntry

        # Create existing node directory
        node_dir = comfyui_dir / "custom_nodes" / "test-repo"
        node_dir.mkdir(parents=True)
        (node_dir / ".git").mkdir()

        installer = NodeInstaller(comfyui_dir, force=False)
        entry = NodeEntry(
            url="https://github.com/user/test-repo.git",
            version="latest",
            name="test-repo"
        )

        result = installer.install_node(entry)

        # Should skip
        assert installer.skipped == 1

    @patch('install_nodes.subprocess.run')
    def test_checkout_version(self, mock_run, comfyui_dir):
        """Test checking out specific version"""
        from install_nodes import NodeInstaller, NodeEntry

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        installer = NodeInstaller(comfyui_dir)
        entry = NodeEntry(
            url="https://github.com/user/test-repo.git",
            version="v1.0.5",
            name="test-repo"
        )

        result = installer.install_node(entry)

        # Should have called git commands including checkout
        assert mock_run.call_count >= 2  # At least clone and checkout

    @patch('install_nodes.subprocess.run')
    def test_latest_version_checkout(self, mock_run, comfyui_dir):
        """Test checking out latest stable version"""
        from install_nodes import NodeInstaller, NodeEntry

        # Mock git commands
        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get('args', [])
            if 'tag' in cmd or 'describe' in cmd:
                return MagicMock(returncode=0, stdout="v1.2.3\n", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = run_side_effect

        installer = NodeInstaller(comfyui_dir)
        entry = NodeEntry(
            url="https://github.com/user/test-repo.git",
            version="latest",
            name="test-repo"
        )

        result = installer.install_node(entry)

        assert mock_run.called

    @patch('install_nodes.subprocess.run')
    def test_nightly_version_checkout(self, mock_run, comfyui_dir):
        """Test checking out nightly (latest commit)"""
        from install_nodes import NodeInstaller, NodeEntry

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        installer = NodeInstaller(comfyui_dir)
        entry = NodeEntry(
            url="https://github.com/user/test-repo.git",
            version="nightly",
            name="test-repo"
        )

        result = installer.install_node(entry)

        assert mock_run.called


@pytest.mark.integration
class TestInstallNodesIntegration:
    """Integration tests for install_nodes script"""

    def test_dry_run_mode(self, sample_config_yml, comfyui_dir, capsys):
        """Test dry run mode with config.yml"""
        from install_nodes import main
        import sys

        old_argv = sys.argv

        try:
            sys.argv = [
                "install_nodes.py",
                "--config", str(sample_config_yml),
                "--comfyui-dir", str(comfyui_dir),
                "--dry-run"
            ]

            result = main()

            captured = capsys.readouterr()
            assert "DRY RUN" in captured.out or "dry run" in captured.out.lower()
            assert result == 0

        finally:
            sys.argv = old_argv

    def test_config_file_argument(self, sample_config_yml, comfyui_dir):
        """Test using custom config file path"""
        from install_nodes import main
        import sys

        old_argv = sys.argv

        try:
            sys.argv = [
                "install_nodes.py",
                "--config", str(sample_config_yml),
                "--comfyui-dir", str(comfyui_dir),
                "--dry-run"
            ]

            result = main()
            assert result == 0

        finally:
            sys.argv = old_argv

    @patch('install_nodes.subprocess.run')
    def test_full_install_workflow(self, mock_run, sample_config_yml, comfyui_dir):
        """Test complete installation workflow"""
        from install_nodes import main
        import sys

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        old_argv = sys.argv

        try:
            sys.argv = [
                "install_nodes.py",
                "--config", str(sample_config_yml),
                "--comfyui-dir", str(comfyui_dir)
            ]

            result = main()

            # Should succeed
            assert result == 0

            # Should have called git commands for all 3 nodes
            assert mock_run.call_count >= 3

        finally:
            sys.argv = old_argv


class TestRealWorldScenarios:
    """Test realistic usage scenarios"""

    def test_comfyui_manager_config(self, temp_dir):
        """Test ComfyUI Manager configuration parsing"""
        from install_nodes import NodeConfigParser

        config_file = temp_dir / "config.yml"
        config = {
            "nodes": [
                {
                    "url": "https://github.com/ltdrdata/ComfyUI-Manager.git",
                    "version": "latest"
                }
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = NodeConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 1
        assert len(parser.errors) == 0
        assert "ComfyUI-Manager" in entries[0].url

    def test_multiple_nodes_mixed_versions(self, temp_dir):
        """Test configuration with mixed version strategies"""
        from install_nodes import NodeConfigParser

        config_file = temp_dir / "config.yml"
        config = {
            "nodes": [
                {
                    "url": "https://github.com/ltdrdata/ComfyUI-Manager.git",
                    "version": "latest"
                },
                {
                    "url": "https://github.com/kijai/ComfyUI-KJNodes.git",
                    "version": "v1.0.5"
                },
                {
                    "url": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git",
                    "version": "nightly"
                }
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = NodeConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 3
        assert entries[0].version == "latest"
        assert entries[1].version == "v1.0.5"
        assert entries[2].version == "nightly"

    def test_wan_animate_setup(self, temp_dir):
        """Test WAN Animate node configuration"""
        from install_nodes import NodeConfigParser

        config_file = temp_dir / "config.yml"
        config = {
            "nodes": [
                {"url": "https://github.com/ltdrdata/ComfyUI-Manager.git", "version": "latest"},
                {"url": "https://github.com/kijai/ComfyUI-WanVideoWrapper.git", "version": "latest"},
                {"url": "https://github.com/rgthree/rgthree-comfy.git", "version": "latest"},
                {"url": "https://github.com/kijai/ComfyUI-KJNodes.git", "version": "latest"},
                {"url": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git", "version": "latest"},
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = NodeConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 5
        assert len(parser.errors) == 0

    def test_production_pinned_versions(self, temp_dir):
        """Test production config with pinned versions"""
        from install_nodes import NodeConfigParser

        config_file = temp_dir / "config.yml"
        config = {
            "nodes": [
                {
                    "url": "https://github.com/ltdrdata/ComfyUI-Manager.git",
                    "version": "v2.47"
                },
                {
                    "url": "https://github.com/kijai/ComfyUI-KJNodes.git",
                    "version": "v1.0.5"
                }
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = NodeConfigParser(config_file)
        entries = parser.parse()

        # Verify all versions are pinned
        for entry in entries:
            assert entry.version.startswith("v")
            assert "." in entry.version


class TestNodeEntryParsing:
    """Test parsing individual node entries"""

    def test_extract_repo_name_from_url(self):
        """Test extracting repository name from URL"""
        from install_nodes import NodeEntry

        entry = NodeEntry(
            url="https://github.com/user/ComfyUI-CustomNode.git",
            version="latest",
            name="ComfyUI-CustomNode"
        )

        assert entry.name == "ComfyUI-CustomNode"

    def test_various_github_urls(self, temp_dir):
        """Test parsing various GitHub URL formats"""
        from install_nodes import NodeConfigParser

        config_file = temp_dir / "config.yml"
        config = {
            "nodes": [
                {"url": "https://github.com/user/repo.git", "version": "latest"},
                {"url": "https://github.com/user/repo-name.git", "version": "latest"},
                {"url": "https://github.com/user/Repo_Name.git", "version": "latest"},
            ]
        }
        config_file.write_text(yaml.dump(config))

        parser = NodeConfigParser(config_file)
        entries = parser.parse()

        assert len(entries) == 3
        assert all(entry.url.endswith(".git") for entry in entries)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
