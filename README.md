# Vault Tool

<img src="docs/img/vaulttool_icon.png" alt="Vault Tool Icon" width="50%" /> 

![License: Apache-2](https://img.shields.io/badge/License-Apache%202-blue.svg)
![Python: 3.10–3.13](https://img.shields.io/badge/python-3.10--3.13-blue.svg)



A simple tool that allows you to automatically encrypt your secrets and configuration files so that they can be safely stored in your version control system.

## Features

- **Encrypts sensitive files**: Protects configuration files, API keys, and secrets by encrypting them.
- **Works with Git**: Lets you track changes to encrypted files without exposing secrets in your repository.
- **Detects changes automatically**: Updates encrypted files whenever the original files change.
- **Restores missing files**: Automatically decrypts files if the original is missing and a `.vault` file exists.
- **Refreshes plaintext from vaults**: On demand, overwrite existing plaintext from `.vault` files (with `--force`).
- **Uses OpenSSL encryption**: Secures your data with strong, industry-standard encryption.
- **Encrypts before commit**: Ensures files are encrypted before you commit them to version control.
- **Updates .gitignore for you**: Adds plain text files to `.gitignore` to prevent accidental commits of secrets.
- **Verifies file integrity**: Uses hashes to make sure encrypted files are always up to date.
- **Editor-friendly format**: Encrypted files are base64 encoded, making them easy to copy and paste.
- **Easy to use**: Integrates smoothly with your workflow and tools.
- **Keeps secrets safe**: Stores sensitive information securely and restricts access to authorized users.
- **Flexible configuration**: Lets you specify which files to encrypt and how to handle them using a config file.


## Requirements

- Python 3.10 or newer
- OpenSSL (for secure file encryption)

## Installation

### 1. Install OpenSSL

OpenSSL is required for secure file encryption. Install it based on your operating system:

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install openssl
```

**Linux (RHEL/CentOS/Fedora):**
```bash
sudo yum install openssl    # RHEL/CentOS
sudo dnf install openssl    # Fedora
```

**macOS:**
```bash
brew install openssl
```

**Windows:**
- Download from [OpenSSL for Windows](https://slproweb.com/products/Win32OpenSSL.html)
- Follow the installation wizard


### 2. Install Vault Tool (Recommended: Poetry)

#### Development/Local Installation
```bash
git clone https://github.com/jifox/vaulttool.git
cd vaulttool
poetry install
pre-commit install
```

#### Running the CLI
You can run the CLI directly with:
```bash
poetry run vaulttool
```

If you want to install the CLI globally (optional, for advanced users):
```bash
poetry build
pipx install dist/vaulttool-*.whl
```

### 3. Generate Encryption Key

To create a secure encryption key for your vault run the `./vaulttool-generate-key.sh` script
or execute the following commands:

```bash
# Create vaulttool directory in home
mkdir -p "$HOME/.vaulttool"

# Generate a 256-bit encryption key
openssl rand -hex 32 > "$HOME/.vaulttool/vault.key"

# Secure the key file (Unix/Linux/macOS)
chmod 600 "$HOME/.vaulttool/vault.key"
```

## Configuration

Vault Tool uses a YAML configuration file named `.vaulttool.yml` in your project directory to control which files are encrypted and how.

Example `.vaulttool.yml`:

```yaml
vaulttool:
  include_directories:
    - "src"
    - "configs"
  exclude_directories:
    - ".venv"
    - ".git"
    - "__pycache__"
  include_patterns:
    - "*.env"
    - "*.ini"
    - "*.json"
  exclude_patterns:
    - "*.log"
    - "*example*"
    - "*.vault"
  options:
    suffix: ".vault"           # Suffix for encrypted files
    openssl_path: "openssl"    # Path to OpenSSL binary
    algorithm: "aes-256-cbc"   # Encryption algorithm
    key_type: "file"           # Key storage type
    key_file: "vault.key"      # Path to encryption key file
```

**Configuration Options:**
- **`include_directories`**: List of directories to search for files to encrypt. Defaults to current directory if empty.
- **`exclude_directories`**: Directories to skip during encryption.
- **`include_patterns`**: Wildcard patterns for files to encrypt (e.g., `*.env`, `*.json`).
- **`exclude_patterns`**: Patterns for files to exclude. Defaults to `[*.vault]` (options.suffix).
- **`options`**: Encryption settings including:
  - `suffix`: File extension for encrypted files (default: `.vault`)
  - `openssl_path`: Path to OpenSSL binary (default: `openssl`)
  - `algorithm`: Encryption algorithm (default: `aes-256-cbc`)
  - `key_file`: Path to encryption key file

Edit `.vaulttool.yml` to match your project structure and security requirements.

## Usage

To encrypt your sensitive files, navigate to your project directory and run:

```bash
vaulttool
```

This will:
- ✅ Encrypt specified files based on the configuration in `.vaulttool.yml`
- ✅ Automatically detect changes in unencrypted files and update corresponding `.vault` files
- ✅ Add plain text files to `.gitignore` to prevent accidental commits of sensitive information
- ✅ Restore missing source files from existing `.vault` files

### Refresh plaintext from vaults

You can refresh (restore) plaintext files from existing `.vault` files.

- Restore only missing plaintext files (default behavior):
```bash
vaulttool
```

- Overwrite existing plaintext files from `.vault` files (force refresh):
```bash
vaulttool --force
```

The `--force` option also re-encrypts sources to update `.vault` files even when they already exist and the checksum
has not changed, ensuring the vaults are regenerated consistently (for example after changing algorithms or keys).

### Optional subcommands (advanced)

If you prefer explicit commands, the Typer CLI exposes subcommands:

```bash
# Re-encrypt sources; add --force to rewrite existing .vault files
python -m vaulttool.cli encrypt --force

# Refresh plaintext from vaults; defaults to overwriting
python -m vaulttool.cli refresh           # overwrite existing plaintext
python -m vaulttool.cli refresh --no-force  # only restore missing files
```

## Example Workflow

### Initial Setup
1. **Add secrets** to your project (e.g., `configs/secret.env`)
2. **Configure** `.vaulttool.yml` to match your files
3. **Run** `vaulttool` to encrypt files

### Daily Workflow
1. **Edit** your secret files as needed
2. **Run** `vaulttool` before committing to Git
3. **Commit** only `.vault` files (plain files are automatically ignored)
4. **If a plain file is deleted**, run `vaulttool` to restore it from its `.vault` file
5. **To discard local plaintext changes and refresh from vaults**, run `vaulttool --force`


## Pre-commit Installation

To enable automatic encryption and code checks before every commit, install pre-commit:

```bash
pip install pre-commit
```

Then enable it in your repository:

```bash
pre-commit install
```

This will ensure all configured hooks (including Vault Tool encryption, ignore checks, tests, and linting) run automatically before each commit.

## Pre-commit Integration

For automatic encryption before commits, add this to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: vaulttool
        name: Encrypt sensitive files
        entry: vaulttool
        language: system
        always_run: true
```

## Related Tools

- **[OpenSSL](https://www.openssl.org/)**: Industry-standard cryptographic library
- **[pipx](https://pypa.github.io/pipx/)**: Install and run Python applications in isolated environments
- **[pre-commit](https://pre-commit.com/)**: Framework for managing Git pre-commit hooks
- **[Git](https://git-scm.com/)**: Version control system

## Contributing

We welcome contributions to Vault Tool! Here's how you can help:

### How to Contribute
1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
4. **Make** your changes and add tests
5. **Run** tests to ensure everything works
6. **Commit** your changes (`git commit -m 'Add amazing feature'`)
7. **Push** to your branch (`git push origin feature/amazing-feature`)
8. **Open** a Pull Request

### Development Setup
```bash
git clone https://github.com/yourusername/vaulttool.git
cd vaulttool
pip install -e .[dev]
pre-commit install
```

## Troubleshooting

### Common Issues

#### ❌ OpenSSL not found
**Solution:** Make sure OpenSSL is installed and available in your system PATH.
```bash
# Test OpenSSL installation
openssl version
```

#### ❌ Permission denied
**Solution:** Run Vault Tool with appropriate permissions to access files.
```bash
# Check file permissions
ls -la ~/.vaulttool/vault.key
chmod 600 ~/.vaulttool/vault.key
```

#### ❌ Key file missing
**Solution:** Generate a key file as described in the installation section and update your `.vaulttool.yml`.

#### ❌ Configuration not found
**Solution:** Ensure `.vaulttool.yml` exists in your project root or specify the config path.

### Getting Help

- 📖 **Documentation**: Check this README for setup and usage instructions
- 🐛 **Bug Reports**: [Open an issue](https://github.com/yourusername/vaulttool/issues) on GitHub
- 💡 **Feature Requests**: [Start a discussion](https://github.com/yourusername/vaulttool/discussions) on GitHub

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---
