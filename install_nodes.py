#!/usr/bin/env python3
"""
ComfyUI Custom Nodes Installer
Parses nodes.txt and installs custom nodes with version control.

Usage:
    python install_nodes.py [options]

Options:
    --nodes-file PATH       Path to nodes.txt (default: ./nodes.txt)
    --comfyui-dir PATH      ComfyUI directory (default: ./ComfyUI)
    --dry-run               Show what would be installed without installing
    --validate-only         Only validate the nodes file
    --force                 Force reinstall even if node exists
    --skip-deps             Skip installing node dependencies
    --verbose               Show detailed output
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class NodeEntry:
    """Represents a custom node to install"""
    url: str
    version: str
    line_number: int
    name: Optional[str] = None  # Extracted from URL

    @property
    def repo_name(self) -> str:
        """Extract repository name from URL"""
        if self.name:
            return self.name
        # Extract from URL: https://github.com/user/repo.git -> repo
        match = re.search(r'/([^/]+?)(?:\.git)?$', self.url)
        if match:
            return match.group(1)
        return "unknown"


class NodeFileParser:
    """Parses nodes.txt file"""

    # Pattern: URL @ version
    ENTRY_PATTERN = re.compile(
        r'^(?P<url>https?://[^\s@]+(?:\.git)?)\s+@\s+(?P<version>\S+)$'
    )

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse(self) -> List[NodeEntry]:
        """Parse the nodes file and return list of entries"""
        entries = []

        if not self.file_path.exists():
            self.errors.append(f"Nodes file not found: {self.file_path}")
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
                version = match.group('version')

                # Validate URL format
                if not self._validate_url(url):
                    self.warnings.append(
                        f"Line {line_num}: URL may not be a valid git repository: {url}"
                    )

                # Validate version format
                if not self._validate_version(version):
                    self.warnings.append(
                        f"Line {line_num}: Unusual version specifier: {version}"
                    )

                entries.append(NodeEntry(
                    url=url,
                    version=version,
                    line_number=line_num
                ))

        return entries

    def _validate_url(self, url: str) -> bool:
        """Validate that URL looks like a git repository"""
        # Should contain github/gitlab/gitea or end with .git
        return bool(
            re.search(r'(github|gitlab|gitea|bitbucket)\.', url) or
            url.endswith('.git')
        )

    def _validate_version(self, version: str) -> bool:
        """Validate version specifier format"""
        # Valid: latest, nightly, v1.2.3, commit hash, branch name
        if version in ['latest', 'nightly']:
            return True
        # Semver pattern
        if re.match(r'^v?\d+\.\d+(\.\d+)?', version):
            return True
        # Commit hash (7-40 hex chars)
        if re.match(r'^[0-9a-f]{7,40}$', version):
            return True
        # Branch name (alphanumeric, dash, underscore)
        if re.match(r'^[a-zA-Z0-9_-]+$', version):
            return True
        return False


class NodeInstaller:
    """Installs custom nodes with version control"""

    def __init__(
        self,
        comfyui_dir: Path,
        force: bool = False,
        skip_deps: bool = False,
        verbose: bool = False
    ):
        self.comfyui_dir = comfyui_dir
        self.custom_nodes_dir = comfyui_dir / "custom_nodes"
        self.force = force
        self.skip_deps = skip_deps
        self.verbose = verbose
        self.installed = 0
        self.skipped = 0
        self.failed = 0

    def install_entry(self, entry: NodeEntry) -> Tuple[bool, str]:
        """
        Install a single node entry.
        Returns (success, message)
        """
        node_dir = self.custom_nodes_dir / entry.repo_name

        # Check if already exists
        if node_dir.exists() and not self.force:
            if self._check_version(node_dir, entry.version):
                return True, f"✓ {entry.repo_name} (already at {entry.version})"
            else:
                # Exists but wrong version - update it
                return self._update_node(entry, node_dir)

        # Clone the repository
        return self._clone_node(entry, node_dir)

    def _clone_node(self, entry: NodeEntry, node_dir: Path) -> Tuple[bool, str]:
        """Clone a node repository"""
        try:
            if self.verbose:
                print(f"  Cloning {entry.url}...")

            # Clone with --recursive for submodules
            result = subprocess.run(
                ['git', 'clone', '--recursive', entry.url, str(node_dir)],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                return False, f"✗ {entry.repo_name} (clone failed: {result.stderr.strip()})"

            # Checkout specific version
            success, msg = self._checkout_version(entry, node_dir)
            if not success:
                return False, msg

            # Install dependencies
            if not self.skip_deps:
                dep_success, dep_msg = self._install_dependencies(entry, node_dir)
                if not dep_success:
                    return False, f"✗ {entry.repo_name} (installed but dependencies failed: {dep_msg})"

            return True, f"✓ {entry.repo_name} @ {entry.version}"

        except subprocess.TimeoutExpired:
            return False, f"✗ {entry.repo_name} (clone timeout after 5 minutes)"
        except Exception as e:
            return False, f"✗ {entry.repo_name} (error: {e})"

    def _update_node(self, entry: NodeEntry, node_dir: Path) -> Tuple[bool, str]:
        """Update an existing node to a different version"""
        try:
            if self.verbose:
                print(f"  Updating {entry.repo_name}...")

            # Fetch latest changes
            result = subprocess.run(
                ['git', '-C', str(node_dir), 'fetch', '--tags', '--all'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return False, f"✗ {entry.repo_name} (fetch failed: {result.stderr.strip()})"

            # Checkout specific version
            success, msg = self._checkout_version(entry, node_dir)
            if not success:
                return False, msg

            # Update submodules
            subprocess.run(
                ['git', '-C', str(node_dir), 'submodule', 'update', '--init', '--recursive'],
                capture_output=True,
                timeout=60
            )

            # Install/update dependencies
            if not self.skip_deps:
                dep_success, dep_msg = self._install_dependencies(entry, node_dir)
                if not dep_success:
                    return False, f"⚠ {entry.repo_name} @ {entry.version} (updated but dependencies failed: {dep_msg})"

            return True, f"✓ {entry.repo_name} @ {entry.version} (updated)"

        except subprocess.TimeoutExpired:
            return False, f"✗ {entry.repo_name} (update timeout)"
        except Exception as e:
            return False, f"✗ {entry.repo_name} (update error: {e})"

    def _checkout_version(self, entry: NodeEntry, node_dir: Path) -> Tuple[bool, str]:
        """Checkout specific version in a git repository"""
        try:
            version = entry.version

            if version == 'nightly':
                # Get default branch and checkout latest
                result = subprocess.run(
                    ['git', '-C', str(node_dir), 'symbolic-ref', 'refs/remotes/origin/HEAD'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    default_branch = result.stdout.strip().split('/')[-1]
                else:
                    default_branch = 'main'  # Fallback

                subprocess.run(
                    ['git', '-C', str(node_dir), 'checkout', default_branch],
                    capture_output=True,
                    check=True
                )
                subprocess.run(
                    ['git', '-C', str(node_dir), 'pull'],
                    capture_output=True,
                    check=True
                )

            elif version == 'latest':
                # Get latest tag
                result = subprocess.run(
                    ['git', '-C', str(node_dir), 'describe', '--tags', '--abbrev=0'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    latest_tag = result.stdout.strip()
                    subprocess.run(
                        ['git', '-C', str(node_dir), 'checkout', latest_tag],
                        capture_output=True,
                        check=True
                    )
                else:
                    # No tags, use default branch
                    return self._checkout_version(
                        NodeEntry(entry.url, 'nightly', entry.line_number),
                        node_dir
                    )

            else:
                # Specific version (tag, branch, or commit)
                subprocess.run(
                    ['git', '-C', str(node_dir), 'checkout', version],
                    capture_output=True,
                    check=True
                )

            return True, ""

        except subprocess.CalledProcessError as e:
            return False, f"checkout failed: {e.stderr.decode() if e.stderr else str(e)}"
        except Exception as e:
            return False, f"checkout error: {e}"

    def _check_version(self, node_dir: Path, target_version: str) -> bool:
        """Check if node is at the target version"""
        try:
            if target_version == 'nightly':
                # For nightly, always update (return False to trigger update)
                return False

            if target_version == 'latest':
                # Check if we're at the latest tag
                result = subprocess.run(
                    ['git', '-C', str(node_dir), 'describe', '--tags', '--exact-match'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    current_tag = result.stdout.strip()
                    # Get latest tag
                    latest_result = subprocess.run(
                        ['git', '-C', str(node_dir), 'describe', '--tags', '--abbrev=0', 'origin/HEAD'],
                        capture_output=True,
                        text=True
                    )
                    if latest_result.returncode == 0:
                        latest_tag = latest_result.stdout.strip()
                        return current_tag == latest_tag
                return False

            # For specific version, check if we're on that commit/tag/branch
            result = subprocess.run(
                ['git', '-C', str(node_dir), 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                current_commit = result.stdout.strip()
                target_result = subprocess.run(
                    ['git', '-C', str(node_dir), 'rev-parse', target_version],
                    capture_output=True,
                    text=True
                )
                if target_result.returncode == 0:
                    target_commit = target_result.stdout.strip()
                    return current_commit == target_commit

            return False

        except Exception:
            return False

    def _install_dependencies(self, entry: NodeEntry, node_dir: Path) -> Tuple[bool, str]:
        """Install node dependencies from requirements.txt"""
        requirements_file = node_dir / "requirements.txt"

        if not requirements_file.exists():
            return True, "no requirements"

        try:
            if self.verbose:
                print(f"    Installing dependencies for {entry.repo_name}...")

            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                return False, result.stderr.strip()

            return True, "dependencies installed"

        except subprocess.TimeoutExpired:
            return False, "pip install timeout"
        except Exception as e:
            return False, str(e)

    def install_all(self, entries: List[NodeEntry]) -> Dict[str, int]:
        """Install all node entries"""
        if not entries:
            return {"installed": 0, "skipped": 0, "failed": 0}

        print(f"\n{'='*70}")
        print(f"  Installing {len(entries)} custom node(s)")
        print(f"  Target: {self.custom_nodes_dir}")
        print(f"{'='*70}\n")

        # Ensure custom_nodes directory exists
        self.custom_nodes_dir.mkdir(parents=True, exist_ok=True)

        for entry in entries:
            success, message = self.install_entry(entry)
            print(f"  {message}")

            if success:
                if "already" in message or "skipped" in message:
                    self.skipped += 1
                else:
                    self.installed += 1
            else:
                self.failed += 1

        print(f"\n{'='*70}")
        print(f"  Summary: {self.installed} installed, {self.skipped} skipped, {self.failed} failed")
        print(f"{'='*70}\n")

        return {
            "installed": self.installed,
            "skipped": self.skipped,
            "failed": self.failed
        }


def main():
    parser = argparse.ArgumentParser(
        description="Install ComfyUI custom nodes from nodes.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--nodes-file",
        type=Path,
        default=Path("nodes.txt"),
        help="Path to nodes.txt (default: ./nodes.txt)"
    )
    parser.add_argument(
        "--comfyui-dir",
        type=Path,
        default=Path("./ComfyUI"),
        help="ComfyUI directory (default: ./ComfyUI)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be installed without installing"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the nodes file"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstall even if node exists"
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip installing node dependencies"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )

    args = parser.parse_args()

    # Check git is available
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: git is not installed or not in PATH")
        return 1

    # Parse the nodes file
    print(f"Parsing nodes file: {args.nodes_file}")
    file_parser = NodeFileParser(args.nodes_file)
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
        print("\n✓ No custom nodes to install (all lines commented out or empty file)")
        return 0

    print(f"\n✓ Found {len(entries)} custom node(s) to install")

    # Group by version type for display
    by_version = {"latest": [], "nightly": [], "specific": []}
    for entry in entries:
        if entry.version == "latest":
            by_version["latest"].append(entry)
        elif entry.version == "nightly":
            by_version["nightly"].append(entry)
        else:
            by_version["specific"].append(entry)

    print(f"\nBreakdown:")
    if by_version["latest"]:
        print(f"  • Latest stable: {len(by_version['latest'])} node(s)")
    if by_version["nightly"]:
        print(f"  • Nightly builds: {len(by_version['nightly'])} node(s)")
    if by_version["specific"]:
        print(f"  • Specific versions: {len(by_version['specific'])} node(s)")

    if args.validate_only:
        print("\n✓ Validation complete!")
        return 0

    if args.dry_run:
        print(f"\n{'='*70}")
        print(f"  DRY RUN - Would install to: {args.comfyui_dir / 'custom_nodes'}")
        print(f"{'='*70}\n")
        for entry in entries:
            print(f"  {entry.repo_name} @ {entry.version}")
            print(f"    URL: {entry.url}")
        print()
        return 0

    # Check ComfyUI directory exists
    if not args.comfyui_dir.exists():
        print(f"\nError: ComfyUI directory not found: {args.comfyui_dir}")
        print("Run this script after ComfyUI has been installed")
        return 1

    # Install nodes
    installer = NodeInstaller(
        args.comfyui_dir,
        force=args.force,
        skip_deps=args.skip_deps,
        verbose=args.verbose
    )
    results = installer.install_all(entries)

    return 1 if results["failed"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
