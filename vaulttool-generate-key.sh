#!/bin/bash
# vaulttool-generate-key.sh
# Generate a random 256-bit key for vaulttool and save to ~/.vaulttool/aes-gcm.key
set -e
KEYDIR="$HOME/.vaulttool"
KEYFILE="$KEYDIR/aes-gcm.key"

mkdir -p "$KEYDIR"
if [ -f "$KEYFILE" ]; then
    echo "Key file already exists: $KEYFILE"
    exit 1
fi
openssl rand -out "$KEYFILE" -base64 32
chmod 600 "$KEYFILE"
echo "Vault key generated at: $KEYFILE"
