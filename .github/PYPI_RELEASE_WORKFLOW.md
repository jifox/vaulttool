# PyPI Release Workflow Documentation

## Overview

This document describes the automated PyPI release workflow that publishes VaultTool to PyPI when a version tag is pushed to the repository.

## Workflow Trigger

The release workflow triggers automatically when you push a tag starting with `v`:

```bash
# Example tags that trigger release:
git tag v2.0.0
git tag v2.0.1
git tag v1.0.0-beta.1
git tag v3.0.0-rc.1

# Push the tag to trigger release
git push origin v2.0.0
```

**Pattern:** `v*` (any tag starting with 'v')

## GitHub Secrets Setup

You need to configure a PyPI API token as a GitHub secret. Two options are available:

### Option 1: Repository Secret (Recommended for Most Cases)

**When to use:**

- Simple projects with trusted collaborators
- You want automatic releases without manual approval
- Single deployment target (PyPI only)

**Setup Steps:**

1. **Get PyPI Token:**
   - Go to <https://pypi.org/manage/account/token/>
   - Click "Add API token"
   - Token name: `vaulttool-github-actions`
   - Scope: Project: `vaulttool` (or "Entire account" for first release)
   - Copy the token (starts with `pypi-`)

2. **Add to GitHub:**
   - Go to: `https://github.com/jifox/vaulttool/settings/secrets/actions`
   - Click "New repository secret"
   - Name: `PYPI_TOKEN`
   - Value: Paste your PyPI token
   - Click "Add secret"

3. **Workflow Configuration:**

   ```yaml
   # In .github/workflows/release.yml
   - name: Publish to PyPI
     env:
       POETRY_PYPI_TOKEN_PYPI: ${{ secrets.PYPI_TOKEN }}
     run: poetry publish
   ```

**Pros:**

- Simple setup
- Automatic releases
- Available to all workflows
- No additional configuration needed

**Cons:**

- No manual approval required
- Anyone with write access can trigger release

### Option 2: Environment Secret (More Secure)

**When to use:**

- You want manual approval before publishing
- Multiple team members with varying trust levels
- Need deployment protection rules
- Want to restrict releases to specific branches
- Testing with test.pypi.org before production

**Setup Steps:**

1. **Create Environment:**
   - Go to: `https://github.com/jifox/vaulttool/settings/environments`
   - Click "New environment"
   - Name: `pypi-production`
   - Configure protection rules:
     - Required reviewers: Add yourself or team members
     - Wait timer: 5 minutes (optional cooldown period)
     - Deployment branches: Select "Selected branches"
       - Add pattern: `main` or `v*` tags
   - Click "Save protection rules"

2. **Add Environment Secret:**
   - In the environment page, under "Environment secrets"
   - Click "Add secret"
   - Name: `PYPI_TOKEN`
   - Value: Paste your PyPI token
   - Click "Add secret"

3. **Workflow Configuration:**

   ```yaml
   # In .github/workflows/release.yml
   jobs:
     release:
       name: Build and publish to PyPI
       runs-on: ubuntu-latest
       environment: pypi-production  # Add this line
       
       steps:
         - name: Publish to PyPI
           env:
             POETRY_PYPI_TOKEN_PYPI: ${{ secrets.PYPI_TOKEN }}
           run: poetry publish
   ```

**Pros:**

- Manual approval required
- Additional security layer
- Can restrict to specific branches
- Audit trail of who approved
- Can add wait timer
- Separate environments (test vs prod)

**Cons:**

- More complex setup
- Requires manual action to approve
- Releases are not fully automatic

## Workflow Features

### 1. Version Validation

The workflow automatically validates that the git tag version matches `pyproject.toml`:

```bash
# Tag: v2.0.0
# pyproject.toml: version = "2.0.0"
# Match - proceeds with release

# Tag: v2.0.1
# pyproject.toml: version = "2.0.0"
# Mismatch - fails with error
```

### 2. Pre-Release Testing

Before publishing, the workflow runs the full test suite:

```bash
poetry run pytest -v
```

If tests fail, the release is aborted.

### 3. Build Artifacts

The workflow builds both wheel and source distributions:

```
dist/
  vaulttool-2.0.0-py3-none-any.whl
  vaulttool-2.0.0.tar.gz
```

### 4. PyPI Publishing

Publishes to PyPI using the configured token:

```bash
poetry publish
```

### 5. GitHub Release

Automatically creates a GitHub release with:

- Release notes from CHANGELOG.md
- Build artifacts (wheel + source)
- Installation instructions
- Link to PyPI package

### 6. Pre-release Detection

Automatically marks releases as pre-release if version contains:

- `alpha` (e.g., v2.0.0-alpha.1)
- `beta` (e.g., v2.0.0-beta.2)
- `rc` (e.g., v2.0.0-rc.1)

## Release Process

### Standard Release

```bash
# 1. Update version in pyproject.toml
poetry version 2.0.1

# 2. Update CHANGELOG.md with release notes

# 3. Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 2.0.1"

# 4. Create and push tag
git tag v2.0.1
git push origin main
git push origin v2.0.1

# 5. Workflow automatically:
#    - Validates version
#    - Runs tests
#    - Builds package
#    - Publishes to PyPI
#    - Creates GitHub release
```

### Pre-release (Beta/RC)

```bash
# 1. Update version
poetry version 2.1.0-beta.1

# 2. Update CHANGELOG.md

# 3. Commit and tag
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 2.1.0-beta.1"
git tag v2.1.0-beta.1
git push origin main
git push origin v2.1.0-beta.1

# 4. Workflow publishes as pre-release
```

### Patch Release

```bash
# Quick patch release
poetry version patch  # 2.0.0 -> 2.0.1
git add pyproject.toml
git commit -m "chore: bump version to $(poetry version -s)"
git tag v$(poetry version -s)
git push origin main
git push origin v$(poetry version -s)
```

## Workflow File Location

`.github/workflows/release.yml`

## Monitoring Releases

### View Workflow Runs

- Go to: `https://github.com/jifox/vaulttool/actions/workflows/release.yml`
- See all release attempts and their status

### View Releases

- Go to: `https://github.com/jifox/vaulttool/releases`
- See all published releases

### View on PyPI

- Go to: `https://pypi.org/project/vaulttool/`
- See all published versions

## Troubleshooting

### Error: Version Mismatch

```
Error: Tag version (2.0.1) does not match pyproject.toml version (2.0.0)
```

**Solution:** Update `pyproject.toml` version to match the tag:

```bash
poetry version 2.0.1
git add pyproject.toml
git commit --amend --no-edit
git tag -d v2.0.1
git tag v2.0.1
git push origin main --force
git push origin v2.0.1 --force
```

### Error: Tests Failed

```
Tests failed
```

**Solution:** Fix failing tests before releasing:

```bash
poetry run pytest -v
# Fix issues
git add .
git commit -m "fix: resolve test failures"
git push origin main
# Then re-create tag
```

### Error: Package Already Exists

```
Error: File already exists
```

**Solution:** PyPI doesn't allow re-uploading the same version:

```bash
# Increment version
poetry version patch
git add pyproject.toml
git commit -m "chore: bump version"
# Create new tag
git tag v$(poetry version -s)
git push origin main
git push origin v$(poetry version -s)
```

### Error: Authentication Failed

```
Error: Invalid credentials
```

**Solutions:**

1. **Check token exists:**
   - Go to repository/environment secrets
   - Verify `PYPI_TOKEN` is set

2. **Token expired or revoked:**
   - Generate new token on PyPI
   - Update GitHub secret

3. **Wrong token scope:**
   - Token must have scope for the project
   - Or use "Entire account" scope

4. **Token not accessible:**
   - If using environment: Check environment name matches workflow
   - If using repository: Check secret name is `PYPI_TOKEN`

### Workflow Not Triggering

**Problem:** Pushed tag but workflow didn't run

**Solutions:**

1. **Check tag format:**

   ```bash
   # Must start with 'v'
   git tag v2.0.0  # Correct
   git tag 2.0.0   # Won't trigger
   ```

2. **Check workflow file:**

   ```bash
   # Verify file exists
   ls .github/workflows/release.yml
   
   # Check syntax
   python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"
   ```

3. **Check branch:**
   - Workflow must be on the branch where tag points
   - Ensure `.github/workflows/release.yml` is committed

## Testing the Workflow

### Dry Run (Test PyPI)

Before releasing to production PyPI, test with Test PyPI:

1. **Get Test PyPI token:**
   - <https://test.pypi.org/manage/account/token/>

2. **Add as GitHub secret:**
   - Name: `TEST_PYPI_TOKEN`

3. **Create test release workflow:**

   ```yaml
   # .github/workflows/test-release.yml
   on:
     push:
       tags:
         - 'test-v*'
   
   jobs:
     test-release:
       # ... same steps but:
       - name: Publish to Test PyPI
         env:
           POETRY_PYPI_TOKEN_TESTPYPI: ${{ secrets.TEST_PYPI_TOKEN }}
         run: |
           poetry config repositories.testpypi https://test.pypi.org/legacy/
           poetry config pypi-token.testpypi $POETRY_PYPI_TOKEN_TESTPYPI
           poetry publish -r testpypi
   ```

4. **Test with:**

   ```bash
   git tag test-v2.0.0
   git push origin test-v2.0.0
   ```

## Security Best Practices

1. **Use project-scoped tokens**
   - Limit token to specific project
   - Avoid "Entire account" scope if possible

2. **Use environment secrets with protection**
   - Add required reviewers
   - Use wait timers
   - Restrict to specific branches

3. **Rotate tokens regularly**
   - Update tokens every 6-12 months
   - Revoke old tokens after rotation

4. **Monitor releases**
   - Subscribe to release notifications
   - Review PyPI downloads/statistics
   - Check for unauthorized releases

5. **Use 2FA on PyPI**
   - Enable two-factor authentication
   - Secure your PyPI account

## Summary

| Aspect | Repository Secret | Environment Secret |
|--------|------------------|-------------------|
| **Setup Complexity** | Simple | Moderate |
| **Approval Required** | No | Yes (optional) |
| **Security Level** | Medium | High |
| **Best For** | Solo dev, trusted team | Teams, critical projects |
| **Release Speed** | Instant | Requires approval |

**Recommendation for VaultTool:** Start with **Repository Secret** for simplicity. Upgrade to **Environment Secret** if you add more contributors or need stricter control.

## Next Steps

1. Choose secret type (Repository or Environment)
2. Add PYPI_TOKEN to GitHub secrets
3. Update workflow if using environment secrets
4. Test with a pre-release (e.g., v2.0.1-rc.1)
5. Monitor first release workflow
6. Create actual release (v2.0.1)

The workflow is ready to use!
