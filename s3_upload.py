"""
S3 Upload Module for ComfyUI RunPod Handler

Provides optional S3 upload functionality for ComfyUI output images.
Requires boto3 and the following environment variables to be configured:
- BUCKET_ENDPOINT_URL: S3 endpoint URL
- BUCKET_ACCESS_KEY_ID: S3 access key ID
- BUCKET_SECRET_ACCESS_KEY: S3 secret access key
- BUCKET_NAME: S3 bucket name (optional, defaults to "comfyui-outputs")
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Try to import boto3, but make it optional
try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not installed. S3 upload functionality will be disabled.")


def is_s3_configured() -> bool:
    """
    Check if S3 is properly configured with all required environment variables.

    Returns:
        bool: True if all required S3 environment variables are set, False otherwise
    """
    if not BOTO3_AVAILABLE:
        return False

    required_vars = [
        "BUCKET_ENDPOINT_URL",
        "BUCKET_ACCESS_KEY_ID",
        "BUCKET_SECRET_ACCESS_KEY"
    ]

    configured = all(os.getenv(var) for var in required_vars)

    if configured:
        logger.info("S3 is configured and available")
    else:
        missing = [var for var in required_vars if not os.getenv(var)]
        logger.info(f"S3 not configured. Missing variables: {', '.join(missing)}")

    return configured


def get_s3_client():
    """
    Create and return an S3 client configured with environment variables.

    Returns:
        boto3.client: Configured S3 client

    Raises:
        ValueError: If S3 is not properly configured
    """
    if not BOTO3_AVAILABLE:
        raise ValueError("boto3 is not installed")

    if not is_s3_configured():
        raise ValueError("S3 is not properly configured")

    endpoint_url = os.getenv("BUCKET_ENDPOINT_URL")
    access_key_id = os.getenv("BUCKET_ACCESS_KEY_ID")
    secret_access_key = os.getenv("BUCKET_SECRET_ACCESS_KEY")

    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
        )
        logger.info(f"S3 client created for endpoint: {endpoint_url}")
        return s3_client
    except Exception as e:
        logger.error(f"Failed to create S3 client: {str(e)}")
        raise


def upload_file_to_s3(
    file_path: str,
    object_name: Optional[str] = None,
    bucket_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a file to S3 and return the public URL.

    Args:
        file_path: Path to the file to upload
        object_name: S3 object name (defaults to filename)
        bucket_name: S3 bucket name (defaults to BUCKET_NAME env var or "comfyui-outputs")

    Returns:
        Dict containing:
            - success: bool
            - url: str (public URL if successful)
            - error: str (error message if failed)
            - object_name: str (S3 object key)

    Raises:
        ValueError: If S3 is not configured or file doesn't exist
    """
    if not os.path.exists(file_path):
        raise ValueError(f"File not found: {file_path}")

    if not is_s3_configured():
        raise ValueError("S3 is not properly configured")

    # Use filename if object_name not specified
    if object_name is None:
        object_name = Path(file_path).name

    # Get bucket name from env or use default
    if bucket_name is None:
        bucket_name = os.getenv("BUCKET_NAME", "comfyui-outputs")

    try:
        s3_client = get_s3_client()

        # Upload the file
        logger.info(f"Uploading {file_path} to s3://{bucket_name}/{object_name}")
        s3_client.upload_file(file_path, bucket_name, object_name)

        # Construct public URL
        endpoint_url = os.getenv("BUCKET_ENDPOINT_URL")
        # Remove trailing slash if present
        endpoint_url = endpoint_url.rstrip('/')

        # Construct URL based on endpoint format
        # Most S3-compatible services use: endpoint_url/bucket_name/object_name
        public_url = f"{endpoint_url}/{bucket_name}/{object_name}"

        logger.info(f"Successfully uploaded to: {public_url}")

        return {
            "success": True,
            "url": public_url,
            "object_name": object_name,
            "bucket_name": bucket_name
        }

    except (ClientError, BotoCoreError) as e:
        error_msg = f"S3 upload error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "object_name": object_name
        }
    except Exception as e:
        error_msg = f"Unexpected error during S3 upload: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "object_name": object_name
        }


def upload_bytes_to_s3(
    file_bytes: bytes,
    object_name: str,
    bucket_name: Optional[str] = None,
    content_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload file bytes to S3 and return the public URL.

    Args:
        file_bytes: File content as bytes
        object_name: S3 object name
        bucket_name: S3 bucket name (defaults to BUCKET_NAME env var or "comfyui-outputs")
        content_type: MIME type of the file (e.g., "image/png")

    Returns:
        Dict containing:
            - success: bool
            - url: str (public URL if successful)
            - error: str (error message if failed)
            - object_name: str (S3 object key)
    """
    if not is_s3_configured():
        raise ValueError("S3 is not properly configured")

    # Get bucket name from env or use default
    if bucket_name is None:
        bucket_name = os.getenv("BUCKET_NAME", "comfyui-outputs")

    try:
        s3_client = get_s3_client()

        # Prepare upload kwargs
        upload_kwargs = {}
        if content_type:
            upload_kwargs['ContentType'] = content_type

        # Upload the bytes
        logger.info(f"Uploading bytes to s3://{bucket_name}/{object_name}")
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_name,
            Body=file_bytes,
            **upload_kwargs
        )

        # Construct public URL
        endpoint_url = os.getenv("BUCKET_ENDPOINT_URL")
        endpoint_url = endpoint_url.rstrip('/')
        public_url = f"{endpoint_url}/{bucket_name}/{object_name}"

        logger.info(f"Successfully uploaded to: {public_url}")

        return {
            "success": True,
            "url": public_url,
            "object_name": object_name,
            "bucket_name": bucket_name
        }

    except (ClientError, BotoCoreError) as e:
        error_msg = f"S3 upload error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "object_name": object_name
        }
    except Exception as e:
        error_msg = f"Unexpected error during S3 upload: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "object_name": object_name
        }
