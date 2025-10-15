#!/bin/bash
# vaulttool-generate-key.sh
# Generate a random 256-bit (32-byte) key for vaulttool and save to ~/.vaulttool/vault.key
# Uses Python's secrets module for cryptographically secure random key generation
set -e

KEYDIR="$HOME/.vaulttool"
KEYFILE="$KEYDIR/vault.key"

# Create directory if it doesn't exist
mkdir -p "$KEYDIR"

# Check if key file already exists
if [ -f "$KEYFILE" ]; then
    echo "Error: Key file already exists: $KEYFILE"
    echo "Remove existing key file first if you want to generate a new one."
    exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found in PATH"
    echo "Please install Python 3.10 or newer"
    exit 1
fi

# Generate a 256-bit (32-byte) key using Python's secrets module
# Output as hex string (64 hex characters = 32 bytes)
echo "Generating secure 256-bit encryption key..."
python3 -c "import secrets; print(secrets.token_hex(32))" > "$KEYFILE"

# Verify key was generated successfully
if [ ! -s "$KEYFILE" ]; then
    echo "Error: Failed to generate key file"
    rm -f "$KEYFILE"
    exit 1
fi

# Secure the key file (readable/writable by owner only)
chmod 600 "$KEYFILE"

echo "✓ Vault key successfully generated at: $KEYFILE"
echo "✓ Key file permissions set to 600 (owner read/write only)"
echo ""
echo "Key details:"
echo "  - Size: 32 bytes (256 bits)"
echo "  - Format: Hexadecimal string"
echo "  - Algorithm: Cryptographically secure random (Python secrets module)"
echo ""
echo "Next steps:"
echo "  1. Configure your .vaulttool.yml to reference this key file"
echo "  2. Keep this key secure and backed up"
echo "  3. Never commit this key to version control"
