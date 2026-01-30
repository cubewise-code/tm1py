# Contributing to TM1Py

Thank you for your interest in contributing to TM1Py! This document provides guidelines and information about the
contribution process.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)
- [Code Style](#code-style)

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/tm1py.git`
3. Add upstream remote: `git remote add upstream https://github.com/cubewise-code/tm1py.git`

## Development Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install TM1Py in development mode:**
   ```bash
   pip install -e .[pandas,dev]
   ```

3. **Install development tools:**
   ```bash
   pip install black ruff pytest
   ```

## Making Changes

1. **Create a branch:**
   ```bash
   git checkout -b your-feature-name
   ```

2. **Make your changes** following the code style guidelines

3. **Format your code:**
   ```bash
   black .
   ruff check --fix .
   ```

4. **Test your changes** (if you have access to a TM1 instance):
   ```bash
   pytest Tests/
   ```

## Pull Request Process

### 1. Before Opening a PR

- Ensure your code follows the style guidelines
- Run formatting tools (Black, Ruff)
- Update documentation if needed
- Write clear, descriptive commit messages

### 2. Opening a PR

- Push your branch to your fork
- Open a PR against the `master` branch
- Fill out the PR template (if available)
- Describe what your PR does and why

**Note**: You don't need to follow any special commit message format! Maintainers will handle versioning via labels.

### 3. PR Validation

Your PR will automatically trigger validation checks:

- **Code formatting** (Black)
- **Linting** (Ruff)
- **Future**: Unit tests (when available)

These checks must pass before your PR can be merged.

### 4. Review Process

- Maintainers will review your PR
- Address any feedback or requested changes
- Once approved, a maintainer will add the appropriate release label and merge

## Release Process

TM1Py uses **automated nightly releases** with semantic versioning.

### For Contributors

**You don't need to do anything special!** Just:

1. Create your PR
2. Wait for review
3. That's it!

No need for special:

- Commit message formats
- Branch naming conventions
- Version bumping
- Release notes

### For Maintainers

**IMPORTANT**: Before merging a PR, you must add the appropriate label to control the version bump.

| Label                        | Version Bump      | When to Use                                                       | Example                                   |
|------------------------------|-------------------|-------------------------------------------------------------------|-------------------------------------------|
| `release:patch`              | `2.1.5` → `2.1.6` | Bug fixes, small improvements                                     | Fix pandas compatibility issue            |
| `release:minor`              | `2.1.5` → `2.2.0` | New features, enhancements                                        | Add support for new TM1 REST API endpoint |
| `release:major`              | `2.1.5` → `3.0.0` | Breaking changes, major updates                                   | Remove deprecated methods, change API     |
| `skip-release` (or no label) | No version bump   | Docs, tests, CI changes, or changes you don't want to release yet | Update README, fix typo in docs           |

**Default behavior**: If no label is added, **NO release will be created**. This is a safe default to prevent accidental
releases.

**To create a release**: You must explicitly add `release:patch`, `release:minor`, or `release:major` label.

### Release Timeline

**Daily cycle:**

```
Day 1:
  10:00 AM - PR #123 (bug fix, labeled 'release:patch') merged
  2:00 PM  - PR #124 (feature, labeled 'release:minor') merged
  5:00 PM  - PR #125 (docs update, no label) merged

  4:00 AM (next day) - Nightly workflow starts:
    - Runs full integration tests (2-3 hours)
    - If tests pass:
      → Creates release 2.2.0 (because of the minor label)
      → Publishes to PyPI (includes all 3 PRs)
      → Updates documentation
  7:00 AM - Users can: pip install --upgrade TM1py

Day 2:
  11:00 AM - PR #126 (minor fix, no label) merged
  3:00 PM  - PR #127 (test update, no label) merged

  4:00 AM (next day) - Nightly workflow starts:
    - No release labels found
    - Skips release (no version bump, no PyPI publish)
```

### How It Works

1. **Merge to master** → PR is merged after validation passes
2. **Nightly at 4 AM CET** → Automated workflow runs:
    - Checks for new commits since last release
    - Runs full integration test suite
    - Determines version bump from PR labels
    - Creates GitHub Release
    - Publishes to PyPI
3. **Next morning** → New version available to users!

## Code Style

### Python Code Style

- **Line length**: 120 characters (configured in Black)
- **Formatting**: Use Black for automatic formatting
- **Linting**: Use Ruff for import sorting and error detection
- **Target version**: Python 3.7+

### Running Code Style Tools

```bash
# Format code
black .

# Check imports and linting
ruff check .

# Auto-fix linting issues
ruff check --fix .
```

### Import Organization

Imports should be organized by Ruff/isort:

1. Standard library imports
2. Third-party imports
3. Local application imports

Example:

```python
# Standard library imports
from pathlib import Path
from typing import List

# Third-party imports
import pandas as pd

# Local application imports
from TM1py import TM1Service
```

## Testing

### Running Tests

If you have access to TM1 instances:

```bash
# Run all tests
pytest Tests/

# Run specific test file
pytest Tests/test_cube_service.py

# Run with verbose output
pytest Tests/ -v
```

### Test Configuration

Tests require TM1 connection configuration. See `Tests/resources/` for setup instructions.

## Questions?

- Check existing [Issues](https://github.com/cubewise-code/tm1py/issues)
- Review [Discussions](https://github.com/cubewise-code/tm1py/discussions)
- Read the [Documentation](https://tm1py.readthedocs.io/)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to TM1Py! 🎉
