#!/usr/bin/env python3
"""
ComfyUI Model Downloader
Parses models.txt and downloads models to appropriate directories.

Usage:
    python download_models.py [options]

Options:
    --models-file PATH    Path to models.txt (default: ./models.txt)
    --base-dir PATH       Base models directory (default: ./ComfyUI/models)
    --dry-run             Show what would be downloaded without downloading
    --validate-only       Only validate the models file
    --force               Re-download even if file exists
    --parallel N          Download N files in parallel (default: 1)
    --verbose             Show detailed output
"""

import argparse
import os
import re
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed


# Valid model destination directories in ComfyUI
VALID_DESTINATIONS = {
    "checkpoints",
    "clip",
    "clip_vision",
    "configs",
    "controlnet",
    "diffusion_models",
    "embeddings",
    "loras",
    "upscale_models",
    "vae",
    "sams",
    "detection",
    "text_encoders",
    "unet",
    "style_models",
    "hypernetworks",
}

# Valid model file extensions
VALID_EXTENSIONS = {
    ".safetensors",
    ".ckpt",
    ".pt",
    ".pth",
    ".bin",
    ".onnx",
    ".pb",
    ".yaml",
    ".json",
}


@dataclass
class ModelEntry:
    """Represents a model to download"""
    url: str
    destination: str
    flags: List[str]
    line_number: int
    filename: Optional[str] = None

    @property
    def is_optional(self) -> bool:
        return "/optional" in self.flags or "/skip" in self.flags

    @property
    def destination_path(self) -> Path:
        return Path(self.destination)


class ModelFileParser:
    """Parses models.txt file"""

    # Pattern: URL -> destination [flags]
    ENTRY_PATTERN = re.compile(
        r'^(?P<url>https?://[^\s]+)\s+->\s+(?P<dest>\S+)(?P<flags>(?:\s+/\w+)*)$'
    )

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse(self) -> List[ModelEntry]:
        """Parse the models file and return list of entries"""
        entries = []

        if not self.file_path.exists():
            self.errors.append(f"Models file not found: {self.file_path}")
            return entries

        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Try to parse the entry
                match = self.ENTRY_PATTERN.match(line)
                if not match:
                    self.errors.append(f"Line {line_num}: Invalid format: {line}")
                    continue

                url = match.group('url')
                dest = match.group('dest')
                flags = match.group('flags').split() if match.group('flags') else []

                # Validate destination
                if dest not in VALID_DESTINATIONS:
                    self.errors.append(
                        f"Line {line_num}: Invalid destination '{dest}'. "
                        f"Valid: {', '.join(sorted(VALID_DESTINATIONS))}"
                    )
                    continue

                # Extract filename from URL
                filename = self._extract_filename(url)
                if not filename:
                    self.warnings.append(
                        f"Line {line_num}: Could not extract filename from URL: {url}"
                    )

                # Validate file extension
                if filename:
                    ext = Path(filename).suffix.lower()
                    if ext not in VALID_EXTENSIONS:
                        self.warnings.append(
                            f"Line {line_num}: Unusual file extension '{ext}' for {filename}"
                        )

                entries.append(ModelEntry(
                    url=url,
                    destination=dest,
                    flags=flags,
                    line_number=line_num,
                    filename=filename
                ))

        return entries

    def _extract_filename(self, url: str) -> Optional[str]:
        """Extract filename from URL"""
        # Remove query parameters for analysis
        parsed = urllib.parse.urlparse(url)
        path = parsed.path

        # Get the last part of the path
        filename = Path(path).name

        # If it has a valid extension, return it
        if Path(filename).suffix.lower() in VALID_EXTENSIONS:
            return filename

        # Check if there's a filename in query params (common for HuggingFace)
        if 'download' in parsed.query.lower():
            # Try to extract from path before query
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
        """
        Download a single model entry.
        Returns (success, message)
        """
        dest_dir = self.base_dir / entry.destination
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Determine output filename
        if entry.filename:
            output_file = dest_dir / entry.filename
        else:
            # Generate filename from URL hash if we can't extract it
            url_hash = hashlib.md5(entry.url.encode()).hexdigest()[:8]
            output_file = dest_dir / f"model_{url_hash}.bin"

        # Check if file exists
        if output_file.exists() and not self.force:
            if entry.is_optional:
                return True, f"✓ {output_file.name} (already exists)"
            return True, f"✓ {output_file.name} (already exists, use --force to re-download)"

        # Download the file
        try:
            if self.verbose:
                print(f"  Downloading: {entry.url}")
                print(f"  → {output_file}")

            # Add headers to handle HuggingFace and Civitai
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            req = urllib.request.Request(entry.url, headers=headers)

            with urllib.request.urlopen(req, timeout=30) as response:
                # Check if it's a redirect or download
                if response.geturl() != entry.url and self.verbose:
                    print(f"  Redirected to: {response.geturl()}")

                # Get file size if available
                file_size = int(response.headers.get('Content-Length', 0))

                # Download with progress
                with open(output_file, 'wb') as f:
                    downloaded = 0
                    block_size = 8192

                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break

                        f.write(buffer)
                        downloaded += len(buffer)

                        # Show progress for large files
                        if file_size > 0 and self.verbose:
                            progress = (downloaded / file_size) * 100
                            print(f"\r  Progress: {progress:.1f}%", end='', flush=True)

                    if self.verbose and file_size > 0:
                        print()  # New line after progress

            # Verify the file was created
            if not output_file.exists() or output_file.stat().st_size == 0:
                return False, f"✗ {entry.filename or 'unknown'} (download produced empty file)"

            size_mb = output_file.stat().st_size / (1024 * 1024)
            return True, f"✓ {output_file.name} ({size_mb:.1f} MB)"

        except urllib.error.HTTPError as e:
            if entry.is_optional:
                return True, f"⚠ {entry.filename or 'unknown'} (optional, HTTP {e.code})"
            return False, f"✗ {entry.filename or 'unknown'} (HTTP {e.code}: {e.reason})"

        except urllib.error.URLError as e:
            if entry.is_optional:
                return True, f"⚠ {entry.filename or 'unknown'} (optional, network error)"
            return False, f"✗ {entry.filename or 'unknown'} (network error: {e.reason})"

        except Exception as e:
            if entry.is_optional:
                return True, f"⚠ {entry.filename or 'unknown'} (optional, {type(e).__name__})"
            return False, f"✗ {entry.filename or 'unknown'} (error: {e})"

    def download_all(self, entries: List[ModelEntry], parallel: int = 1) -> Dict[str, int]:
        """Download all model entries"""
        if not entries:
            return {"downloaded": 0, "skipped": 0, "failed": 0}

        print(f"\n{'='*70}")
        print(f"  Downloading {len(entries)} model(s)")
        print(f"{'='*70}\n")

        if parallel > 1:
            # Parallel downloads
            with ThreadPoolExecutor(max_workers=parallel) as executor:
                futures = {
                    executor.submit(self.download_entry, entry): entry
                    for entry in entries
                }

                for future in as_completed(futures):
                    entry = futures[future]
                    success, message = future.result()
                    print(f"  {message}")

                    if success:
                        if "already exists" in message:
                            self.skipped += 1
                        else:
                            self.downloaded += 1
                    else:
                        self.failed += 1
        else:
            # Sequential downloads
            for entry in entries:
                success, message = self.download_entry(entry)
                print(f"  {message}")

                if success:
                    if "already exists" in message:
                        self.skipped += 1
                    else:
                        self.downloaded += 1
                else:
                    self.failed += 1

        print(f"\n{'='*70}")
        print(f"  Summary: {self.downloaded} downloaded, {self.skipped} skipped, {self.failed} failed")
        print(f"{'='*70}\n")

        return {
            "downloaded": self.downloaded,
            "skipped": self.skipped,
            "failed": self.failed
        }


def main():
    parser = argparse.ArgumentParser(
        description="Download ComfyUI models from models.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--models-file",
        type=Path,
        default=Path("models.txt"),
        help="Path to models.txt (default: ./models.txt)"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("./ComfyUI/models"),
        help="Base models directory (default: ./ComfyUI/models)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the models file"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if file exists"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Download N files in parallel (default: 1)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )

    args = parser.parse_args()

    # Parse the models file
    print(f"Parsing models file: {args.models_file}")
    file_parser = ModelFileParser(args.models_file)
    entries = file_parser.parse()

    # Show errors
    if file_parser.errors:
        print(f"\n{'='*70}")
        print(f"  ERRORS ({len(file_parser.errors)})")
        print(f"{'='*70}")
        for error in file_parser.errors:
            print(f"  ✗ {error}")
        print()
        return 1

    # Show warnings
    if file_parser.warnings:
        print(f"\n{'='*70}")
        print(f"  WARNINGS ({len(file_parser.warnings)})")
        print(f"{'='*70}")
        for warning in file_parser.warnings:
            print(f"  ⚠ {warning}")
        print()

    # Show what we found
    if not entries:
        print("\n✓ No models to download (all lines commented out or empty file)")
        return 0

    print(f"\n✓ Found {len(entries)} model(s) to download")

    # Group by destination for display
    by_dest = {}
    for entry in entries:
        by_dest.setdefault(entry.destination, []).append(entry)

    print(f"\nBreakdown by destination:")
    for dest in sorted(by_dest.keys()):
        count = len(by_dest[dest])
        print(f"  • {dest}: {count} model(s)")

    if args.validate_only:
        print("\n✓ Validation complete!")
        return 0

    if args.dry_run:
        print(f"\n{'='*70}")
        print(f"  DRY RUN - Would download to: {args.base_dir}")
        print(f"{'='*70}\n")
        for entry in entries:
            status = "optional" if entry.is_optional else "required"
            print(f"  [{status}] {entry.filename or 'unknown'} -> {entry.destination}")
        print()
        return 0

    # Download models
    downloader = ModelDownloader(args.base_dir, force=args.force, verbose=args.verbose)
    results = downloader.download_all(entries, parallel=args.parallel)

    return 1 if results["failed"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
