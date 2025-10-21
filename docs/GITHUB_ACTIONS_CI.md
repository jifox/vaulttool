# GitHub Actions CI/CD Workflow

## Overview

This document describes the GitHub Actions CI/CD workflow configured for VaultTool.

## Workflow File

`.github/workflows/ci.yml`

## Triggers

The workflow runs on:
- **Push** to `main` and `develop` branches
- **Pull requests** targeting `main` and `develop` branches

## Jobs

### 1. Pre-commit Checks Job

**Purpose:** Runs all pre-commit hooks to ensure code quality and style consistency.

**Matrix Strategy:** Tests against Python 3.10, 3.11, 3.12, and 3.13

**Steps:**
1. **Check out code** - Uses `actions/checkout@v4`
2. **Set up Python** - Installs specified Python version
3. **Install Poetry** - Uses `snok/install-poetry@v1` (v1.8.3)
4. **Cache virtual environment** - Caches `.venv` based on `poetry.lock` hash
5. **Install dependencies** - Runs `poetry install` (skipped if cached)
6. **Create test key file** - Generates encryption key for tests
7. **Cache pre-commit** - Caches pre-commit hooks
8. **Run pre-commit hooks** - Executes all configured hooks:
   - VaultTool Encrypt
   - VaultTool Check Ignore
   - Pytest
   - Ruff (linting)
9. **Clean up test artifacts** - Removes files created during test execution

### 2. Test Job

**Purpose:** Runs the full test suite with coverage reporting.

**Matrix Strategy:** Tests against Python 3.10, 3.11, 3.12, and 3.13

**Steps:**
1. **Check out code**
2. **Set up Python**
3. **Install Poetry**
4. **Cache virtual environment**
5. **Install dependencies**
6. **Create test key file**
7. **Run tests with coverage** - Uses pytest with coverage tracking
8. **Upload coverage** - Uploads to Codecov (Python 3.12 only)
9. **Clean up test artifacts**

## Cleanup Strategy

Both jobs include comprehensive cleanup steps to prevent test artifacts from persisting:

### Files Removed:
- `*.vault` files (encrypted vault files created during tests)
- `tmp*` directories (temporary test directories)
- `.pytest_cache` (pytest cache)
- `.coverage` and `coverage.xml` (coverage reports)
- Orphaned `.vaulttool.yml` files (test configuration files)

### Cleanup Commands:
```bash
# Remove vault files
find . -name "*.vault" -type f -delete

# Remove temporary directories (excluding .venv)
find . -path "./.venv" -prune -o -type d -name "tmp*" -exec rm -rf {} + 2>/dev/null || true

# Remove pytest cache
rm -rf .pytest_cache

# Remove coverage files
rm -f .coverage coverage.xml

# Remove test config files (keep main .vaulttool.yml)
find . -path "./.venv" -prune -o -name ".vaulttool.yml" ! -path "./.vaulttool.yml" -type f -delete 2>/dev/null || true
```

## Caching Strategy

The workflow uses GitHub Actions caching to speed up runs:

### Virtual Environment Cache
- **Key:** `venv-{OS}-{Python-Version}-{poetry.lock-hash}`
- **Path:** `.venv`
- **Benefit:** Avoids reinstalling dependencies if `poetry.lock` hasn't changed

### Pre-commit Cache
- **Key:** `pre-commit-{OS}-{Python-Version}-{.pre-commit-config.yaml-hash}`
- **Path:** `~/.cache/pre-commit`
- **Benefit:** Avoids reinstalling pre-commit hooks

## Coverage Reporting

- Coverage is collected using `pytest-cov`
- Reports generated in XML and terminal formats
- Only Python 3.12 uploads to Codecov (to avoid duplicate reports)
- Coverage upload failures don't fail the CI (fail_ci_if_error: false)

## Python Version Support

**Tested Versions:**
- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13

**Note:** Python 3.14 is not yet released, so it's not included in the matrix.

## Configuration Files

### Poetry Dependencies

The workflow requires these dev dependencies in `pyproject.toml`:
```toml
[tool.poetry.group.dev.dependencies]
ruff = "*"
pre-commit = "*"
pytest = "^8.4.2"
pytest-cov = "*"
```

### Pre-commit Configuration

All pre-commit hooks must pass:
- vaulttool (encrypt)
- vaulttool (check-ignore)
- pytest
- ruff (linting)

## Best Practices

1. **Always run locally first:**
   ```bash
   pre-commit run --all-files
   ```

2. **Test with multiple Python versions locally using tox:**
   ```bash
   # Install tox
   pip install tox
   
   # Run tests across all Python versions
   tox
   ```

3. **Check workflow syntax before committing:**
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
   ```

4. **Monitor GitHub Actions tab** for workflow status

## Troubleshooting

### Job Fails Due to Leftover Files

If cleanup fails, check:
- File permissions (especially vault files with 600 permissions)
- Locked files or processes
- Virtual environment conflicts

**Solution:** The cleanup uses `|| true` to continue even if some files can't be deleted.

### Cache Issues

If dependencies seem stale:
1. Go to repository Settings → Actions → Caches
2. Delete specific caches
3. Re-run the workflow

### Python Version Not Available

If a Python version fails to install:
- Check Python 3.13 availability in GitHub Actions runners
- May need to wait for official runner image updates
- Consider using `actions/setup-python@v5` with deadsnakes PPA

## Maintenance

### Updating Python Versions

To add Python 3.14 (when released):
```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]
```

### Updating Poetry Version

Change in both jobs:
```yaml
- name: Install Poetry
  uses: snok/install-poetry@v1
  with:
    version: 1.9.0  # Update version here
```

### Adding More Cleanup

Add to the cleanup step:
```bash
# Example: Remove additional test artifacts
rm -rf build/ dist/ *.egg-info
```

## Status Badges

Add to README.md:
```markdown
![CI](https://github.com/yourusername/vaulttool/workflows/CI/badge.svg)
[![codecov](https://codecov.io/gh/yourusername/vaulttool/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/vaulttool)
```

## Further Reading

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Pre-commit Framework](https://pre-commit.com/)
- [Codecov Documentation](https://docs.codecov.com/)
