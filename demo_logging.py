#!/usr/bin/env python3
"""Demo script showing VaultTool's new logging capabilities."""

import tempfile
import os
from pathlib import Path
import sys

# Add vaulttool to path
sys.path.insert(0, str(Path(__file__).parent))

from vaulttool import setup_logging
from vaulttool.core import VaultTool
import logging


def demo_logging_levels():
    """Demonstrate different logging levels."""

    print("="*70)
    print("VaultTool v2.0 - Logging & Error Handling Demo")
    print("="*70)
    print()

    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        # Create key file
        key_file = Path(tmpdir) / "demo.key"
        key_file.write_text("demo-key-16-bytes-for-testing-purposes-only")

        # Create config
        config_file = Path(tmpdir) / ".vaulttool.yml"
        config_file.write_text(f"""
vaulttool:
  include_directories: ["."]
  exclude_directories: []
  include_patterns: ["*.env"]
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_file}"
""")

        # Create some test files
        (Path(tmpdir) / "config.env").write_text("SECRET=demo123")
        (Path(tmpdir) / "database.env").write_text("DB_PASSWORD=secret456")

        # Demo 1: INFO level (default)
        print("📊 Demo 1: INFO Level Logging (Default)")
        print("-" * 70)
        setup_logging(level=logging.INFO, include_timestamp=False)
        vt = VaultTool()
        result = vt.encrypt_task()
        print(f"\nResult: {result['created']} created, {result['failed']} failed")
        print()

        # Demo 2: DEBUG level (verbose)
        print("\n📊 Demo 2: DEBUG Level Logging (--verbose)")
        print("-" * 70)
        setup_logging(level=logging.DEBUG, include_timestamp=False)

        # Remove source files to trigger refresh
        (Path(tmpdir) / "config.env").unlink()
        (Path(tmpdir) / "database.env").unlink()

        vt2 = VaultTool()
        result = vt2.refresh_task(force=True)
        print(f"\nResult: {result['succeeded']} succeeded, {result['failed']} failed")
        print()

        # Demo 3: ERROR level (quiet)
        print("\n📊 Demo 3: ERROR Level Logging (--quiet)")
        print("-" * 70)
        setup_logging(level=logging.ERROR, include_timestamp=False)
        print("(Only errors would be shown - none expected here)")

        vt3 = VaultTool()
        result = vt3.encrypt_task()
        print(f"Result: {result['updated']} updated")
        print()

        # Demo 4: Error handling
        print("\n📊 Demo 4: Error Handling Demo")
        print("-" * 70)
        setup_logging(level=logging.INFO, include_timestamp=False)

        # Create a malformed vault file
        malformed = Path(tmpdir) / "broken.env.vault"
        malformed.write_text("only-one-line")

        vt4 = VaultTool()
        result = vt4.refresh_task(force=True)
        print(f"\nResult: {result['succeeded']} succeeded, {result['failed']} failed")
        if result['errors']:
            print(f"Errors captured: {len(result['errors'])}")
            for file, error in result['errors']:
                print(f"  - {Path(file).name}: {error}")
        print()

        # Demo 5: Summary display
        print("\n📊 Demo 5: Operation Summary")
        print("-" * 70)

        # Clean up and re-encrypt everything
        for vault in Path(tmpdir).glob("*.vault"):
            vault.unlink()

        result = vt4.encrypt_task(force=True)

        # Display summary like CLI does
        print("\n" + "="*60)
        print("Encrypt Summary:")
        print(f"  Total:    {result['total']}")
        print(f"  Created:  {result['created']}")
        print(f"  Updated:  {result['updated']}")
        print(f"  Skipped:  {result['skipped']}")
        print(f"  Failed:   {result['failed']}")
        print("="*60)
        print()

    print("="*70)
    print("✅ Demo Complete!")
    print("="*70)
    print()
    print("Key Features Demonstrated:")
    print("  ✅ INFO level logging (default)")
    print("  ✅ DEBUG level logging (--verbose)")
    print("  ✅ ERROR level logging (--quiet)")
    print("  ✅ Error aggregation and tracking")
    print("  ✅ Summary statistics")
    print("  ✅ Graceful error handling")
    print()
    print("Try it yourself:")
    print("  vaulttool encrypt           # Normal logging")
    print("  vaulttool --verbose refresh # Detailed debug logs")
    print("  vaulttool --quiet encrypt   # Errors only")
    print()


if __name__ == "__main__":
    demo_logging_levels()
