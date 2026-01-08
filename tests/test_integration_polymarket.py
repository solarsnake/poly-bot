#!/usr/bin/env python3
"""
Integration test for Polymarket client (requires internet connection).
This test uses real Polymarket APIs but is read-only.
"""
import asyncio
import sys
from src.signal_server.polymarket_client import PolymarketClient


async def test_polymarket_get_markets():
    """Test fetching markets from Polymarket Gamma API."""
    print("\n" + "=" * 60)
    print("TEST: Fetch Markets from Polymarket Gamma API")
    print("=" * 60)

    client = PolymarketClient()

    try:
        print("Fetching open markets with tags: Crypto, Economics...")
        markets = client.get_markets(closed=False, tags=["Crypto", "Economics"])

        if markets:
            print(f"✓ Successfully fetched {len(markets)} markets")
            print(f"\nFirst 3 markets:")
            for i, market in enumerate(markets[:3], 1):
                print(f"\n{i}. {market.get('question', 'N/A')}")
                print(f"   ID: {market.get('id', 'N/A')}")
                print(f"   Active: {market.get('active', 'N/A')}")
                print(f"   End Date: {market.get('end_date_iso', 'N/A')}")
            return True
        else:
            print("✗ No markets fetched (empty response)")
            return False

    except Exception as e:
        print(f"✗ Error fetching markets: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_polymarket_order_book():
    """Test fetching order book from Polymarket CLOB."""
    print("\n" + "=" * 60)
    print("TEST: Fetch Order Book from Polymarket CLOB")
    print("=" * 60)

    client = PolymarketClient()

    try:
        # First get a market to test with
        markets = client.get_markets(closed=False, limit=1)

        if not markets:
            print("⊘ Skipping: No markets available to test order book")
            return None

        market_id = markets[0].get('id')
        market_question = markets[0].get('question', 'N/A')

        print(f"Testing order book for market: {market_question}")
        print(f"Market ID: {market_id}")

        order_book = await client.get_order_book(market_id, n_levels=3)

        print(f"\nOrder Book:")
        print(f"  Bids: {len(order_book.get('bids', []))} levels")
        print(f"  Asks: {len(order_book.get('asks', []))} levels")

        if order_book.get('bids'):
            print(f"\n  Top 3 Bids:")
            for price, size in order_book['bids'][:3]:
                print(f"    {price:.4f} x {size:.2f}")

        if order_book.get('asks'):
            print(f"\n  Top 3 Asks:")
            for price, size in order_book['asks'][:3]:
                print(f"    {price:.4f} x {size:.2f}")

        # Calculate liquidity-weighted probability
        probability = client.get_liquidity_weighted_probability(order_book)

        if probability is not None:
            print(f"\n  Liquidity-weighted probability: {probability:.4f} ({probability*100:.2f}%)")
            print("✓ Order book fetched and probability calculated successfully")
            return True
        else:
            print("✗ Could not calculate probability (no liquidity?)")
            return False

    except Exception as e:
        print(f"✗ Error fetching order book: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all Polymarket integration tests."""
    print("\n" + "#" * 60)
    print("# POLYMARKET INTEGRATION TESTS")
    print("# (Read-only API calls - no execution)")
    print("#" * 60)

    results = []

    # Test 1: Fetch markets
    result1 = await test_polymarket_get_markets()
    results.append(("Fetch Markets", result1))

    # Test 2: Fetch order book
    result2 = await test_polymarket_order_book()
    results.append(("Fetch Order Book", result2))

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

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
