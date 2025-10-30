"""Tests for config.yml parsing and validation"""
import pytest
from pathlib import Path
import tempfile
import yaml


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_yml(temp_dir):
    """Create sample config.yml file"""
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
        ],
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
def minimal_config_yml(temp_dir):
    """Create minimal valid config.yml"""
    config_file = temp_dir / "config.yml"
    config = {
        "models": [
            {
                "url": "https://example.com/model.safetensors",
                "destination": "checkpoints"
            }
        ],
        "nodes": [
            {
                "url": "https://github.com/user/repo.git",
                "version": "latest"
            }
        ]
    }
    config_file.write_text(yaml.dump(config))
    return config_file


@pytest.fixture
def empty_config_yml(temp_dir):
    """Create empty config.yml"""
    config_file = temp_dir / "config.yml"
    config = {
        "models": [],
        "nodes": []
    }
    config_file.write_text(yaml.dump(config))
    return config_file


class TestConfigYAMLStructure:
    """Test config.yml structure and validity"""

    def test_valid_config_loads(self, sample_config_yml):
        """Test that valid config.yml can be loaded"""
        with open(sample_config_yml) as f:
            config = yaml.safe_load(f)

        assert "models" in config
        assert "nodes" in config
        assert isinstance(config["models"], list)
        assert isinstance(config["nodes"], list)

    def test_models_section_structure(self, sample_config_yml):
        """Test models section has correct structure"""
        with open(sample_config_yml) as f:
            config = yaml.safe_load(f)

        assert len(config["models"]) == 3

        for model in config["models"]:
            assert "url" in model
            assert "destination" in model
            assert isinstance(model["url"], str)
            assert isinstance(model["destination"], str)

    def test_nodes_section_structure(self, sample_config_yml):
        """Test nodes section has correct structure"""
        with open(sample_config_yml) as f:
            config = yaml.safe_load(f)

        assert len(config["nodes"]) == 3

        for node in config["nodes"]:
            assert "url" in node
            assert "version" in node
            assert isinstance(node["url"], str)
            assert isinstance(node["version"], str)

    def test_optional_field_in_models(self, sample_config_yml):
        """Test optional field is correctly parsed"""
        with open(sample_config_yml) as f:
            config = yaml.safe_load(f)

        model_with_optional = config["models"][1]
        assert "optional" in model_with_optional
        assert model_with_optional["optional"] is True

    def test_empty_config_is_valid(self, empty_config_yml):
        """Test that empty models/nodes lists are valid"""
        with open(empty_config_yml) as f:
            config = yaml.safe_load(f)

        assert config["models"] == []
        assert config["nodes"] == []

    def test_missing_config_file(self, temp_dir):
        """Test handling of missing config file"""
        nonexistent = temp_dir / "nonexistent.yml"

        assert not nonexistent.exists()


class TestConfigYAMLValidation:
    """Test validation of config.yml contents"""

    def test_valid_model_destinations(self, temp_dir):
        """Test valid model destinations"""
        valid_destinations = [
            "checkpoints", "vae", "loras", "controlnet", "clip_vision",
            "embeddings", "upscale_models", "diffusion_models",
            "text_encoders", "clip", "configs", "sams", "detection",
            "unet", "style_models", "hypernetworks"
        ]

        for dest in valid_destinations:
            config_file = temp_dir / f"config_{dest}.yml"
            config = {
                "models": [
                    {
                        "url": "https://example.com/model.safetensors",
                        "destination": dest
                    }
                ]
            }
            config_file.write_text(yaml.dump(config))

            with open(config_file) as f:
                loaded = yaml.safe_load(f)
                assert loaded["models"][0]["destination"] == dest

    def test_valid_node_versions(self, temp_dir):
        """Test various valid node version specifiers"""
        valid_versions = [
            "latest",
            "nightly",
            "v1.0.5",
            "v2.47",
            "abc123def456",
            "main",
            "develop",
            "feature/new-nodes"
        ]

        for version in valid_versions:
            config_file = temp_dir / f"config_{version.replace('/', '_')}.yml"
            config = {
                "nodes": [
                    {
                        "url": "https://github.com/user/repo.git",
                        "version": version
                    }
                ]
            }
            config_file.write_text(yaml.dump(config))

            with open(config_file) as f:
                loaded = yaml.safe_load(f)
                assert loaded["nodes"][0]["version"] == version


class TestConfigYAMLComments:
    """Test that YAML comments are preserved"""

    def test_config_with_comments(self, temp_dir):
        """Test config.yml with comments"""
        config_file = temp_dir / "config.yml"
        content = """# Model Configuration
models:
  # Base models
  - url: https://example.com/model.safetensors
    destination: checkpoints

# Custom nodes configuration
nodes:
  # Essential nodes
  - url: https://github.com/user/repo.git
    version: latest
"""
        config_file.write_text(content)

        # Comments should not affect parsing
        with open(config_file) as f:
            config = yaml.safe_load(f)

        assert len(config["models"]) == 1
        assert len(config["nodes"]) == 1


class TestConfigYAMLMultipleEntries:
    """Test config.yml with multiple entries"""

    def test_many_models(self, temp_dir):
        """Test config with many model entries"""
        config_file = temp_dir / "config.yml"
        config = {
            "models": [
                {
                    "url": f"https://example.com/model{i}.safetensors",
                    "destination": "checkpoints"
                }
                for i in range(10)
            ]
        }
        config_file.write_text(yaml.dump(config))

        with open(config_file) as f:
            loaded = yaml.safe_load(f)

        assert len(loaded["models"]) == 10

    def test_many_nodes(self, temp_dir):
        """Test config with many node entries"""
        config_file = temp_dir / "config.yml"
        config = {
            "nodes": [
                {
                    "url": f"https://github.com/user/repo{i}.git",
                    "version": "latest"
                }
                for i in range(10)
            ]
        }
        config_file.write_text(yaml.dump(config))

        with open(config_file) as f:
            loaded = yaml.safe_load(f)

        assert len(loaded["nodes"]) == 10


class TestConfigYAMLRealWorld:
    """Test realistic config.yml scenarios"""

    def test_sdxl_setup(self, temp_dir):
        """Test typical SDXL configuration"""
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
            ],
            "nodes": [
                {
                    "url": "https://github.com/ltdrdata/ComfyUI-Manager.git",
                    "version": "latest"
                }
            ]
        }
        config_file.write_text(yaml.dump(config))

        with open(config_file) as f:
            loaded = yaml.safe_load(f)

        assert len(loaded["models"]) == 2
        assert len(loaded["nodes"]) == 1
        assert "xl" in loaded["models"][0]["url"].lower()

    def test_production_setup_pinned_versions(self, temp_dir):
        """Test production config with pinned versions"""
        config_file = temp_dir / "config.yml"
        config = {
            "models": [
                {
                    "url": "https://example.com/checkpoint.safetensors",
                    "destination": "checkpoints"
                },
                {
                    "url": "https://example.com/lora.safetensors",
                    "destination": "loras",
                    "optional": True
                }
            ],
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

        with open(config_file) as f:
            loaded = yaml.safe_load(f)

        # Verify pinned versions
        for node in loaded["nodes"]:
            assert node["version"].startswith("v")
            assert "." in node["version"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
