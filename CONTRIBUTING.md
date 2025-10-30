# Contributing to ComfyUI RunPod Handler

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/comfy-template.git
   cd comfy-template
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL-OWNER/comfy-template.git
   ```

## Development Setup

### Prerequisites

- Docker with GPU support
- NVIDIA GPU with drivers
- NVIDIA Container Toolkit
- Python 3.10+
- Git

### Local Development

```bash
# Copy environment template
cp .env.example .env

# Start development environment
docker compose up

# Access ComfyUI at http://localhost:8188
# Access API at http://localhost:8000
```

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_handler.py

# Run linting
flake8 .
black --check .
mypy .
```

### Docker Hub and Deployment

**Important:** Contributors do NOT need to build or push Docker images.

- **Official images** are published to `alongbottom/comfyui-runpod` by the maintainer
- **Contributors** only need to test locally with `docker compose up`
- **No Docker Hub login required** for contributing code

If you want to deploy your own version:
1. **Fork this repository**
2. Edit `build.sh` and change `DOCKER_USERNAME="alongbottom"` to your username
3. Login to Docker Hub: `docker login`
4. Deploy: `./deploy.sh ada`

For contributing to this repo, just test locally - no deployment needed!

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

- 🐛 **Bug fixes**
- ✨ **New features**
- 📝 **Documentation improvements**
- 🧪 **Tests**
- 🎨 **Code quality improvements**
- 🔧 **Configuration improvements**

### Contribution Workflow

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes**:
   - Write clear, concise commit messages
   - Follow the coding standards
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**:
   ```bash
   # Run tests locally
   pytest

   # Test with Docker
   docker compose up --build

   # Test the actual workflow
   python examples/test_local.py
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
   - `feat:` - New feature (minor version bump)
   - `fix:` - Bug fix (patch version bump)
   - `feat!:` or `BREAKING CHANGE:` - Breaking change (major version bump)
   - `docs:` - Documentation changes (no version bump)
   - `test:` - Test changes (no version bump)
   - `chore:` - Maintenance tasks (no version bump)
   - `refactor:` - Code refactoring (no version bump)
   - `perf:` - Performance improvements (patch version bump)

   **Important:** Commit messages determine automatic version bumps! See [Versioning Guide](.github/workflows/VERSION_GUIDE.md).

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request** on GitHub

## Coding Standards

### Python Code Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [flake8](https://flake8.pycqa.org/) for linting
- Use type hints where appropriate
- Maximum line length: 100 characters

### Code Quality

```bash
# Format code with Black
black .

# Run linter
flake8 .

# Type checking
mypy .

# Sort imports
isort .
```

### Documentation

- Add docstrings to all functions, classes, and modules
- Use Google-style docstrings
- Update README.md for user-facing changes
- Update CLAUDE.md for architectural changes
- Add inline comments for complex logic

### Git Commit Messages

- Use imperative mood ("Add feature" not "Added feature")
- First line: brief summary (50 chars or less)
- Blank line, then detailed explanation if needed
- Reference issues: `Fixes #123` or `Closes #456`

## Testing

### Test Structure

```
tests/
├── test_handler.py          # Handler function tests
├── test_download_models.py  # Model downloader tests
├── test_install_nodes.py    # Node installer tests
├── test_s3_upload.py        # S3 upload tests
└── test_integration.py      # End-to-end tests
```

### Writing Tests

- Use `pytest` framework
- Write unit tests for new functions
- Write integration tests for workflows
- Aim for >80% code coverage
- Mock external dependencies (ComfyUI API, S3, etc.)

Example test:

```python
def test_apply_overrides():
    workflow = {"6": {"inputs": {"text": "old"}}}
    overrides = [{"node_id": "6", "field": "inputs.text", "value": "new"}]

    result = apply_overrides(workflow, overrides)

    assert result["6"]["inputs"]["text"] == "new"
```

### Running Specific Tests

```bash
# Run specific test
pytest tests/test_handler.py::test_apply_overrides

# Run with verbose output
pytest -v

# Run with print statements
pytest -s

# Run failed tests only
pytest --lf
```

## Pull Request Process

### Before Submitting

- [ ] Tests pass locally (`pytest`)
- [ ] Code is formatted (`black .`)
- [ ] Linting passes (`flake8 .`)
- [ ] Type checking passes (`mypy .`)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (if applicable)
- [ ] Commit messages follow conventions

### PR Guidelines

1. **Title**: Clear, descriptive title following conventional commits
2. **Description**: Explain what and why, not how
3. **Testing**: Describe how you tested the changes
4. **Screenshots**: Include if UI/output changes
5. **Breaking Changes**: Clearly document any breaking changes
6. **Issue Link**: Reference related issues

### Automated Deployment

When your PR is merged to `main`:

1. **Version is automatically bumped** based on commit messages (see [Versioning Guide](.github/workflows/VERSION_GUIDE.md))
2. **Docker images are built** for both Ada and Blackwell architectures
3. **Images are pushed** to Docker Hub
4. **GitHub Release is created** with changelog

**No manual deployment needed!** Just merge your PR and the CI/CD pipeline handles the rest.

**Important:** Use proper commit message format (`feat:`, `fix:`, etc.) as it determines version bumps!

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (patch version bump)
- [ ] New feature (minor version bump)
- [ ] Breaking change (major version bump)
- [ ] Documentation update (no version bump)

## Testing
How did you test this?

## Checklist
- [ ] Tests pass
- [ ] Code formatted
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process

- Maintainers will review your PR
- Address feedback promptly
- Be open to suggestions
- CI must pass before merging
- At least one approval required

## Reporting Issues

### Bug Reports

Include:
- Clear, descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, GPU, Docker version)
- Error messages and logs
- Screenshots if applicable

### Feature Requests

Include:
- Clear use case
- Why this feature is useful
- Proposed implementation (optional)
- Alternative solutions considered

### Security Issues

**DO NOT** open public issues for security vulnerabilities. Email security@example.com instead.

## Development Tips

### Debugging

```bash
# View Docker logs
docker compose logs -f

# Debug handler locally
python -m pdb examples/test_local.py

# Check handler directly
python handler.py
```

### Performance Testing

```bash
# Benchmark workflow execution
time python examples/test_local.py

# Profile handler
python -m cProfile -o profile.stats handler.py
```

### Building for Multiple Architectures

```bash
# Build for Ada (RTX 4090)
./build.sh --arch ada

# Build for Blackwell (RTX 5090)
./build.sh --arch blackwell

# Test both builds
docker run --rm --gpus all alongbottom/comfyui-runpod:ada python3 --version
```

## Questions?

- Check existing [Issues](https://github.com/OWNER/REPO/issues)
- Check [Discussions](https://github.com/OWNER/REPO/discussions)
- Read the [documentation](docs/)
- Ask in pull request comments

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🎉
