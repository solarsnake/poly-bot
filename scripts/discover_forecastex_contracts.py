#!/usr/bin/env python3
"""
ForecastEx Contract Discovery Script

This script connects to IBKR and discovers all available ForecastEx contracts.
Run this once IBKR account is set up to find the "boring plumbing" symbols.

Usage:
    python scripts/discover_forecastex_contracts.py
"""
import sys
import asyncio
import csv
from datetime import datetime
sys.path.insert(0, '/Users/tippens/solarcode/repos/poly-bot')

from src.execution.ibkr_client import IBKRClient
from src.signal_server.config import settings
from ib_insync import Contract


async def discover_contracts():
    """Discover all available ForecastEx contracts."""
    print("=" * 70)
    print("FORECASTEX CONTRACT DISCOVERY")
    print("=" * 70)
    print()

    # Connect to IBKR
    client = IBKRClient()
    print(f"Connecting to IBKR at {settings.IB_HOST}:{settings.IB_PORT}...")
    await client.connect()

    if not client._connected:
        print("✗ Failed to connect to IBKR")
        print("  Make sure IB Gateway is running and API is enabled")
        return

    print("✓ Connected to IBKR")
    print()

    # Search strategies to try
    search_strategies = [
        {
            "name": "EVENT contracts",
            "contract": Contract(secType='EVENT', exchange='FORECASTX', currency='USD')
        },
        {
            "name": "OPT contracts on FORECASTX",
            "contract": Contract(secType='OPT', exchange='FORECASTX', currency='USD')
        },
        {
            "name": "FUT contracts on FORECASTX",
            "contract": Contract(secType='FUT', exchange='FORECASTX', currency='USD')
        },
        {
            "name": "Broad FORECASTX search",
            "contract": Contract(exchange='FORECASTX', currency='USD')
        },
    ]

    all_contracts = []

    for strategy in search_strategies:
        print(f"Searching: {strategy['name']}...")
        try:
            details = client.get_contract_details(strategy['contract'])

            if details:
                print(f"  ✓ Found {len(details)} contracts")
                all_contracts.extend(details)
            else:
                print(f"  ⊘ No contracts found")

        except Exception as e:
            print(f"  ✗ Error: {e}")

        print()

    # Deduplicate by contract ID
    unique_contracts = {}
    for detail in all_contracts:
        contract = detail.contract
        if hasattr(contract, 'conId') and contract.conId:
            unique_contracts[contract.conId] = detail

    print("=" * 70)
    print(f"DISCOVERY SUMMARY: Found {len(unique_contracts)} unique contracts")
    print("=" * 70)
    print()

    if not unique_contracts:
        print("⚠ No ForecastEx contracts found!")
        print()
        print("Possible reasons:")
        print("1. ForecastEx permission not yet approved")
        print("   → Check IBKR Client Portal → Settings → Trading Permissions")
        print("2. No contracts currently available")
        print("   → ForecastEx may have limited offerings")
        print("3. Market is closed")
        print("   → Try during US trading hours")
        print()
        print("Next steps:")
        print("- Contact IBKR support: 1-877-442-2757")
        print("- Ask about 'ForecastEx event contract access'")
        print("- Verify account has futures/options permissions")
        client.disconnect()
        return

    # Display and save results
    contracts_data = []

    print("AVAILABLE CONTRACTS:")
    print("-" * 70)

    for i, (con_id, detail) in enumerate(unique_contracts.items(), 1):
        contract = detail.contract

        # Extract useful info
        symbol = contract.symbol if hasattr(contract, 'symbol') else 'N/A'
        local_symbol = contract.localSymbol if hasattr(contract, 'localSymbol') else 'N/A'
        sec_type = contract.secType if hasattr(contract, 'secType') else 'N/A'
        expiry = contract.lastTradeDateOrContractMonth if hasattr(contract, 'lastTradeDateOrContractMonth') else 'N/A'
        strike = contract.strike if hasattr(contract, 'strike') else 'N/A'
        right = contract.right if hasattr(contract, 'right') else 'N/A'
        long_name = detail.longName if hasattr(detail, 'longName') else 'N/A'

        print(f"{i}. {long_name}")
        print(f"   Symbol: {symbol} | Local: {local_symbol}")
        print(f"   Type: {sec_type} | Expiry: {expiry}")
        if strike != 'N/A':
            print(f"   Strike: {strike} | Right: {right}")
        print(f"   Contract ID: {con_id}")
        print()

        contracts_data.append({
            'contract_id': con_id,
            'symbol': symbol,
            'local_symbol': local_symbol,
            'sec_type': sec_type,
            'description': long_name,
            'expiry': expiry,
            'strike': strike,
            'right': right,
            'exchange': 'FORECASTX',
            'currency': 'USD',
            'discovered_at': datetime.now().isoformat()
        })

    # Save to CSV
    output_file = 'data/contracts_available.csv'
    import os
    os.makedirs('data', exist_ok=True)

    with open(output_file, 'w', newline='') as f:
        if contracts_data:
            writer = csv.DictWriter(f, fieldnames=contracts_data[0].keys())
            writer.writeheader()
            writer.writerows(contracts_data)

    print("=" * 70)
    print(f"✓ Results saved to: {output_file}")
    print("=" * 70)
    print()

    print("NEXT STEPS:")
    print("1. Review the contracts above")
    print("2. Find matching events on Polymarket:")
    print("   → https://polymarket.com")
    print("3. Update the symbol mapping in:")
    print("   → src/execution/forecastex_contracts.py")
    print("4. Add to watchlist in:")
    print("   → main_execution_bot.py")
    print()

    # Disconnect
    client.disconnect()
    print("Disconnected from IBKR")


async def main():
    """Main entry point."""
    try:
        await discover_contracts()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
