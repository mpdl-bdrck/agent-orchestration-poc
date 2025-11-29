#!/usr/bin/env python3
"""
Test runner for Google Sheets shared modules.

This script runs all unit tests for the sheets functionality.
Run from the tools/shared directory.
"""

import unittest
import sys
import os

# Add the parent directory to path so we can import shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

if __name__ == '__main__':
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
