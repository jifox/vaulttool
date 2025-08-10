# Bootstrap to allow running this file directly (without `-m vaulttool`)
if __package__ is None or __package__ == "":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "vaulttool"

from pathlib import Path
from shutil import which
import argparse

from .config import load_config  # existing relative import remains valid
from .core import encrypt_files, decrypt_missing_sources, check_unencrypted_files_ignored


def load_and_validate_config():
    """Load the configuration from the vaulttool config file and validate it.

    This function checks if the OpenSSL binary is available and if the key file exists.
    Raises RuntimeError if OpenSSL is not found or the key file does not exist.
    """
    config = load_config()
    # Validate that openssl is available
    openssl = config["options"].get("openssl_path", "openssl")
    if not which(openssl):
        raise RuntimeError(
            f"OpenSSL not found at {openssl}. Please install OpenSSL or specify the path in the config."
        )
    key_file = config["options"].get("key_file", None)
    if not key_file or not Path(key_file).exists():
        raise RuntimeError(f"Key file '{key_file}' does not exist. Please provide a valid key file in the config.")
    return config

 
def main():
    parser = argparse.ArgumentParser(description="VaultTool: encrypt and refresh secrets.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-encryption and overwrite plaintext from vaults.",
    )
    parser.add_argument(
        "--check-ignore",
        action="store_true",
        help="Check that plaintext files are ignored by Git and exit non-zero if not.",
    )
    # Ignore unrelated args (e.g., from pytest) when invoked programmatically
    args, _unknown = parser.parse_known_args()

    try:
        config = load_and_validate_config()
        encrypt_files(config, force=args.force)
        decrypt_missing_sources(config, force=args.force)
        if args.check_ignore:
            missing = check_unencrypted_files_ignored(config)
            if missing:
                print("The following plaintext files are not ignored by Git:")
                for m in missing:
                    print(f" - {m}")
                exit(1)
    except RuntimeError as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
