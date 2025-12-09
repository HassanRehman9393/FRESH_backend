#!/usr/bin/env python
"""
Test runner script for FRESH Backend
Provides convenient commands to run different test suites
"""
import sys
import subprocess
from pathlib import Path


def run_command(cmd):
    """Run a shell command and return the result"""
    print(f"\n🚀 Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print("""
FRESH Backend Test Runner

Usage: python run_tests.py [command]

Commands:
  all               Run all tests
  unit              Run only unit tests
  integration       Run only integration tests
  coverage          Run tests with coverage report
  auth              Run authentication tests
  detection         Run detection tests
  disease           Run disease detection tests
  weather           Run weather tests
  orchards          Run orchard tests
  images            Run image tests
  alerts            Run alert tests
  fast              Run fast tests (unit only)
  slow              Run slow tests (integration)
  verbose           Run all tests with verbose output
  last-failed       Run only last failed tests
  help              Show this help message

Examples:
  python run_tests.py all
  python run_tests.py coverage
  python run_tests.py auth
  python run_tests.py fast
        """)
        return 0

    command = sys.argv[1].lower()

    commands = {
        'all': ['pytest', '-v'],
        'unit': ['pytest', '-m', 'unit', '-v'],
        'integration': ['pytest', '-m', 'integration', '-v'],
        'coverage': ['pytest', '--cov=src', '--cov-report=html', '--cov-report=term-missing'],
        'auth': ['pytest', '-m', 'auth', '-v'],
        'detection': ['pytest', '-m', 'detection', '-v'],
        'disease': ['pytest', '-m', 'disease', '-v'],
        'weather': ['pytest', '-m', 'weather', '-v'],
        'orchards': ['pytest', '-m', 'orchards', '-v'],
        'images': ['pytest', '-m', 'images', '-v'],
        'alerts': ['pytest', '-m', 'alerts', '-v'],
        'fast': ['pytest', '-m', 'unit', '-v', '--tb=short'],
        'slow': ['pytest', '-m', 'slow', '-v'],
        'verbose': ['pytest', '-vv', '-s'],
        'last-failed': ['pytest', '--lf', '-v'],
        'help': None,
    }

    if command == 'help':
        main()
        return 0

    if command not in commands:
        print(f"❌ Unknown command: {command}")
        print("Run 'python run_tests.py help' for available commands")
        return 1

    return run_command(commands[command])


if __name__ == '__main__':
    sys.exit(main())
