# Testing Guide

This document describes all available tests and how to run them.

## Setup

First, install all dependencies:

```bash
# Option 1: Using pip
pip install -r requirements.txt

# Option 2: Using the package
pip install -e .
```

## Test Overview

### Unit Tests (No External Connections Required)

These tests validate core functionality without requiring IBKR or Polymarket connections:

1. **test_config.py** - Configuration loading and validation
2. **test_models.py** - Pydantic models (TradeIntent)
3. **test_ledger.py** - SQLite/CSV ledger operations
4. **test_execution_engine.py** - Yield adjustment and arb calculations

### Integration Tests (Require External Services)

These tests connect to real services but remain read-only:

1. **test_integration_polymarket.py** - Polymarket API tests (requires internet)
2. **test_integration_ibkr.py** - IBKR TWS/Gateway tests (requires TWS/Gateway running)

## Running Tests

### Quick Start: Run All Unit Tests

```bash
# Run all unit tests (no external connections)
python3 -m pytest tests/test_config.py tests/test_models.py tests/test_ledger.py tests/test_execution_engine.py -v
```

### Using the Test Runner

```bash
# Run all tests (unit + integration)
python3 run_tests.py

# Run only unit tests
python3 run_tests.py --unit-only

# Run only integration tests
python3 run_tests.py --integration-only

# Skip IBKR tests (if TWS not running)
python3 run_tests.py --skip-ibkr

# Skip Polymarket tests (if offline)
python3 run_tests.py --skip-polymarket
```

### Individual Test Suites

```bash
# Config tests
python3 -m pytest tests/test_config.py -v

# Model tests
python3 -m pytest tests/test_models.py -v

# Ledger tests
python3 -m pytest tests/test_ledger.py -v

# Execution engine tests
python3 -m pytest tests/test_execution_engine.py -v

# Polymarket integration (requires internet)
python3 tests/test_integration_polymarket.py

# IBKR integration (requires TWS/Gateway)
python3 tests/test_integration_ibkr.py
```

## What Each Test Suite Validates

### test_config.py
- ✓ Settings load from .env correctly
- ✓ Default values are correct
- ✓ ALLOW_POLYMARKET_EXECUTION is False (critical safety check)
- ✓ Risk-free rate is reasonable
- ✓ IBKR connection settings are valid

**Expected Result**: All tests pass

### test_models.py
- ✓ TradeIntent can be created with required fields
- ✓ Optional fields work correctly
- ✓ Timestamp is auto-generated
- ✓ Field validation works (side, mode, status)
- ✓ Pydantic model works correctly

**Expected Result**: All tests pass

### test_ledger.py
- ✓ Database initialization creates tables
- ✓ Trades can be recorded
- ✓ Trade status can be updated
- ✓ Trades can be filtered by status, venue, symbol
- ✓ CSV export works
- ✓ PnL calculation works for buy/sell trades

**Expected Result**: All tests pass

### test_execution_engine.py
- ✓ ExecutionEngine initializes correctly
- ✓ Paper/live mode validation works
- ✓ Yield-adjusted fair value calculation is correct
- ✓ Arb spread calculation is correct
- ✓ Edge cases handled (negative days, >100% probability)

**Expected Result**: All tests pass

Example calculations verified:
- p_poly=0.48, days=45, r=0.045 → fair_value ≈ 0.4827
- Arb detection works with configurable thresholds

### test_integration_polymarket.py
- ✓ Can fetch markets from Gamma API
- ✓ Can parse market data (question, ID, dates)
- ✓ Can fetch order book (may be empty for some markets)
- ✓ Can calculate liquidity-weighted probability
- ✓ All operations are read-only (no execution)

**Expected Result**: Should pass if internet is available
**Acceptable**: Order book may be empty for some markets (not a failure)

### test_integration_ibkr.py
- ✓ Can connect to TWS/Gateway
- ✓ Can look up contract details (tests with SPY)
- ✓ Can request market data
- ✓ Can query positions
- ✓ Can search for ForecastEx contracts

**Expected Result**:
- Connection test must pass
- Contract lookup should pass for SPY
- Market data may show N/A outside market hours (acceptable)
- ForecastEx lookup may not find contracts (acceptable)

**Prerequisites**:
- TWS or IB Gateway must be running
- API connections enabled (Global Config → API → Settings)
- Correct port configured (4002 for paper, 7496 for live)

## Troubleshooting

### Import Errors

```
ModuleNotFoundError: No module named 'pydantic_settings'
```

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### IBKR Connection Failed

```
✗ Error connecting to IBKR: [Errno 61] Connection refused
```

**Solution**:
1. Make sure TWS or IB Gateway is running
2. Enable API in TWS: File → Global Configuration → API → Settings
   - ☑ Enable ActiveX and Socket Clients
   - ☑ Read-Only API (recommended)
3. Verify port in .env matches TWS:
   - Paper trading: 4002
   - Live trading: 7496
4. Check client ID is unique (default: 1)

### Polymarket Tests Fail

```
✗ Error fetching markets: Connection timeout
```

**Solution**:
1. Check internet connection
2. Verify Polymarket API is accessible
3. If behind firewall/proxy, configure network settings

### No Market Data in IBKR

```
⚠ Market data request succeeded but no prices received
```

**Solution**: This is normal for paper trading outside market hours. The test still passes.

## Test Coverage

### What's Tested

✓ Configuration loading and validation
✓ Data models (TradeIntent)
✓ Trade ledger (record, update, query, export)
✓ Yield-adjusted fair value calculations
✓ Arbitrage spread detection
✓ Polymarket API integration (read-only)
✓ IBKR connection and contract lookup
✓ Market data requests
✓ Paper trading mode

### What's NOT Tested (By Design)

✗ Live order execution (too risky for automated tests)
✗ Real money transactions
✗ Polymarket write operations (system is read-only)
✗ ForecastEx order fills (requires real market conditions)

## Running Tests in CI/CD

For automated testing in CI/CD:

```bash
# Run only unit tests (no external dependencies)
python3 run_tests.py --unit-only

# Or with pytest directly
python3 -m pytest tests/ -k "not integration" -v
```

## Manual Integration Testing

For end-to-end testing with real connections but paper trading:

```bash
# 1. Start TWS/Gateway with paper trading account
# 2. Run a single iteration of the execution bot
python3 main_execution_bot.py --mode paper --max-iterations 1

# 3. Check the ledger
python3 -c "
from src.storage.ledger import TradeLedger
ledger = TradeLedger()
trades = ledger.get_trades(limit=10)
print(f'Found {len(trades)} trades')
for t in trades:
    print(f\"  {t['side']} {t['quantity']} {t['symbol_root']} @ {t['limit_price']} [{t['status']}]\")
"
```

## Test Data Cleanup

Tests create temporary files. To clean up:

```bash
# Remove test databases
rm -f data/test_*.db data/test_*.csv

# Remove pytest cache
rm -rf .pytest_cache __pycache__ tests/__pycache__
```

## Expected Test Results Summary

When everything is set up correctly:

```
OVERALL TEST SUMMARY
================================================================================
✓ PASSED     Unit Tests (4/4 test files)
✓ PASSED     Polymarket Integration (internet required)
✓ PASSED     IBKR Integration (TWS/Gateway required)
```

If you don't have TWS running:

```
OVERALL TEST SUMMARY
================================================================================
✓ PASSED     Unit Tests
✓ PASSED     Polymarket Integration
✗ FAILED     IBKR Integration (TWS not running - expected)
```

This is acceptable - unit tests are the most important for code validation.

## Next Steps

Once all tests pass:

1. **Verify Configuration**: Check your `.env` file
2. **Test Polymarket Connection**: `python3 tests/test_integration_polymarket.py`
3. **Test IBKR Connection**: Start TWS, then `python3 tests/test_integration_ibkr.py`
4. **Run Paper Trading Bot**: `python3 main_execution_bot.py --mode paper --max-iterations 1`
5. **Review Logs**: Check trade ledger in `data/trades.db`

## Questions?

If tests fail unexpectedly:
1. Check prerequisites are met
2. Verify .env configuration
3. Review error messages carefully
4. Check TESTING.md for troubleshooting tips
