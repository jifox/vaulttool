def remove_vault_files(config):
    """Delete all vault files matching the configured suffix in the include directories."""
    suffix = config["options"].get("suffix", ".vault")
    include_dirs = config.get("include_directories", ["."])
    removed = []
    for dir in include_dirs:
        for vault_file in Path(dir).rglob(f"*{suffix}"):
            try:
                vault_file.unlink()
                removed.append(str(vault_file))
            except Exception as e:
                print(f"Failed to remove {vault_file}: {e}")
    return removed
import os
from pathlib import Path
import subprocess
from .crypto import encrypt_file
from .utils import compute_checksum, encode_base64

# Flag to indicate running under pre-commit/CI to avoid touching .gitignore
VAULTTOOL_PRECOMMIT: bool = bool(os.environ.get("VAULTTOOL_PRECOMMIT"))


def decrypt_missing_sources(config, force: bool = False):
    """
    For each .vault file found in the configured directories, if the corresponding source file does not exist,
    decrypt the .vault file and restore the source file using OpenSSL and the configured key.
    """
    suffix = config["options"].get("suffix", ".vault")
    key_file = config["options"].get("key_file")
    algorithm = config["options"].get("algorithm", "aes-256-cbc")
    openssl_path = config["options"].get("openssl_path", "openssl")
    include_dirs = config.get("include_directories", ["."])
    for dir in include_dirs:
        for vault_file in Path(dir).rglob(f"*{suffix}"):
            source_file = vault_file.with_suffix("")
            if source_file.exists() and not force:
                # Skip existing files unless forcing a refresh
                continue
            with open(vault_file, "r") as vf:
                lines = vf.readlines()
                if len(lines) < 2:
                    continue  # invalid vault file
                encrypted_b64 = lines[1].strip()
            import base64
            encrypted = base64.b64decode(encrypted_b64)
            tmp_enc = str(vault_file) + ".dec.tmp"
            with open(tmp_enc, "wb") as df:
                df.write(encrypted)
            # Decrypt using OpenSSL
            os.system(
                f"{openssl_path} enc -d -{algorithm} -pbkdf2 -in {tmp_enc} "
                f"-out {source_file} -pass file:{key_file}"
            )
            os.remove(tmp_enc)
            print(f"Restored source file: {source_file} from vault: {vault_file}")


def encrypt_files(config, force: bool = False):
    """
    Encrypts files matching patterns in the specified directories according to the configuration.

    - Encrypts files using OpenSSL and writes a .vault file containing the checksum and base64-encoded data.
    - Only re-encrypts if the source file's checksum changes.
    - Automatically adds the source files to the project's .gitignore to prevent accidental commits.
    - Uses include/exclude directories and patterns from the config.
    """
    include_dirs = config.get("include_directories", ["."])
    exclude_dirs = set(config.get("exclude_directories", []))
    include_patterns = config.get("include_patterns", [])
    exclude_patterns = set(config.get("exclude_patterns", []))
    suffix = config["options"].get("suffix", ".vault")
    key_file = config["options"].get("key_file")
    algorithm = config["options"].get("algorithm", "aes-256-cbc")
    openssl_path = config["options"].get("openssl_path", "openssl")

    # In pre-commit/CI runs, avoid touching repo .gitignore to prevent hook failures
    disable_gitignore = VAULTTOOL_PRECOMMIT and (Path(".git").exists())
    gitignore_lines = set()
    if not disable_gitignore:
        gitignore_path = Path(".gitignore")
        # Ensure .gitignore exists
        if not gitignore_path.exists():
            gitignore_path.touch()
        # Read existing .gitignore entries
        with open(gitignore_path, "r") as gi:
            gitignore_lines = set(line.strip() for line in gi if line.strip())

    files_to_ignore = set()

    # Automatically add key_file to .gitignore if not present
    if key_file and not disable_gitignore:
        rel_key_path = os.path.relpath(key_file, Path().absolute())
        if rel_key_path not in gitignore_lines:
            with open(gitignore_path, "a") as gi:
                gi.write(f"{rel_key_path}\n")
            print(f"Added key file to .gitignore: {rel_key_path}")

    for dir in include_dirs:
        for pattern in include_patterns:
            for file_path in Path(dir).rglob(pattern):
                if any(file_path.match(ex_pat) for ex_pat in exclude_patterns):
                    continue
                if any(ex_dir in str(file_path) for ex_dir in exclude_dirs):
                    continue
                vault_path = file_path.with_suffix(file_path.suffix + suffix)
                checksum = compute_checksum(file_path)
                vault_checksum = None
                if vault_path.exists():
                    with open(vault_path, "r") as vf:
                        first_line = vf.readline().strip()
                        vault_checksum = first_line if first_line else None
                if not vault_path.exists() or force:
                    # Encrypt file to temp, then encode and write .vault file
                    encrypt_file(str(file_path), str(vault_path) + ".tmp", key_file, algorithm, openssl_path)
                    with open(str(vault_path) + ".tmp", "rb") as ef:
                        encoded = encode_base64(ef.read()).decode()
                    os.remove(str(vault_path) + ".tmp")
                    with open(vault_path, "w") as vf:
                        vf.write(checksum + "\n" + encoded + "\n")
                    action = "Updated" if vault_path.exists() and force else "Created"
                    print(f"{action} vault file: {vault_path} for source: {file_path}")
                elif checksum != vault_checksum:
                    # Encrypt file to temp, then encode and write .vault file
                    encrypt_file(str(file_path), str(vault_path) + ".tmp", key_file, algorithm, openssl_path)
                    with open(str(vault_path) + ".tmp", "rb") as ef:
                        encoded = encode_base64(ef.read()).decode()
                    os.remove(str(vault_path) + ".tmp")
                    with open(vault_path, "w") as vf:
                        vf.write(checksum + "\n" + encoded + "\n")
                    print(f"Updated vault file: {vault_path} for source: {file_path}")
                # Add source file to ignore list
                rel_path = os.path.relpath(file_path, Path().absolute())
                files_to_ignore.add(rel_path)

    # Update .gitignore if needed
    new_ignores = [f for f in files_to_ignore if f not in gitignore_lines]
    if new_ignores and not disable_gitignore:
        with open(gitignore_path, "a") as gi:
            for f in new_ignores:
                gi.write(f"{f}\n")


def check_unencrypted_files_ignored(config) -> list[str]:
    """Return a list of plaintext files that should be ignored but are not.

    Identifies plaintext files using include/exclude directories and patterns from the config
    and checks with `git check-ignore` whether they are ignored by .gitignore. Files that are
    not ignored are returned for reporting/failing in hooks.
    """
    include_dirs = config.get("include_directories", ["."])
    exclude_dirs = set(config.get("exclude_directories", []))
    include_patterns = config.get("include_patterns", [])
    exclude_patterns = set(config.get("exclude_patterns", []))

    candidates: list[Path] = []
    for dir in include_dirs:
        for pattern in include_patterns:
            for file_path in Path(dir).rglob(pattern):
                if any(file_path.match(ex_pat) for ex_pat in exclude_patterns):
                    continue
                if any(ex_dir in str(file_path) for ex_dir in exclude_dirs):
                    continue
                candidates.append(file_path)

    not_ignored: list[str] = []
    for fp in candidates:
        try:
            res = subprocess.run(
                ["git", "check-ignore", "-q", str(fp)],
                capture_output=True,
                text=True,
            )
            # exit code 0 => ignored, 1 => not ignored, 128 => error
            if res.returncode == 1:
                not_ignored.append(str(fp))
            elif res.returncode == 128:
                # Not a git repo or error; treat as not ignored for safety
                not_ignored.append(str(fp))
        except FileNotFoundError:
            # git not available; conservatively report as not ignored
            not_ignored.append(str(fp))

    return not_ignored
