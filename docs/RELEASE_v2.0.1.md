# VaultTool v2.0.1 Release Summary

**Release Date:** October 16, 2025

## Overview

Version 2.0.1 introduces a powerful new CLI command for encryption key management with comprehensive backup and rotation
capabilities, improved CLI help text formatting, enhanced testing infrastructure,
and automated PyPI publishing workflow.

## Quick Summary

### New Features
- **`generate-key` Command** - Complete encryption key lifecycle management with backup and rekey
- **Automated PyPI Publishing** - GitHub Actions workflow for seamless releases
- **Improved CLI Help** - Better formatted terminal output across all commands
- **VS Code Test Support** - Fixed pytest integration for Test Explorer

### Statistics
- **19 files changed**
- **2,316 additions** (+)
- **512 deletions** (-)
- **Net change**: +1,804 lines
- **All 99 tests passing** ✓

### Major File Changes
| File                            | Changes    | Description                                |
| ------------------------------- | ---------- | ------------------------------------------ |
| `vaulttool/cli.py`              | +474 lines | New generate-key command + help formatting |
| `docs/PYPI_RELEASE_WORKFLOW.md` | +451 lines | Complete release automation guide          |
| `docs/GENERATE_KEY_FEATURE.md`  | +371 lines | Feature documentation                      |
| `README.md`                     | +267 lines | Enhanced usage documentation               |
| `CHANGELOG.md`                  | +118 lines | Detailed changelog                         |
| `.github/workflows/release.yml` | +106 lines | PyPI publishing workflow                   |
| `docs/README.md`                | +102 lines | Documentation index                        |

### Key Changes Summary

#### New Features
1. **`generate-key` Command** - Complete encryption key lifecycle management
2. **Automated PyPI Publishing** - GitHub Actions workflow for releases
3. **Improved CLI Help Text** - Better formatted terminal output with preserved line breaks
4. **Test Infrastructure** - New pytest configuration for VS Code compatibility

#### Code Changes
- **vaulttool/cli.py** (+474 lines) - New `generate-key` command and improved help formatting
- **vaulttool/tests/conftest.py** (+29 lines, new file) - Auto-restore working directory fixture
- **vaulttool/tests/test_checksum_trigger.py** - Enhanced with proper directory handling
- **.github/workflows/release.yml** (+106 lines, new file) - Automated PyPI publishing

#### Documentation
- **docs/GENERATE_KEY_FEATURE.md** (+371 lines, new file) - Comprehensive feature documentation
- **docs/PYPI_RELEASE_WORKFLOW.md** (+451 lines, new file) - Complete release process guide
- **docs/README.md** (+102 lines, new file) - Documentation index
- **README.md** - Enhanced with generate-key usage and examples
- **CHANGELOG.md** - Detailed v2.0.1 changelog entry

#### Infrastructure
- **Removed**: `vaulttool-generate-key.sh` (replaced by native CLI command)
- **Removed**: `wip_pre-commit.yml` (housekeeping)
- **Moved**: `.github/GITHUB_ACTIONS_CI.md` → `docs/GITHUB_ACTIONS_CI.md`

## What's New

### New Command: `generate-key`

A complete solution for managing encryption keys throughout their lifecycle.

#### Key Features

1. **Secure Key Generation**
   - Cryptographically secure 32-byte keys (256-bit entropy)
   - Automatic directory creation
   - Proper file permissions (600)
   - Integration with configuration system

2. **Safe Key Replacement**
   - Timestamped backups of old keys
   - Interactive confirmation prompts
   - Force mode for automation
   - Clear operation summaries

3. **Automatic Rekey (Key Rotation)**
   - Complete 5-step automated process
   - Graceful error handling
   - Progress indicators
   - Rollback information on failure

#### Command Usage

```bash
# Generate new key
vaulttool generate-key

# Generate key in custom location
vaulttool generate-key --key-file ~/.vaulttool/vault.key

# Replace existing key
vaulttool generate-key --force

# Rotate key and re-encrypt all vaults
vaulttool generate-key --rekey --force
```

#### Options

| Option       | Short | Description                             |
| ------------ | ----- | --------------------------------------- |
| `--key-file` | `-k`  | Path to key file (default: from config) |
| `--rekey`    |       | Re-encrypt all vault files with new key |
| `--force`    |       | Skip confirmation prompts               |
| `--verbose`  | `-v`  | Enable debug logging                    |
| `--quiet`    | `-q`  | Show errors only                        |

## Use Cases

### 1. Initial Setup

```bash
vaulttool gen-vaulttool > .vaulttool.yml
vaulttool generate-key
vaulttool encrypt
```

### 2. Periodic Key Rotation (Security Best Practice)

```bash
vaulttool generate-key --rekey --force
git add *.vault
git commit -m "security: rotated encryption keys"
```

### 3. Emergency Key Replacement

```bash
# Immediate replacement after suspected compromise
vaulttool generate-key --rekey --force
vaulttool refresh --force  # Verify
```

### 4. Migration to New Key

```bash
# Move to new key management system
vaulttool generate-key --key-file /new/path/vault.key --rekey
```

## Safety Features

- Interactive confirmations before destructive operations
- Automatic timestamped backups (`vault.key.backup_YYYYMMDD_HHMMSS`)
- Proper file permissions (600) enforced
- Comprehensive error handling with recovery instructions
- Step-by-step progress reporting
- Verification prompts for safety

## Rekey Process

When `--rekey` is specified, the command performs:

```
[1/5] Restoring plaintext files from vaults...
      ↓
[2/5] Removing old vault files...
      ↓
[3/5] Backing up old key...
      ↓
[4/5] Writing new key...
      ↓
[5/5] Re-encrypting files with new key...
      ↓
✅ Success Summary
```

## Security Best Practices

1. **Regular Rotation**: Rotate keys every 6-12 months
2. **Backup Strategy**: Keep backup keys in secure offline storage
3. **Access Control**: Limit access to key files (600 permissions)
4. **Verification**: Always test decryption after rotation
5. **Documentation**: Log key rotations in security audit trail

## Documentation Updates

- **README.md**: Added comprehensive `generate-key` documentation
  - New "Generate or rotate encryption key" section in Usage
  - Enhanced "Generate Encryption Key" section in Installation
  - Updated Table of Contents

- **docs/GENERATE_KEY_FEATURE.md**: Detailed feature documentation
  - Command syntax and options
  - Use cases and examples
  - Safety features
  - Implementation details
  - Security considerations
  - Error messages and solutions
  - Process flow diagrams

- **docs/PYPI_RELEASE_WORKFLOW.md**: Complete PyPI release automation guide
  - GitHub Actions workflow configuration
  - Release process documentation
  - Security best practices
  - Troubleshooting guide

- **docs/README.md**: Documentation directory index

- **docs/GITHUB_ACTIONS_CI.md**: Moved from `.github/` for better organization

## CLI Improvements

### Improved Help Text Formatting

All CLI commands now use Click's `\b` directive for proper terminal formatting:

- **Main app help**: Preserved line breaks and indentation for better readability
- **All subcommands**: Enhanced help text with proper formatting
  - `generate-key` - Structured sections with examples
  - `version` - Simplified output
  - `gen-vaulttool` - Clear usage instructions
  - `remove` - Concise description
  - `encrypt` - Options and examples properly formatted
  - `refresh` - Options and examples properly formatted
  - `check-ignore` - Clear purpose statement

**Before:**
```
Encrypts sensitive files using AES-256-CBC and manages their encrypted counterparts. Key Options: encrypt --force Re-encrypt all files (ignores checksums) refresh --no-force Only restore missing files...
```

**After:**
```
Encrypts sensitive files using AES-256-CBC and manages their encrypted counterparts.

Key Options:
  encrypt --force      Re-encrypt all files (ignores checksums)
  refresh --no-force   Only restore missing files
  generate-key         Create new encryption key with backup
```

## Testing Improvements

### VS Code Pytest Integration

**New File: `vaulttool/tests/conftest.py`**

Added an auto-use pytest fixture to fix issues with VS Code's Test Explorer:

```python
@pytest.fixture(autouse=True)
def preserve_cwd():
    """Automatically preserve and restore the current working directory."""
```

**Features:**
- Automatically runs for all tests
- Saves and restores working directory
- Prevents `FileNotFoundError` in VS Code Test Explorer
- Handles edge cases where directories are deleted during tests

**Fixed Test: `test_checksum_trigger.py`**
- Added explicit try-finally blocks
- Proper directory restoration before temp directory cleanup
- Prevents VS Code pytest plugin failures

**VS Code Configuration:**
```json
{
  "python.testing.pytestArgs": ["vaulttool/tests"],
  "python.testing.cwd": "${workspaceFolder}"
}
```

All 99 tests now pass in both terminal and VS Code Test Explorer.

## DevOps & Automation

### GitHub Actions - PyPI Publishing

**New File: `.github/workflows/release.yml`**

Automated release workflow that triggers on version tags:

**Features:**
- Automatic triggering on `v*` tags (e.g., `v2.0.1`)
- Version validation against `pyproject.toml`
- Poetry-based build process
- Automated PyPI publishing via trusted publishing
- Build artifact retention (30 days)

**Release Process:**
```bash
git tag v2.0.1
git push origin v2.0.1
# GitHub Actions automatically builds and publishes to PyPI
```

**Security:**
- Uses OpenID Connect (OIDC) trusted publishing
- No API tokens stored in repository
- Configured through PyPI project settings

## Documentation Updates

## Testing

- All 99 tests pass
- New key creation tested
- Key replacement with backup tested
- Full rekey process tested
- Error handling verified
- File permissions verified
- Backup naming verified
- Decryption after rekey verified

## Compatibility

- **Backward Compatible**: No breaking changes
- **Python**: 3.10+
- **Dependencies**: No new dependencies
- **Configuration**: No changes required
- **VS Code**: Enhanced test runner support
- **CI/CD**: New GitHub Actions workflow for automated releases

## Commit History

This release includes commits from the following features and fixes:

1. **feat-pypi-publishing**: PyPI automation and generate-key command
2. **5-fix-helptext**: CLI help text formatting improvements  
3. **6-python-tests-in-vscode**: VS Code pytest integration fixes

**Merged Pull Requests:**
- #9: Python tests in VS Code
- #8: Fix help text formatting
- #7: PyPI publishing workflow
- #4: Sync with main branch

## Testing

## Upgrade Instructions

```bash
# Using Poetry
poetry update vaulttool

# Using pip
pip install --upgrade vaulttool

# Verify version
vaulttool version  # Should show 2.0.1
```

## Technical Details

### Implementation

- Uses `secrets.token_hex(32)` for cryptographically secure keys
- Integrates with existing configuration system
- Full error handling with `try/except` blocks
- Atomic operations with clear rollback information
- Proper file permission handling (600 on all key files)

### Files Modified

**Core Application:**
- `vaulttool/cli.py` - Added `generate_key_cmd()` function (~250 lines) + improved help text formatting
- `vaulttool/__init__.py` - Minor refactoring
- `vaulttool/config.py` - Code improvements
- `vaulttool/core.py` - Enhanced error handling and logging
- `vaulttool/utils.py` - Improved utility functions
- `pyproject.toml` - Updated version to 2.0.1

**Testing:**
- `vaulttool/tests/conftest.py` - New file with `preserve_cwd` fixture
- `vaulttool/tests/test_checksum_trigger.py` - Enhanced directory handling

**Documentation:**
- `README.md` - Enhanced with new command documentation
- `CHANGELOG.md` - Added v2.0.1 comprehensive entry
- `docs/GENERATE_KEY_FEATURE.md` - New comprehensive feature guide
- `docs/PYPI_RELEASE_WORKFLOW.md` - New release automation guide
- `docs/README.md` - New documentation index
- `docs/GITHUB_ACTIONS_CI.md` - Moved from `.github/` directory
- `docs/RELEASE_v2.0.1.md` - This release summary

**DevOps:**
- `.github/workflows/release.yml` - New PyPI publishing workflow

**Removed:**
- `vaulttool-generate-key.sh` - Replaced by native CLI command
- `wip_pre-commit.yml` - Housekeeping cleanup

## Code Quality Improvements

### Logging and Error Handling
- Enhanced error messages throughout codebase
- Better exception handling in crypto operations
- Improved debug logging for troubleshooting
- Consistent error reporting patterns

### Code Refactoring
- Improved function organization in `cli.py`
- Better separation of concerns
- Enhanced docstrings and comments
- Consistent code style

## Breaking Changes

**None** - This release is fully backward compatible.

### Performance

- No performance impact on existing operations
- Key generation: < 100ms
- Rekey operation: Depends on number of vault files

## Migration Guide

No migration required - this is a pure addition with no breaking changes.

### For New Users

```bash
pip install vaulttool
vaulttool gen-vaulttool > .vaulttool.yml
nano .vaulttool.yml  # Configure your paths
vaulttool generate-key
vaulttool encrypt
```

### For Existing Users

Simply upgrade and start using the new command:

```bash
pip install --upgrade vaulttool
vaulttool generate-key --help
```

## Future Enhancements

Potential future improvements:

- Key encryption at rest
- HSM integration
- Key derivation from passphrases
- Multi-key support for teams
- Automated rotation scheduling

## Contributors

- Josef Fuchs - Lead Developer

## Resources

- **GitHub**: <https://github.com/jifox/vaulttool>
- **PyPI**: <https://pypi.org/project/vaulttool/>
- **Documentation**: [README.md](../README.md)
- **Feature Guide**: [GENERATE_KEY_FEATURE.md](GENERATE_KEY_FEATURE.md)
- **Changelog**: [CHANGELOG.md](../CHANGELOG.md)

## Support

- **Bug Reports**: [GitHub Issues](https://github.com/jifox/vaulttool/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jifox/vaulttool/discussions)
- **Built-in Help**: `vaulttool generate-key --help`

---

**Ready to upgrade?** Simply run `pip install --upgrade vaulttool` or `poetry update vaulttool`

**Questions?** Check the [GENERATE_KEY_FEATURE.md](GENERATE_KEY_FEATURE.md) documentation for detailed usage examples and troubleshooting.
