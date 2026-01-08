#!/usr/bin/env python3
"""
Master test runner for poly-bot.
Runs unit tests and optionally integration tests.
"""
import sys
import subprocess
import argparse


def run_unit_tests():
    """Run unit tests (no external connections required)."""
    print("\n" + "=" * 70)
    print("RUNNING UNIT TESTS (No external connections)")
    print("=" * 70)

    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_config.py",
        "tests/test_models.py",
        "tests/test_ledger.py",
        "tests/test_execution_engine.py",
        "-v",
        "--tb=short"
    ]

    result = subprocess.run(cmd)
    return result.returncode == 0


def run_integration_tests_polymarket():
    """Run Polymarket integration tests (requires internet)."""
    print("\n" + "=" * 70)
    print("RUNNING POLYMARKET INTEGRATION TESTS (Requires internet)")
    print("=" * 70)

    cmd = [sys.executable, "tests/test_integration_polymarket.py"]
    result = subprocess.run(cmd)
    return result.returncode == 0


def run_integration_tests_ibkr():
    """Run IBKR integration tests (requires TWS/Gateway running)."""
    print("\n" + "=" * 70)
    print("RUNNING IBKR INTEGRATION TESTS (Requires TWS/Gateway)")
    print("=" * 70)

    cmd = [sys.executable, "tests/test_integration_ibkr.py"]
    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run poly-bot tests")
    parser.add_argument(
        "--unit-only",
        action="store_true",
        help="Run only unit tests (no external connections)"
    )
    parser.add_argument(
        "--integration-only",
        action="store_true",
        help="Run only integration tests"
    )
    parser.add_argument(
        "--skip-ibkr",
        action="store_true",
        help="Skip IBKR integration tests"
    )
    parser.add_argument(
        "--skip-polymarket",
        action="store_true",
        help="Skip Polymarket integration tests"
    )

    args = parser.parse_args()

    results = {}

    # Run unit tests
    if not args.integration_only:
        results['unit_tests'] = run_unit_tests()
    else:
        results['unit_tests'] = None

    # Run integration tests
    if not args.unit_only:
        if not args.skip_polymarket:
            results['polymarket_integration'] = run_integration_tests_polymarket()
        else:
            results['polymarket_integration'] = None

        if not args.skip_ibkr:
            results['ibkr_integration'] = run_integration_tests_ibkr()
        else:
            results['ibkr_integration'] = None
    else:
        results['polymarket_integration'] = None
        results['ibkr_integration'] = None

    # Summary
    print("\n" + "=" * 70)
    print("OVERALL TEST SUMMARY")
    print("=" * 70)

    for test_suite, passed in results.items():
        if passed is None:
            status = "⊘ SKIPPED"
        elif passed:
            status = "✓ PASSED"
        else:
            status = "✗ FAILED"

        print(f"{status:12} {test_suite.replace('_', ' ').title()}")

    # Overall result
    failures = [name for name, passed in results.items() if passed is False]

    if failures:
        print(f"\n✗ {len(failures)} test suite(s) failed: {', '.join(failures)}")
        return 1
    else:
        print("\n✓ All test suites passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
