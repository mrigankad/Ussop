#!/usr/bin/env python3
"""
Test Runner for Ussop
Run: python run_tests.py
"""
import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run all tests with coverage."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🧪 USSOP - Test Suite                                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("❌ pytest not installed. Run: pip install pytest pytest-cov")
        sys.exit(1)
    
    # Run tests
    args = [
        "-v",
        "--tb=short",
        "--strict-markers",
    ]
    
    # Add coverage if available
    try:
        import pytest_cov
        args.extend(["--cov=services", "--cov=models", "--cov-report=term-missing"])
    except ImportError:
        print("⚠️  pytest-cov not installed, running without coverage")
    
    # Add test path
    args.append("tests/")
    
    print(f"Running: pytest {' '.join(args)}\n")
    
    result = subprocess.run([sys.executable, "-m", "pytest"] + args)
    
    if result.returncode == 0:
        print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ✅ All Tests Passed!                                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    else:
        print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ❌ Some Tests Failed                                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    sys.exit(result.returncode)


if __name__ == "__main__":
    run_tests()
