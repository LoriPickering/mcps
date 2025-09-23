#!/usr/bin/env python3
"""
Test runner script for MCP server test suite
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run the test suite"""

    project_root = Path(__file__).parent
    tests_dir = project_root / "tests"

    print("MCP Server Test Suite")
    print("=" * 50)
    print(f"Project root: {project_root}")
    print(f"Tests directory: {tests_dir}")
    print()

    # Check if tests directory exists
    if not tests_dir.exists():
        print("❌ Tests directory not found!")
        return 1

    # List test files
    test_files = list(tests_dir.glob("test_*.py"))
    print(f"Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {test_file.name}")
    print()

    # Run pytest with verbose output
    cmd = [
        sys.executable, "-m", "pytest",
        str(tests_dir),
        "-v",           # verbose
        "-s",           # don't capture output
        "--tb=short",   # shorter traceback format
        "--color=yes"   # colored output
    ]

    print("Running tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)