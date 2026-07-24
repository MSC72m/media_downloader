# Contributing to Media Downloader

First off, thanks for taking the time to contribute! 🎉

The following is a set of guidelines for contributing to Media Downloader. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Branching Strategy](#branching-strategy)
- [Development Process](#development-process)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git
- A GitHub account

### Setup Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork locally**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/media_downloader.git
   cd media_downloader
   ```

3. **Install development dependencies**:
   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

4. **Install Playwright browser**:
   ```bash
   # Using uv
   uv run playwright install chromium

   # Or using pip
   playwright install chromium
   ```

5. **Create a branch for your changes**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Branching Strategy

We follow a structured branching model to maintain code quality:

### Main Branches

- **`main`** - Production-ready code. Always stable. **No direct commits or PRs allowed.**
- **`development`** - Integration branch for features and fixes. PRs merge here first.

### Feature Branches

- **`feature/*`** - New features and enhancements
- **`fix/*`** - Bug fixes
- **`hotfix/*`** - Critical production fixes
- **`docs/*`** - Documentation updates
- **`test/*`** - Test additions or improvements

### Branch Naming Convention

```
<type>/<short-description>

Examples:
feature/youtube-chapter-support
fix/spotify-download-timeout
docs/api-documentation
test/radiojavan-coverage
```

## Development Process

1. **Create an issue** (if one doesn't exist) to discuss the change
2. **Create a branch** from `development` following naming conventions
3. **Make your changes** following coding standards
4. **Write/update tests** for your changes
5. **Run quality checks locally**:
   ```bash
   # Run linting
   uv run ruff check .

   # Run type checking
   npx basedpyright --outputjson

   # Run tests
   uv run pytest -q
   ```
6. **Commit your changes** with a descriptive message
7. **Push to your fork** and create a pull request

## Commit Guidelines

We follow conventional commits for clear project history:

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks
- `perf:` - Performance improvements

### Examples

```
feat(youtube): add chapter download support

fix(spotify): resolve timeout on large playlists

docs(readme): update installation instructions

test(radiojavan): add CDN fallback coverage
```

### Pre-commit Hooks

This project uses pre-commit hooks that automatically:
- Trim trailing whitespace
- Fix end-of-file issues
- Check YAML, JSON, TOML files
- Run ruff linting and formatting
- Run mypy type checking

## Pull Request Process

### Before Submitting

1. **Update from development**:
   ```bash
   git fetch origin
   git rebase origin/development
   ```

2. **Run all quality checks**:
   ```bash
   uv run ruff check .
   npx basedpyright --outputjson
   uv run pytest -q
   ```

3. **Update documentation** if needed

### PR Requirements

- **Target branch**: `development` (never `main`)
- **Title**: Clear, descriptive, follows commit format
- **Description**: Explain what and why, not just how
- **Tests**: New code requires new tests
- **Documentation**: Update relevant docs
- **No merge conflicts**: Rebase if necessary

### PR Template

```markdown
## Description
[Describe your changes]

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Edge cases covered

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings introduced
- [ ] Tests added/updated
```

### Review Process

1. At least one maintainer approval required
2. All CI checks must pass
3. No unresolved conversations
4. Branch must be up-to-date with `development`

### After Approval

- Maintainers will merge your PR into `development`
- Changes will be included in the next release to `main`

## Coding Standards

### Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) with ruff formatting
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Keep functions focused and under 50 lines when possible
- Use descriptive variable names (no single letters except counters)

### Code Organization

```
src/
├── application/     # Application orchestration and DI
├── coordinators/    # UI coordinators
├── core/           # Core domain logic
├── handlers/       # Platform-specific handlers
├── services/       # Download services and utilities
├── ui/            # UI components
└── utils/         # Shared utilities
```

### Imports

Group imports in this order:
1. Standard library
2. Third-party packages
3. Local application imports

Use absolute imports from `src.` for clarity.

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest -q

# Run specific test file
uv run pytest tests/test_youtube_downloader.py

# Run with coverage
uv run pytest --cov=src tests/

# Run verbose
uv run pytest -v
```

### Test Guidelines

- Write unit tests for business logic
- Write integration tests for service interactions
- Mock external APIs and network calls
- Use descriptive test names: `test_<what>_<condition>_<expected>`
- One concept per test

### Test Structure

```python
def test_download_handles_timeout_gracefully():
    """Test that downloader retries on network timeout."""
    # Arrange
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = TimeoutError()

    # Act & Assert
    with pytest.raises(DownloadError):
        downloader.download("https://example.com/file.mp3")
```

## Reporting Bugs

### Before Reporting

1. Check existing issues to avoid duplicates
2. Try the latest version
3. Collect debug information:
   - OS and version
   - Python version
   - Error messages/stack traces
   - Steps to reproduce

### Bug Report Template

```markdown
**Description**
[Clear description of the bug]

**Steps to Reproduce**
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
[What you expected to happen]

**Actual Behavior**
[What actually happened]

**Environment**
- OS: [e.g., Windows 11, macOS 14, Ubuntu 22.04]
- Python version: [e.g., 3.11.4]
- Media Downloader version: [e.g., 1.2.2]

**Logs**
```
[Paste relevant log output]
```

**Screenshots**
[If applicable]
```

## Feature Requests

We welcome feature requests! Please:

1. Check existing issues first
2. Describe the feature clearly
3. Explain the use case and benefit
4. Consider implementation complexity

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
[A clear description of the problem]

**Describe the solution you'd like**
[What you want to happen]

**Describe alternatives you've considered**
[Other solutions you've thought about]

**Additional context**
[Any other context, screenshots, or examples]

**Would you be willing to implement this?**
[Yes/No/Maybe - contributions welcome!]
```

## Questions?

Feel free to:
- Open a [Discussion](https://github.com/MSC72m/media_downloader/discussions) for questions
- Create an issue for bug reports or feature requests
- Review existing PRs to understand the contribution flow

Thank you for contributing! 🙌
