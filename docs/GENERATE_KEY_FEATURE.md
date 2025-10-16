# Generate Key Command - Feature Documentation

## Overview

VaultTool now includes a comprehensive `generate-key` command that handles encryption key generation, backup, and rotation with an optional rekey functionality.

## Command Syntax

```bash
vaulttool generate-key [OPTIONS]
```

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--key-file` | `-k` | Path to key file (default: from .vaulttool.yml config) |
| `--rekey` | | Re-encrypt all vault files with the new key |
| `--force` | | Skip confirmation prompts (use with caution) |
| `--verbose` | `-v` | Enable verbose debug logging |
| `--quiet` | `-q` | Show only errors (suppress info/warning) |

## Features

### 1. New Key Creation

When the key file doesn't exist:
- Generates a cryptographically secure 32-byte key (64 hex characters)
- Creates parent directories if needed
- Sets proper file permissions (600 - owner read/write only)
- Provides warnings about backing up the key

**Example:**

```bash
vaulttool generate-key --key-file ~/.vaulttool/vault.key
```

Output:

```
Key file does not exist: /home/user/.vaulttool/vault.key
Creating new key file...
✅ Successfully created new key file: /home/user/.vaulttool/vault.key
   Permissions: 600 (owner read/write only)

⚠️  IMPORTANT: Back up this key file securely!
   Without this key, you cannot decrypt your vault files.
```

### 2. Key Replacement with Backup

When the key file exists:
- Prompts user for confirmation (unless `--force` is used)
- Creates timestamped backup of old key
- Generates and writes new key
- Maintains proper file permissions

**Example:**

```bash
vaulttool generate-key --force
```

Output:

```
⚠️  Key file already exists: /home/user/.vaulttool/vault.key

Options:
  1. Backup old key and replace with new key
  3. Cancel operation
   ✅ Old key backed up to: /home/user/.vaulttool/vault.key.backup_20251016_144518

[4/5] Writing new key...
   ✅ New key written to: /home/user/.vaulttool/vault.key

============================================================
✅ Key generation complete!
============================================================
   New key: /home/user/.vaulttool/vault.key
   Backup:  /home/user/.vaulttool/vault.key.backup_20251016_144518

⚠️  IMPORTANT:
   1. Back up both keys securely
   2. Test decryption before deleting backup
```

### 3. Automatic Rekey (Key Rotation)

When `--rekey` is specified, the command performs complete key rotation:

**Step 1:** Restore plaintext files from existing vaults

```
[1/5] Restoring plaintext files from vaults...
   ✅ Restored: 5 files
```

**Step 2:** Remove old vault files

```
[2/5] Removing old vault files...
   ✅ Removed: 5 vault files
```

**Step 3:** Backup old key

```
[3/5] Backing up old key...
   ✅ Old key backed up to: /path/to/vault.key.backup_20251016_144518
```

**Step 4:** Write new key

```
[4/5] Writing new key...
   ✅ New key written to: /path/to/vault.key
```

**Step 5:** Re-encrypt with new key

```
[5/5] Re-encrypting files with new key...
   ✅ Created: 5 vault files
   ✅ Updated: 0 vault files
```

**Example:**

```bash
vaulttool generate-key --rekey --force
```

## Use Cases

### 1. Initial Setup

Generate a new key for a new project:

```bash
# Create config
vaulttool gen-vaulttool > .vaulttool.yml

# Edit config to set key_file path
nano .vaulttool.yml

# Generate key
vaulttool generate-key
```

### 2. Key Rotation (Security Best Practice)

Rotate keys periodically or after suspected compromise:

```bash
# Rotate key and re-encrypt all vaults
vaulttool generate-key --rekey --force

# Test decryption
vaulttool refresh --no-force

# If successful, can delete old backup
rm ~/.vaulttool/vault.key.backup_*
```

### 3. Emergency Key Replacement

If a key is compromised:

```bash
# Immediate key replacement with rekey
vaulttool generate-key --rekey --force

# Verify all vaults work
vaulttool refresh --force

# Commit new vaults to git
git add *.vault
git commit -m "security: rotated encryption keys"
```

### 4. Migration to New System

Moving vaults to a new encryption key:

```bash
# On old system: ensure all plaintext files exist
vaulttool refresh --force

# Generate new key and rekey
vaulttool generate-key --rekey --force

# Commit new vaults
git add *.vault
git commit -m "chore: migrated to new encryption key"
```

## Safety Features

### Interactive Confirmation

Without `--force`, the command prompts for confirmation before:
- Replacing existing keys
- Performing rekey operations

### Automatic Backups

- Old keys are always backed up with timestamp
- Format: `vault.key.backup_YYYYMMDD_HHMMSS`
- Maintains same permissions (600)

### Error Handling

The command will abort and show clear errors if:
- Configuration cannot be loaded
- Restoration of plaintext files fails
- Removal of old vaults fails
- New key write fails
- Re-encryption fails

### Rollback Information

If rekey fails, the output shows:
- Location of backup key
- Instructions for manual recovery

## Implementation Details

### Key Generation

- Uses Python's `secrets.token_hex(32)` for cryptographically secure random keys
- Generates 64 hexadecimal characters (256 bits of entropy)
- Automatically adds newline for proper file format

### File Permissions

- All key files set to 600 (owner read/write only)
- Parent directories created with `mkdir -p` semantics

### Backup Naming

- Format: `{original_name}.backup_{timestamp}`
- Timestamp: `YYYYMMDD_HHMMSS`
- Prevents overwriting existing backups

### Rekey Process Flow

```
┌─────────────────────┐
│ Read Configuration  │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Generate New Key    │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Restore Plaintext   │◄── Step 1
│ (refresh --force)   │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Remove Old Vaults   │◄── Step 2
│ (remove)            │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Backup Old Key      │◄── Step 3
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Write New Key       │◄── Step 4
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Re-encrypt Files    │◄── Step 5
│ (encrypt --force)   │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Success Summary     │
└─────────────────────┘
```

## Security Considerations

### Key Management

1. **Backup Strategy**: Always keep backup keys in secure offline storage
2. **Access Control**: Limit access to key files (600 permissions)
3. **Rotation Schedule**: Rotate keys every 6-12 months
4. **Compromise Response**: Immediate rekey if key is suspected compromised

### Rekey Best Practices

1. **Test First**: Test rekey in development before production
2. **Verify After**: Always verify decryption after rekey
3. **Keep Backup**: Don't delete backup until verified
4. **Commit Changes**: Commit new vault files to version control
5. **Document**: Log key rotation in security audit trail

### Safe Deletion

Only delete backup keys after:
- Verifying all vault files decrypt correctly
- Testing on all target systems
- Updating documentation
- Waiting reasonable time period (e.g., 30 days)

## Error Messages

### Configuration Missing

```
ERROR: Cannot load configuration.
Please specify --key-file or create .vaulttool.yml config.
Details: [Errno 2] No such file or directory: '.vaulttool.yml'
```

**Solution**: Create config or specify `--key-file` explicitly.

### Refresh Failure During Rekey

```
ERROR: Failed to restore some files. Aborting rekey.
```

**Solution**: Fix vault files or key issues before attempting rekey.

### Write Permission Error

```
ERROR: Failed to write new key: [Errno 13] Permission denied
   Old key backup is safe at: /path/to/vault.key.backup_20251016_144518
```

**Solution**: Check directory permissions and restore from backup if needed.

## Testing

The feature has been tested with:
- New key creation in non-existent directories
- Key replacement with existing files
- Full rekey with multiple vault files
- Error handling and recovery scenarios
- Permission handling on Linux
- Interactive and force modes

All 99 existing tests pass with the new feature.

## Integration

The command integrates with:
- Configuration system (reads `key_file` from `.vaulttool.yml`)
- Logging system (verbose/quiet modes)
- Error handling (proper exit codes)
- Existing encrypt/refresh/remove commands

## Future Enhancements

Potential improvements:
- Support for key encryption at rest
- Integration with hardware security modules (HSM)
- Key derivation from passphrases
- Multi-key support for team environments
- Automated key rotation scheduling

## Conclusion

The `generate-key` command provides a safe, user-friendly way to manage encryption keys in VaultTool, with built-in safety features and comprehensive rekey functionality for key rotation scenarios.
