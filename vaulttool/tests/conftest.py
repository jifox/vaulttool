"""Pytest configuration and fixtures for vaulttool tests."""

import os
import pytest


@pytest.fixture(autouse=True)
def preserve_cwd():
    """Automatically preserve and restore the current working directory for all tests.
    
    This fixture is autouse=True, so it runs for every test automatically.
    It ensures that if a test changes the current directory, it's restored
    after the test completes, preventing issues with VS Code's pytest plugin.
    """
    original_cwd = os.getcwd()
    try:
        yield
    finally:
        # Restore original directory, but only if it still exists
        if os.path.exists(original_cwd):
            os.chdir(original_cwd)
        else:
            # If original dir was deleted, try to change to a safe location
            # Use the parent of the original, or fall back to home
            parent = os.path.dirname(original_cwd)
            if os.path.exists(parent):
                os.chdir(parent)
            else:
                os.chdir(os.path.expanduser("~"))
