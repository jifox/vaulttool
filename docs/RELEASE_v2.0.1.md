# VaultTool v2.0.1 Release Summary

**Release Date:** October 16, 2025

## Overview

Version 2.0.1 introduces a powerful new CLI command for encryption key management with comprehensive backup and rotation capabilities.

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

| Option | Short | Description |
|--------|-------|-------------|
| `--key-file` | `-k` | Path to key file (default: from config) |
| `--rekey` | | Re-encrypt all vault files with new key |
| `--force` | | Skip confirmation prompts |
| `--verbose` | `-v` | Enable debug logging |
| `--quiet` | `-q` | Show errors only |

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

- `vaulttool/cli.py` - Added `generate_key_cmd()` function (~250 lines)
- `README.md` - Enhanced documentation
- `CHANGELOG.md` - Added v2.0.1 entry
- `pyproject.toml` - Updated version to 2.0.1
- `docs/GENERATE_KEY_FEATURE.md` - Created comprehensive feature doc

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
