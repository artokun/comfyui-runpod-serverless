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
            return True, f"Skipped (exists): {output_file.name}"

        try:
            if self.verbose:
                print(f"  Downloading: {entry.url}")
                print(f"  To: {output_file}")

            # Download with progress
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0 and self.verbose:
                    downloaded = block_num * block_size
                    percent = min(100, (downloaded * 100) / total_size)
                    print(f"\r  Progress: {percent:.1f}%", end='', flush=True)

            urllib.request.urlretrieve(entry.url, output_file, reporthook=progress_hook)

            if self.verbose:
                print()  # New line after progress

            self.downloaded += 1
            return True, f"Downloaded: {output_file.name} ({output_file.stat().st_size / 1024 / 1024:.1f} MB)"

        except Exception as e:
            self.failed += 1
            if entry.optional:
                return True, f"Optional model failed (continuing): {e}"
            return False, f"Failed: {e}"


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
