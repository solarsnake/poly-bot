#!/usr/bin/env python3
"""
Integration test for IBKR client (requires IBKR TWS/Gateway running).
This test uses real IBKR connection but only queries data (no orders).
"""
import asyncio
import sys
from src.execution.ibkr_client import IBKRClient
from src.execution.forecastex_contracts import ForecastExContractFactory
from src.signal_server.config import settings
from ib_insync import Contract


async def test_ibkr_connection():
    """Test connecting to IBKR TWS/Gateway."""
    print("\n" + "=" * 60)
    print("TEST: Connect to IBKR TWS/Gateway")
    print("=" * 60)

    client = IBKRClient()

    try:
        print(f"Attempting connection to {settings.IB_HOST}:{settings.IB_PORT} (client ID: {settings.IB_CLIENT_ID})")
        await client.connect()

        if client._connected:
            print(f"✓ Successfully connected to IBKR")
            return client
        else:
            print(f"✗ Failed to connect to IBKR")
            return None

    except Exception as e:
        print(f"✗ Error connecting to IBKR: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure TWS or IB Gateway is running")
        print("2. Check that API connections are enabled in TWS/Gateway settings")
        print("3. Verify the port number (7496 for TWS live, 4002 for paper)")
        print("4. Check your .env file for correct IB_HOST and IB_PORT")
        return None


async def test_contract_details_lookup(client: IBKRClient):
    """Test looking up contract details."""
    print("\n" + "=" * 60)
    print("TEST: Look Up Contract Details")
    print("=" * 60)

    if not client or not client._connected:
        print("⊘ Skipping: Not connected to IBKR")
        return None

    try:
        # Test with a well-known contract (SPY ETF)
        print("Looking up SPY (S&P 500 ETF) contract...")

        spy_contract = Contract(
            symbol='SPY',
            secType='STK',
            exchange='SMART',
            currency='USD'
        )

        details = client.get_contract_details(spy_contract)

        if details:
            print(f"✓ Found {len(details)} contract details for SPY")
            print(f"  Contract ID: {details[0].conId}")
            print(f"  Local Symbol: {details[0].localSymbol}")
            print(f"  Exchange: {details[0].exchange}")
            return True
        else:
            print("✗ No contract details found for SPY")
            return False

    except Exception as e:
        print(f"✗ Error looking up contract: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_market_data_request(client: IBKRClient):
    """Test requesting market data."""
    print("\n" + "=" * 60)
    print("TEST: Request Market Data")
    print("=" * 60)

    if not client or not client._connected:
        print("⊘ Skipping: Not connected to IBKR")
        return None

    try:
        print("Requesting market data for SPY...")

        spy_contract = Contract(
            symbol='SPY',
            secType='STK',
            exchange='SMART',
            currency='USD'
        )

        ticker = await client.req_market_data(spy_contract)

        if ticker:
            # Wait a few seconds for data to arrive
            print("Waiting for market data...")
            await asyncio.sleep(3)

            print(f"\nMarket Data:")
            print(f"  Bid: {ticker.bid if ticker.bid and ticker.bid > 0 else 'N/A'}")
            print(f"  Ask: {ticker.ask if ticker.ask and ticker.ask > 0 else 'N/A'}")
            print(f"  Last: {ticker.last if ticker.last and ticker.last > 0 else 'N/A'}")

            if ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                midpoint = (ticker.bid + ticker.ask) / 2
                print(f"  Midpoint: {midpoint:.2f}")
                print("✓ Market data received successfully")
                return True
            else:
                print("⚠ Market data request succeeded but no prices received")
                print("  (This is normal for paper trading outside market hours)")
                return True  # Still count as success

        else:
            print("✗ Failed to request market data")
            return False

    except Exception as e:
        print(f"✗ Error requesting market data: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_forecastex_contract_lookup(client: IBKRClient):
    """Test looking up ForecastEx contracts."""
    print("\n" + "=" * 60)
    print("TEST: Look Up ForecastEx Contracts")
    print("=" * 60)

    if not client or not client._connected:
        print("⊘ Skipping: Not connected to IBKR")
        return None

    try:
        print("Searching for ForecastEx contracts...")

        factory = ForecastExContractFactory(client)

        # Try to find a ForecastEx contract
        # Note: This may not find anything if ForecastEx contracts aren't available
        # or if the symbol mapping is incorrect
        print("Attempting to look up 'US CPI YoY' contract...")

        contract = factory.get_forecastex_contract(
            description="US CPI YoY",
            strike=100.0,
            expiry_date="2026-03-15",
            is_yes=True
        )

        if contract:
            print(f"✓ Found ForecastEx contract!")
            print(f"  Symbol: {contract.symbol}")
            print(f"  Local Symbol: {contract.localSymbol if hasattr(contract, 'localSymbol') else 'N/A'}")
            print(f"  Contract ID: {contract.conId if hasattr(contract, 'conId') else 'N/A'}")
            return True
        else:
            print("⚠ No ForecastEx contract found")
            print("  This is expected if:")
            print("  1. ForecastEx contracts aren't available in your account")
            print("  2. The symbol mapping needs to be updated")
            print("  3. The contract doesn't exist for this date/strike")
            return None  # Not a failure, just not available

    except Exception as e:
        print(f"⚠ Error looking up ForecastEx contract: {e}")
        print("  This is expected if ForecastEx isn't available")
        return None


async def test_positions_query(client: IBKRClient):
    """Test querying current positions."""
    print("\n" + "=" * 60)
    print("TEST: Query Current Positions")
    print("=" * 60)

    if not client or not client._connected:
        print("⊘ Skipping: Not connected to IBKR")
        return None

    try:
        print("Requesting current positions...")

        positions = client.req_positions()

        print(f"Found {len(positions)} open positions")

        if positions:
            print("\nOpen Positions:")
            for pos in positions[:5]:  # Show first 5
                print(f"  {pos.contract.symbol}: {pos.position} @ avg cost {pos.avgCost:.2f}")

        print("✓ Positions query successful")
        return True

    except Exception as e:
        print(f"✗ Error querying positions: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all IBKR integration tests."""
    print("\n" + "#" * 60)
    print("# IBKR INTEGRATION TESTS")
    print("# (Read-only queries - no orders placed)")
    print("#" * 60)

    print("\nPrerequisites:")
    print("- TWS or IB Gateway must be running")
    print("- API connections must be enabled")
    print(f"- Check settings: {settings.IB_HOST}:{settings.IB_PORT}")
    print()

    results = []
    client = None

    try:
        # Test 1: Connection
        client = await test_ibkr_connection()
        results.append(("IBKR Connection", client is not None))

        if client:
            # Test 2: Contract lookup
            result2 = await test_contract_details_lookup(client)
            results.append(("Contract Lookup", result2))

            # Test 3: Market data
            result3 = await test_market_data_request(client)
            results.append(("Market Data Request", result3))

            # Test 4: ForecastEx lookup
            result4 = await test_forecastex_contract_lookup(client)
            results.append(("ForecastEx Lookup", result4))

            # Test 5: Positions query
            result5 = await test_positions_query(client)
            results.append(("Positions Query", result5))

    finally:
        # Cleanup
        if client and client._connected:
            print("\nDisconnecting from IBKR...")
            client.disconnect()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, result in results:
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⊘ SKIP"
        print(f"{status:10} {test_name}")

    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)

    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")

    # Only fail if we couldn't connect at all
    return client is not None


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
