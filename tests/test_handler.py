"""Tests for handler.py"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json


@pytest.fixture
def sample_workflow():
    """Sample ComfyUI workflow for testing"""
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 12345,
                "steps": 20
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "original prompt"
            }
        }
    }


@pytest.fixture
def sample_overrides():
    """Sample overrides for testing"""
    return [
        {
            "node_id": "6",
            "field": "inputs.text",
            "value": "new prompt"
        },
        {
            "node_id": "3",
            "field": "inputs.seed",
            "value": 42
        }
    ]


class TestApplyOverrides:
    """Tests for apply_overrides function"""

    def test_apply_simple_override(self, sample_workflow, sample_overrides):
        """Test applying simple field overrides"""
        from handler import apply_overrides

        result = apply_overrides(sample_workflow, sample_overrides)

        assert result["6"]["inputs"]["text"] == "new prompt"
        assert result["3"]["inputs"]["seed"] == 42

    def test_original_workflow_unchanged(self, sample_workflow, sample_overrides):
        """Test that original workflow is not mutated"""
        from handler import apply_overrides

        original_text = sample_workflow["6"]["inputs"]["text"]
        apply_overrides(sample_workflow, sample_overrides)

        # Original should be unchanged
        assert sample_workflow["6"]["inputs"]["text"] == original_text

    def test_nonexistent_node_warning(self, sample_workflow, capsys):
        """Test warning when node doesn't exist"""
        from handler import apply_overrides

        overrides = [{"node_id": "999", "field": "inputs.text", "value": "test"}]
        apply_overrides(sample_workflow, overrides)

        captured = capsys.readouterr()
        assert "Warning: Node 999 not found" in captured.out

    def test_nested_field_creation(self, sample_workflow):
        """Test creating nested fields that don't exist"""
        from handler import apply_overrides

        overrides = [{"node_id": "3", "field": "inputs.new.nested", "value": "test"}]
        result = apply_overrides(sample_workflow, overrides)

        assert result["3"]["inputs"]["new"]["nested"] == "test"

    def test_empty_overrides(self, sample_workflow):
        """Test with no overrides"""
        from handler import apply_overrides

        result = apply_overrides(sample_workflow, [])

        assert result == sample_workflow


class TestCheckServer:
    """Tests for check_server function"""

    @patch('handler.requests.get')
    def test_server_available(self, mock_get):
        """Test when server is available"""
        from handler import check_server

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Should not raise exception
        check_server(max_retries=1)

    @patch('handler.requests.get')
    def test_server_unavailable(self, mock_get):
        """Test when server is unavailable"""
        from handler import check_server

        mock_get.side_effect = Exception("Connection refused")

        with pytest.raises(Exception, match="Connection refused"):
            check_server(max_retries=2, delay=0.01)


class TestGetOutputImages:
    """Tests for get_output_images function"""

    def test_extract_images(self):
        """Test extracting images from history"""
        from handler import get_output_images

        history = {
            "outputs": {
                "9": {
                    "images": [
                        {
                            "filename": "test_00001.png",
                            "subfolder": "",
                            "type": "output"
                        }
                    ]
                }
            }
        }

        images = get_output_images(history)

        assert len(images) == 1
        assert images[0]["filename"] == "test_00001.png"
        assert images[0]["node_id"] == "9"

    def test_multiple_nodes_with_images(self):
        """Test extracting images from multiple nodes"""
        from handler import get_output_images

        history = {
            "outputs": {
                "9": {
                    "images": [{"filename": "img1.png", "subfolder": "", "type": "output"}]
                },
                "10": {
                    "images": [{"filename": "img2.png", "subfolder": "", "type": "output"}]
                }
            }
        }

        images = get_output_images(history)

        assert len(images) == 2

    def test_no_images(self):
        """Test when no images in history"""
        from handler import get_output_images

        history = {"outputs": {}}
        images = get_output_images(history)

        assert len(images) == 0


class TestGetImageUrl:
    """Tests for get_image_url function"""

    def test_basic_url_generation(self):
        """Test basic URL generation"""
        from handler import get_image_url

        url = get_image_url("test.png")

        assert "filename=test.png" in url
        assert "/view?" in url

    def test_url_with_subfolder(self):
        """Test URL generation with subfolder"""
        from handler import get_image_url

        url = get_image_url("test.png", subfolder="subfolder", folder_type="temp")

        assert "filename=test.png" in url
        assert "subfolder=subfolder" in url
        assert "type=temp" in url


class TestHandler:
    """Tests for main handler function"""

    @patch('handler.queue_prompt')
    @patch('handler.wait_for_completion')
    @patch('handler.get_output_images')
    def test_successful_workflow_execution(
        self,
        mock_get_images,
        mock_wait,
        mock_queue,
        sample_workflow
    ):
        """Test successful workflow execution"""
        from handler import handler

        mock_queue.return_value = "test-prompt-id"
        mock_wait.return_value = {"status": {"completed": True}}
        mock_get_images.return_value = [
            {"filename": "test.png", "subfolder": "", "type": "output", "node_id": "9"}
        ]

        event = {
            "input": {
                "workflow": sample_workflow,
                "return_images": True
            }
        }

        result = handler(event)

        assert result["status"] == "success"
        assert result["prompt_id"] == "test-prompt-id"
        assert len(result["images"]) == 1

    def test_missing_workflow_field(self):
        """Test error when workflow is missing"""
        from handler import handler

        event = {"input": {}}
        result = handler(event)

        assert "error" in result

    @patch('handler.queue_prompt')
    def test_timeout_error(self, mock_queue, sample_workflow):
        """Test timeout handling"""
        from handler import handler, TimeoutError

        mock_queue.return_value = "test-id"

        with patch('handler.wait_for_completion', side_effect=TimeoutError("Timeout")):
            event = {"input": {"workflow": sample_workflow}}
            result = handler(event)

            assert result["status"] == "timeout"
