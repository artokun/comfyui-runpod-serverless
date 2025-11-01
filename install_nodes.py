#!/usr/bin/env python3
"""
ComfyUI Custom Nodes Installer
Parses config.yml and installs custom nodes with version control.

Usage:
    python install_nodes.py [options]

Options:
    --config PATH           Path to config.yml (default: ./config.yml)
    --comfyui-dir PATH      ComfyUI directory (default: ./ComfyUI)
    --dry-run               Show what would be installed without installing
    --validate-only         Only validate the config file
    --force                 Force reinstall even if node exists
    --skip-deps             Skip installing node dependencies
    --verbose               Show detailed output
"""

import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("Warning: PyYAML not installed. Install with: pip install pyyaml")


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
    """Parses config.yml file"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse(self) -> List[NodeEntry]:
        """Parse the config file and return list of node entries"""
        if not self.file_path.exists():
            self.errors.append(f"Config file not found: {self.file_path}")
            return []

        return self._parse_yaml()

    def _parse_yaml(self) -> List[NodeEntry]:
        """Parse YAML config file"""
        if not YAML_AVAILABLE:
            self.errors.append("PyYAML not available. Cannot parse YAML config.")
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

        nodes_config = config.get('nodes', [])
        if not isinstance(nodes_config, list):
            self.errors.append("'nodes' section must be a list")
            return []

        entries = []
        for idx, node in enumerate(nodes_config, 1):
            if not isinstance(node, dict):
                self.warnings.append(f"Node entry {idx} is not a dictionary, skipping")
                continue

            url = node.get('url')
            version = node.get('version', 'latest')

            if not url:
                self.warnings.append(f"Node entry {idx} missing 'url', skipping")
                continue

            # Validate URL
            if not self._validate_url(url):
                self.warnings.append(f"Node entry {idx}: URL may not be a valid git repository: {url}")

            # Validate version
            if not self._validate_version(version):
                self.warnings.append(f"Node entry {idx}: Unusual version specifier: {version}")

            entries.append(NodeEntry(
                url=url,
                version=version,
                line_number=idx
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
                # Node exists at correct version, but still ensure dependencies are installed
                # (they might be missing after container rebuild)
                if not self.skip_deps:
                    dep_success, dep_msg = self._install_dependencies(entry, node_dir)
                    if not dep_success:
                        return False, f"[X] {entry.repo_name}: {dep_msg}"
                return True, f"[OK] {entry.repo_name} (already at {entry.version})"
            else:
                # Exists but wrong version - update it
                print(f"  [UPD] Updating {entry.repo_name}...", flush=True)
                return self._update_node(entry, node_dir)

        # Clone the repository
        print(f"  [DL] Installing {entry.repo_name}...", flush=True)
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
                error_msg = result.stderr.strip()[:200]
                return False, f"[ERR] INSTALL FAILED: {entry.repo_name} (clone error: {error_msg})"

            # Checkout specific version
            success, msg = self._checkout_version(entry, node_dir)
            if not success:
                return False, f"[ERR] INSTALL FAILED: {msg}"

            # Install dependencies
            if not self.skip_deps:
                dep_success, dep_msg = self._install_dependencies(entry, node_dir)
                if not dep_success:
                    return False, f"[ERR] INSTALL FAILED: {entry.repo_name} (dependencies: {dep_msg})"

            return True, f"[OK] {entry.repo_name} @ {entry.version}"

        except subprocess.TimeoutExpired:
            return False, f"[ERR] INSTALL FAILED: {entry.repo_name} (TIMEOUT after 5 min cloning)"
        except Exception as e:
            return False, f"[ERR] INSTALL FAILED: {entry.repo_name} ({str(e)[:200]})"

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
                error_msg = result.stderr.strip()[:200]
                return False, f"[ERR] UPDATE FAILED: {entry.repo_name} (fetch error: {error_msg})"

            # Checkout specific version
            success, msg = self._checkout_version(entry, node_dir)
            if not success:
                return False, f"[ERR] UPDATE FAILED: {msg}"

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
                    return False, f"[WARN] PARTIAL UPDATE: {entry.repo_name} @ {entry.version} (updated but dependencies failed: {dep_msg})"

            return True, f"[OK] {entry.repo_name} @ {entry.version} (updated)"

        except subprocess.TimeoutExpired:
            return False, f"[ERR] UPDATE FAILED: {entry.repo_name} (TIMEOUT)"
        except Exception as e:
            return False, f"[ERR] UPDATE FAILED: {entry.repo_name} ({str(e)[:200]})"

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
            # Always show dependency installation (not just in verbose mode)
            print(f"    [PKG] Installing dependencies for {entry.repo_name}...", flush=True)

            # Using uv for 10-100x faster downloads with parallel connections
            result = subprocess.run(
                ['uv', 'pip', 'install', '--system', '--no-cache', '-r', str(requirements_file)],
                capture_output=True,
                text=True,
                timeout=600  # Increased to 10 minutes for heavy packages
            )

            if result.returncode != 0:
                return False, result.stderr.strip()[:200]  # Truncate long errors

            return True, "dependencies installed"

        except subprocess.TimeoutExpired:
            return False, "TIMEOUT (dependencies took >10 min)"
        except Exception as e:
            return False, str(e)[:200]  # Truncate long errors

    def _collect_all_requirements(self, entries: List[NodeEntry]) -> List[Path]:
        """Collect all requirements.txt files from node directories"""
        requirements_files = []
        for entry in entries:
            node_dir = self.custom_nodes_dir / entry.repo_name
            req_file = node_dir / "requirements.txt"
            if req_file.exists():
                requirements_files.append(req_file)
        return requirements_files

    def _batch_install_dependencies(self, requirements_files: List[Path]) -> Tuple[bool, str]:
        """Install all dependencies from multiple requirements files in one UV command"""
        if not requirements_files:
            return True, "no requirements files found"

        try:
            import tempfile

            # Create a temporary combined requirements file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as combined:
                # Read all requirements files and combine them
                seen_requirements = set()
                for req_file in requirements_files:
                    with open(req_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            # Skip comments and empty lines
                            if line and not line.startswith('#'):
                                # Normalize the requirement (ignore version for deduplication key)
                                req_key = line.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].strip()
                                # Keep the full line with version
                                if req_key not in seen_requirements:
                                    combined.write(line + '\n')
                                    seen_requirements.add(req_key)

                combined_path = combined.name

            # Install all dependencies with one UV command
            print(f"  [PKG] Batch installing dependencies from {len(requirements_files)} node(s)...", flush=True)
            print(f"      Total unique packages: {len(seen_requirements)}", flush=True)
            print(f"      UV will show live download progress below:\n", flush=True)

            # Don't capture output to show UV's native progress bars
            result = subprocess.run(
                ['uv', 'pip', 'install', '--system', '--no-cache', '-r', combined_path],
                timeout=1200  # 20 minutes for large batch
            )

            # Clean up temp file
            import os
            os.unlink(combined_path)

            if result.returncode != 0:
                return False, f"UV install failed with exit code {result.returncode}"

            print(f"\n      [OK] Batch installation complete!\n", flush=True)
            return True, f"batch installed {len(seen_requirements)} packages"

        except subprocess.TimeoutExpired:
            return False, "TIMEOUT (batch install took >20 min)"
        except Exception as e:
            return False, str(e)[:500]

    def _run_install_script(self, entry: NodeEntry, node_dir: Path) -> Tuple[bool, str]:
        """Run install.py script if it exists in the node directory"""
        install_script = node_dir / "install.py"

        if not install_script.exists():
            return True, "no install script"

        try:
            # Run install.py in the node directory with relative path
            result = subprocess.run(
                ['python', 'install.py'],
                cwd=str(node_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode != 0:
                return False, f"install script failed: {result.stderr.strip()[:200]}"

            return True, "install script completed"

        except subprocess.TimeoutExpired:
            return False, "install script TIMEOUT (>5 min)"
        except Exception as e:
            return False, f"install script error: {str(e)[:200]}"

    def install_all(self, entries: List[NodeEntry], max_workers: int = 4) -> Dict[str, int]:
        """Install all node entries using optimized batch installation"""
        if not entries:
            return {"installed": 0, "skipped": 0, "failed": 0}

        print(f"\n{'='*70}")
        print(f"  Installing {len(entries)} custom node(s) - BATCH MODE")
        print(f"  Target: {self.custom_nodes_dir}")
        print(f"{'='*70}\n")

        # Ensure custom_nodes directory exists
        self.custom_nodes_dir.mkdir(parents=True, exist_ok=True)

        # PHASE 1: Clone all repos in parallel (without installing deps)
        print(f"  PHASE 1: Cloning repositories ({max_workers} parallel workers)...")
        cloned_entries = []
        skip_deps_backup = self.skip_deps
        self.skip_deps = True  # Temporarily skip deps during cloning

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_entry = {executor.submit(self.install_entry, entry): entry for entry in entries}

            for future in as_completed(future_to_entry):
                entry = future_to_entry[future]
                try:
                    success, message = future.result()
                    print(f"  {message}")

                    if success:
                        if "already" in message or "skipped" in message:
                            self.skipped += 1
                        else:
                            cloned_entries.append(entry)
                            self.installed += 1
                    else:
                        self.failed += 1
                except Exception as e:
                    print(f"  [ERR] CLONE FAILED: {entry.repo_name} (exception: {str(e)[:200]})")
                    self.failed += 1

        self.skip_deps = skip_deps_backup

        # PHASE 2: Batch install ALL dependencies with one UV command
        if not self.skip_deps and cloned_entries:
            print(f"\n  PHASE 2: Batch installing dependencies...")
            requirements_files = self._collect_all_requirements(entries)

            if requirements_files:
                success, msg = self._batch_install_dependencies(requirements_files)
                if success:
                    print(f"      [OK] {msg}")
                else:
                    print(f"      [ERR] Batch install failed: {msg}")
                    # Don't fail the whole process, continue with install scripts
            else:
                print(f"      [INFO] No requirements.txt files found")

        # PHASE 3: Run all install.py scripts in parallel
        print(f"\n  PHASE 3: Running install scripts...")
        install_script_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_entry = {}

            for entry in entries:
                node_dir = self.custom_nodes_dir / entry.repo_name
                install_script = node_dir / "install.py"

                if install_script.exists():
                    future = executor.submit(self._run_install_script, entry, node_dir)
                    future_to_entry[future] = entry
                    install_script_count += 1

            if install_script_count > 0:
                for future in as_completed(future_to_entry):
                    entry = future_to_entry[future]
                    try:
                        success, msg = future.result()
                        if success:
                            print(f"      [OK] {entry.repo_name}: {msg}")
                        else:
                            print(f"      [ERR] {entry.repo_name}: {msg}")
                    except Exception as e:
                        print(f"      [ERR] {entry.repo_name}: install script exception: {str(e)[:200]}")
            else:
                print(f"      [INFO] No install scripts to run")

        print(f"\n{'='*70}")
        print(f"  Summary: {self.installed} installed, {self.skipped} skipped, {self.failed} failed")
        print(f"{'='*70}\n")

        return {
            "installed": self.installed,
            "skipped": self.skipped,
            "failed": self.failed
        }

    def install_orphan_dependencies(self, processed_nodes: List[str]) -> Dict[str, int]:
        """
        Install dependencies for all nodes in custom_nodes that weren't in config.yml.
        This ensures nodes collected over time have their dependencies installed.

        Args:
            processed_nodes: List of node directory names already processed from config.yml

        Returns:
            Dict with counts of successful/failed dependency installations
        """
        if self.skip_deps:
            return {"deps_installed": 0, "deps_failed": 0}

        if not self.custom_nodes_dir.exists():
            return {"deps_installed": 0, "deps_failed": 0}

        # Find all directories in custom_nodes
        all_node_dirs = [d for d in self.custom_nodes_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

        # Filter to only orphaned nodes (not in config.yml)
        orphaned_nodes = [d for d in all_node_dirs if d.name not in processed_nodes]

        if not orphaned_nodes:
            return {"deps_installed": 0, "deps_failed": 0}

        print(f"\n{'='*70}")
        print(f"  Checking dependencies for {len(orphaned_nodes)} orphaned node(s)")
        print(f"  (nodes not in config.yml but found in custom_nodes)")
        print(f"{'='*70}\n")

        deps_installed = 0
        deps_failed = 0

        for node_dir in orphaned_nodes:
            requirements_file = node_dir / "requirements.txt"

            if not requirements_file.exists():
                print(f"  [OK] {node_dir.name} (no requirements)")
                continue

            try:
                print(f"  [PKG] Installing dependencies for {node_dir.name}...", flush=True)

                # Using uv for 10-100x faster downloads with parallel connections
                result = subprocess.run(
                    ['uv', 'pip', 'install', '--system', '--no-cache', '-r', str(requirements_file)],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                if result.returncode != 0:
                    print(f"  [X] {node_dir.name} (dependencies failed: {result.stderr.strip()[:100]})")
                    deps_failed += 1
                else:
                    print(f"  [OK] {node_dir.name} (dependencies installed)")
                    deps_installed += 1

            except subprocess.TimeoutExpired:
                print(f"  [X] {node_dir.name} (TIMEOUT installing dependencies)")
                deps_failed += 1
            except Exception as e:
                print(f"  [X] {node_dir.name} (error: {str(e)[:100]})")
                deps_failed += 1

        print(f"\n{'='*70}")
        print(f"  Orphaned dependencies: {deps_installed} installed, {deps_failed} failed")
        print(f"{'='*70}\n")

        return {
            "deps_installed": deps_installed,
            "deps_failed": deps_failed
        }


def main():
    parser = argparse.ArgumentParser(
        description="Install ComfyUI custom nodes from config.yml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yml"),
        help="Path to config.yml (default: ./config.yml)"
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
        help="Only validate the config file"
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
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Number of parallel workers for installation (default: 4)"
    )
    parser.add_argument(
        "--orphans-only",
        action="store_true",
        help="Only install dependencies for orphaned nodes (nodes in custom_nodes but not in config.yml)"
    )

    args = parser.parse_args()

    # Check git is available
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: git is not installed or not in PATH")
        return 1

    # Check ComfyUI directory exists
    if not args.comfyui_dir.exists():
        print(f"\nError: ComfyUI directory not found: {args.comfyui_dir}")
        print("Run this script after ComfyUI has been installed")
        return 1

    # Handle orphans-only mode
    if args.orphans_only:
        print(f"\n{'='*70}")
        print(f"  Orphaned Nodes Dependency Installation")
        print(f"{'='*70}")
        print(f"  ComfyUI: {args.comfyui_dir}")
        print(f"{'='*70}\n")

        installer = NodeInstaller(
            args.comfyui_dir,
            force=args.force,
            skip_deps=args.skip_deps,
            verbose=args.verbose
        )

        # Parse config to get list of nodes already processed
        # This prevents re-installing dependencies for nodes from config.yml
        processed_nodes = []
        if args.config and args.config.exists():
            file_parser = ConfigFileParser(args.config)
            entries = file_parser.parse()
            processed_nodes = [entry.repo_name for entry in entries]
            if processed_nodes:
                print(f"  Excluding {len(processed_nodes)} node(s) from config.yml")
                print(f"  (their dependencies were already installed)\n")

        orphan_results = installer.install_orphan_dependencies(processed_nodes)

        return 1 if orphan_results.get("deps_failed", 0) > 0 else 0

    # Parse the config file
    print(f"Parsing config file: {args.config}")
    file_parser = NodeFileParser(args.config)
    entries = file_parser.parse()

    # Show errors
    if file_parser.errors:
        print(f"\n{'='*70}")
        print(f"  ERRORS ({len(file_parser.errors)})")
        print(f"{'='*70}")
        for error in file_parser.errors:
            print(f"  [X] {error}")
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
        print("\n[OK] No custom nodes to install (all lines commented out or empty file)")
        return 0

    print(f"\n[OK] Found {len(entries)} custom node(s) to install")

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
        print(f"  - Latest stable: {len(by_version['latest'])} node(s)")
    if by_version["nightly"]:
        print(f"  - Nightly builds: {len(by_version['nightly'])} node(s)")
    if by_version["specific"]:
        print(f"  - Specific versions: {len(by_version['specific'])} node(s)")

    if args.validate_only:
        print("\n[OK] Validation complete!")
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

    # Install nodes
    installer = NodeInstaller(
        args.comfyui_dir,
        force=args.force,
        skip_deps=args.skip_deps,
        verbose=args.verbose
    )
    results = installer.install_all(entries, max_workers=args.max_workers)

    # Install dependencies for any orphaned nodes (nodes in custom_nodes but not in config.yml)
    # This ensures nodes collected over time have their dependencies installed
    processed_node_names = [entry.repo_name for entry in entries]
    orphan_results = installer.install_orphan_dependencies(processed_node_names)

    # Consider orphan dependency failures as failures
    total_failed = results["failed"] + orphan_results.get("deps_failed", 0)

    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
