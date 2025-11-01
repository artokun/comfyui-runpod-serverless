#!/usr/bin/env python3
"""
ComfyUI Model Downloader
Parses config.yml and downloads models to appropriate directories.

Usage:
    python download_models.py [options]

Options:
    --config PATH         Path to config.yml (default: ./config.yml)
    --base-dir PATH       Base models directory (default: ./ComfyUI/models)
    --dry-run             Show what would be downloaded without downloading
    --validate-only       Only validate the config file
    --force               Re-download even if file exists
    --parallel N          Download N files in parallel (default: 1)
    --verbose             Show detailed output
"""

import argparse
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("Error: PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None

try:
    from huggingface_hub import hf_hub_download
    import re
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False
    hf_hub_download = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


# Valid model destination directories in ComfyUI
VALID_DESTINATIONS = {
    "checkpoints", "clip", "clip_vision", "configs", "controlnet",
    "diffusion_models", "embeddings", "loras", "upscale_models", "vae",
    "sams", "detection", "text_encoders", "unet", "style_models", "hypernetworks",
}

# Valid model file extensions
VALID_EXTENSIONS = {
    ".safetensors", ".ckpt", ".pt", ".pth", ".bin",
    ".onnx", ".pb", ".yaml", ".json",
}


def parse_huggingface_url(url: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse HuggingFace URL to extract repo_id, revision, and filename.

    Args:
        url: HuggingFace URL like https://huggingface.co/Aitrepreneur/FLX/resolve/main/clip_vision_h.safetensors

    Returns:
        Tuple of (repo_id, revision, filename) or None if not a valid HF URL

    Examples:
        >>> parse_huggingface_url("https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors")
        ('runwayml/stable-diffusion-v1-5', 'main', 'v1-5-pruned-emaonly.safetensors')
    """
    if not HF_HUB_AVAILABLE:
        return None

    # Pattern: https://huggingface.co/{user}/{repo}/resolve/{revision}/{filename}
    pattern = r'https://huggingface\.co/([^/]+/[^/]+)/resolve/([^/]+)/(.+?)(?:\?.*)?$'
    match = re.match(pattern, url)

    if match:
        repo_id, revision, filename = match.groups()
        return repo_id, revision, filename

    return None


def parallel_download(url: str, output_file: Path, num_threads: int = 8, verbose: bool = False) -> bool:
    """
    Download file using parallel chunk downloads with byte-range requests.

    Args:
        url: URL to download from
        output_file: Path to save file to
        num_threads: Number of parallel download threads (default: 8)
        verbose: Show detailed progress

    Returns:
        True if successful, False otherwise
    """
    if not REQUESTS_AVAILABLE:
        return False

    try:
        # Get file size with HEAD request
        response = requests.head(url, allow_redirects=True, timeout=10)

        # Check if server supports range requests
        if 'Accept-Ranges' not in response.headers or response.headers['Accept-Ranges'] == 'none':
            if verbose:
                print(f"  Server doesn't support range requests, falling back to single-threaded")
            return False

        file_size = int(response.headers.get('Content-Length', 0))
        if file_size == 0:
            if verbose:
                print(f"  Could not determine file size, falling back to single-threaded")
            return False

        if verbose:
            print(f"  File size: {file_size / 1024 / 1024:.1f} MB")
            print(f"  Using {num_threads} parallel connections")

        # Calculate chunk size
        chunk_size = file_size // num_threads

        # Create temporary directory for chunks
        temp_dir = output_file.parent / f".{output_file.name}.chunks"
        temp_dir.mkdir(exist_ok=True)

        def download_chunk(chunk_id: int, start_byte: int, end_byte: int) -> bool:
            """Download a single chunk"""
            chunk_file = temp_dir / f"chunk_{chunk_id}"
            headers = {'Range': f'bytes={start_byte}-{end_byte}'}

            try:
                response = requests.get(url, headers=headers, stream=True, timeout=30)
                response.raise_for_status()

                with open(chunk_file, 'wb') as f:
                    for data in response.iter_content(chunk_size=8192):
                        f.write(data)

                return True
            except Exception as e:
                if verbose:
                    print(f"  Chunk {chunk_id} failed: {e}")
                return False

        # Download chunks in parallel
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_threads):
                start_byte = i * chunk_size
                end_byte = start_byte + chunk_size - 1 if i < num_threads - 1 else file_size - 1
                futures.append(executor.submit(download_chunk, i, start_byte, end_byte))

            # Wait for all chunks with progress
            completed = 0
            if TQDM_AVAILABLE:
                with tqdm(total=num_threads, desc="  Downloading chunks", unit="chunk") as pbar:
                    for future in as_completed(futures):
                        if not future.result():
                            # Cleanup and return False if any chunk fails
                            import shutil
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            return False
                        completed += 1
                        pbar.update(1)
            else:
                for future in as_completed(futures):
                    if not future.result():
                        import shutil
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        return False
                    completed += 1
                    if verbose and completed % 2 == 0:
                        print(f"  Downloaded {completed}/{num_threads} chunks")

        # Combine chunks into final file
        if verbose:
            print(f"  Combining chunks...")

        with open(output_file, 'wb') as outfile:
            for i in range(num_threads):
                chunk_file = temp_dir / f"chunk_{i}"
                with open(chunk_file, 'rb') as infile:
                    outfile.write(infile.read())

        # Cleanup temp directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

        if verbose:
            print(f"  Parallel download complete!")

        return True

    except Exception as e:
        if verbose:
            print(f"  Parallel download failed: {e}")
        return False


@dataclass
class ModelEntry:
    """Represents a model to download"""
    url: str
    destination: str
    optional: bool = False
    filename: Optional[str] = None
    source_line: int = 0

    @property
    def destination_path(self) -> Path:
        return Path(self.destination)


class ConfigParser:
    """Parses config.yml file"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse(self) -> List[ModelEntry]:
        """Parse the config file and return list of model entries"""
        if not self.file_path.exists():
            self.errors.append(f"Config file not found: {self.file_path}")
            return []

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error: {e}")
            return []

        if not config:
            self.warnings.append("Config file is empty")
            return []

        models_config = config.get('models', [])
        if not isinstance(models_config, list):
            self.errors.append("'models' section must be a list")
            return []

        entries = []
        for idx, model in enumerate(models_config, 1):
            if not isinstance(model, dict):
                self.warnings.append(f"Model entry {idx} is not a dictionary, skipping")
                continue

            url = model.get('url')
            destination = model.get('destination')
            optional = model.get('optional', False)

            if not url:
                self.warnings.append(f"Model entry {idx} missing 'url', skipping")
                continue

            if not destination:
                self.warnings.append(f"Model entry {idx} missing 'destination', skipping")
                continue

            # Validate destination
            if destination not in VALID_DESTINATIONS:
                self.errors.append(
                    f"Model entry {idx}: Invalid destination '{destination}'. "
                    f"Valid: {', '.join(sorted(VALID_DESTINATIONS))}"
                )
                continue

            # Extract filename
            filename = self._extract_filename(url)
            if not filename:
                self.warnings.append(f"Model entry {idx}: Could not extract filename from URL: {url}")

            # Validate extension
            if filename:
                ext = Path(filename).suffix.lower()
                if ext not in VALID_EXTENSIONS:
                    self.warnings.append(f"Model entry {idx}: Unusual file extension '{ext}' for {filename}")

            entries.append(ModelEntry(
                url=url,
                destination=destination,
                optional=optional,
                filename=filename,
                source_line=idx
            ))

        return entries

    def _extract_filename(self, url: str) -> Optional[str]:
        """Extract filename from URL"""
        parsed = urllib.parse.urlparse(url)
        path = parsed.path

        filename = Path(path).name

        if Path(filename).suffix.lower() in VALID_EXTENSIONS:
            return filename

        if 'download' in parsed.query.lower():
            if Path(path).suffix.lower() in VALID_EXTENSIONS:
                return Path(path).name

        return None


class ModelDownloader:
    """Downloads models with progress reporting"""

    def __init__(self, base_dir: Path, force: bool = False, verbose: bool = False):
        self.base_dir = base_dir
        self.force = force
        self.verbose = verbose
        self.downloaded = 0
        self.skipped = 0
        self.failed = 0

    def download_entry(self, entry: ModelEntry) -> Tuple[bool, str]:
        """Download a single model entry. Returns (success, message)"""
        dest_dir = self.base_dir / entry.destination
        dest_dir.mkdir(parents=True, exist_ok=True)

        if entry.filename:
            output_file = dest_dir / entry.filename
        else:
            output_file = dest_dir / f"model_{hashlib.md5(entry.url.encode()).hexdigest()[:8]}"

        # Check if exists
        if output_file.exists() and not self.force:
            self.skipped += 1
            return True, f"✓ Skipped (exists): {output_file.name}"

        # Show progress before starting
        print(f"  📥 Downloading {output_file.name}...", flush=True)

        try:
            if self.verbose:
                print(f"  URL: {entry.url}")
                print(f"  To: {output_file}")

            # Try HuggingFace fast download first (uses hf_transfer for 3-5x speed)
            hf_parsed = parse_huggingface_url(entry.url)
            if hf_parsed and HF_HUB_AVAILABLE:
                repo_id, revision, filename = hf_parsed
                print(f"  Using HuggingFace Hub (hf_transfer enabled for fast download)")
                print(f"  Repo: {repo_id}, File: {filename}")

                # Download using hf_hub_download (automatic hf_transfer acceleration)
                try:
                    downloaded_path = hf_hub_download(
                        repo_id=repo_id,
                        revision=revision,
                        filename=filename,
                        cache_dir=None,  # Use default HF cache
                        local_dir=str(dest_dir)
                    )

                    # Verify the file was downloaded to the expected location
                    if Path(downloaded_path).exists():
                        # If downloaded to a different location, move it
                        if Path(downloaded_path) != output_file:
                            import shutil
                            shutil.move(downloaded_path, output_file)

                        self.downloaded += 1
                        file_size = output_file.stat().st_size / 1024 / 1024
                        return True, f"Downloaded (HF): {output_file.name} ({file_size:.1f} MB)"
                    else:
                        raise FileNotFoundError(f"Downloaded file not found: {downloaded_path}")

                except Exception as hf_error:
                    # Fall back to parallel download if HF download fails
                    print(f"  HF download failed ({hf_error}), trying parallel download...")

            # Try parallel chunk download (fast for servers supporting range requests)
            if REQUESTS_AVAILABLE:
                print(f"  Attempting parallel chunk download...")
                parallel_success = parallel_download(
                    url=entry.url,
                    output_file=output_file,
                    num_threads=8,
                    verbose=self.verbose
                )

                if parallel_success:
                    self.downloaded += 1
                    file_size = output_file.stat().st_size / 1024 / 1024
                    return True, f"Downloaded (Parallel): {output_file.name} ({file_size:.1f} MB)"
                else:
                    print(f"  Parallel download not supported, falling back to single-threaded...")

            # Fallback: Standard urllib download (slower, single-threaded)
            if TQDM_AVAILABLE:
                # Use tqdm for progress bar
                with tqdm(
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    miniters=1,
                    desc=f"  {output_file.name[:40]}",
                    disable=False
                ) as progress_bar:
                    def progress_hook(block_num, block_size, total_size):
                        if total_size > 0:
                            if progress_bar.total != total_size:
                                progress_bar.total = total_size
                            downloaded = block_num * block_size
                            progress_bar.update(block_size if block_num > 0 else 0)

                    urllib.request.urlretrieve(entry.url, output_file, reporthook=progress_hook)
            else:
                # Fallback to simple percentage display
                def progress_hook(block_num, block_size, total_size):
                    if total_size > 0:
                        downloaded = block_num * block_size
                        percent = min(100, (downloaded * 100) / total_size)
                        if block_num % 50 == 0:  # Print every 50 blocks to reduce spam
                            print(f"  {output_file.name[:40]}: {percent:.1f}%")

                urllib.request.urlretrieve(entry.url, output_file, reporthook=progress_hook)
                print(f"  {output_file.name}: 100%")

            self.downloaded += 1
            file_size_mb = output_file.stat().st_size / 1024 / 1024
            return True, f"Downloaded: {output_file.name} ({file_size_mb:.1f} MB)"

        except Exception as e:
            self.failed += 1
            error_msg = str(e)[:200]  # Truncate long errors
            if entry.optional:
                return True, f"⚠️ DOWNLOAD FAILED (optional, continuing): {output_file.name} - {error_msg}"
            return False, f"❌ DOWNLOAD FAILED: {output_file.name} - {error_msg}"


def main():
    parser = argparse.ArgumentParser(description='Download ComfyUI models from config.yml')
    parser.add_argument('--config', type=Path, default=Path('config.yml'),
                        help='Path to config.yml (default: ./config.yml)')
    parser.add_argument('--base-dir', type=Path, default=Path('./ComfyUI/models'),
                        help='Base models directory (default: ./ComfyUI/models)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be downloaded')
    parser.add_argument('--validate-only', action='store_true',
                        help='Only validate the config file')
    parser.add_argument('--force', action='store_true',
                        help='Re-download even if file exists')
    parser.add_argument('--parallel', type=int, default=1,
                        help='Number of parallel downloads')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed output')

    args = parser.parse_args()

    # Parse configuration
    print(f"\n{'='*60}")
    print(f"ComfyUI Model Downloader")
    print(f"{'='*60}")
    print(f"Config file: {args.config}")
    print(f"Base directory: {args.base_dir}")
    print(f"{'='*60}\n")

    parser_obj = ConfigParser(args.config)
    entries = parser_obj.parse()

    # Show errors and warnings
    if parser_obj.errors:
        print("Errors:")
        for error in parser_obj.errors:
            print(f"  ❌ {error}")
        print()

    if parser_obj.warnings:
        print("Warnings:")
        for warning in parser_obj.warnings:
            print(f"  ⚠️  {warning}")
        print()

    if parser_obj.errors:
        print("❌ Validation failed. Fix errors and try again.")
        return 1

    if not entries:
        print("No models to download (all commented out or empty config)")
        return 0

    print(f"Found {len(entries)} model(s) to process\n")

    if args.validate_only:
        print("✅ Validation successful!")
        return 0

    if args.dry_run:
        print("DRY RUN - No files will be downloaded\n")
        for entry in entries:
            status = "[OPTIONAL]" if entry.optional else "[REQUIRED]"
            print(f"{status} {entry.url}")
            print(f"    → {args.base_dir / entry.destination / (entry.filename or 'unknown')}")
        return 0

    # Download models
    downloader = ModelDownloader(args.base_dir, args.force, args.verbose)

    if args.parallel > 1:
        with ThreadPoolExecutor(max_workers=args.parallel) as executor:
            futures = {executor.submit(downloader.download_entry, entry): entry
                       for entry in entries}

            for future in as_completed(futures):
                entry = futures[future]
                success, message = future.result()
                print(f"  {'✓' if success else '✗'} {message}")
    else:
        for entry in entries:
            success, message = downloader.download_entry(entry)
            print(f"  {'✓' if success else '✗'} {message}")

    # Summary
    print(f"\n{'='*60}")
    print(f"Download Summary")
    print(f"{'='*60}")
    print(f"Downloaded: {downloader.downloaded}")
    print(f"Skipped: {downloader.skipped}")
    print(f"Failed: {downloader.failed}")
    print(f"{'='*60}\n")

    return 0 if downloader.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
