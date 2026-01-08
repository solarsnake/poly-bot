from ib_insync import Contract
from typing import Dict, Any, Optional
from src.execution.ibkr_client import IBKRClient

class ForecastExContractFactory:
    """
    Factory to find and map ForecastEx contracts (modeled as options) to ib_insync.Contract objects.
    ForecastEx contracts are assumed to be options (secType='OPT') on synthetic underlyings.
    """

    def __init__(self, ibkr_client: IBKRClient):
        """
        Initializes the factory with an IBKR client instance.
        Args:
            ibkr_client: An instance of IBKRClient.
        """
        self.ibkr_client = ibkr_client
        self._contract_cache: Dict[str, Contract] = {}

    def _find_contract(self, symbol_root: str, strike: float, expiry: str, right: str) -> Optional[Contract]:
        """
        Internal method to search for a specific ForecastEx contract using IBKR.
        Args:
            symbol_root: The underlying symbol root (e.g., 'USCPI').
            strike: The strike price of the option.
            expiry: The expiry date in YYYYMMDD format.
            right: 'C' for Call (Yes) or 'P' for Put (No).
        Returns:
            An ib_insync.Contract object if found, otherwise None.
        """
        contract = Contract(
            symbol=symbol_root,  # e.g., 'USCPI'
            secType='OPT',
            exchange='FORECASTX',
            currency='USD',
            right=right,          # 'C' for Yes, 'P' for No
            strike=strike,
            lastTradeDateOrContractMonth=expiry # YYYYMMDD
        )

        print(f"Searching for ForecastEx contract: {symbol_root} {strike} {expiry} {right}")
        details = self.ibkr_client.get_contract_details(contract)

        if details:
            # Assuming the first matching contract is sufficient for now.
            # In a real scenario, you might need more sophisticated matching logic.
            print(f"Found contract: {details[0].conId} - {details[0].localSymbol}")
            return details[0]
        else:
            print(f"No ForecastEx contract found for {symbol_root} {strike} {expiry} {right}")
            return None

    def get_forecastex_contract(self, description: str, strike: float, expiry_date: str, is_yes: bool) -> Optional[Contract]:
        """
        Maps a human description to a specific ForecastEx Contract object.
        Args:
            description: A human-readable description (e.g., "US CPI YoY", "BTC Quarterly").
            strike: The strike price for the binary option (e.g., 0 or 100).
            expiry_date: The expiry date in 'YYYY-MM-DD' format. Will be converted to 'YYYYMMDD'.
            is_yes: True for a 'Yes' contract (Call), False for a 'No' contract (Put).
        Returns:
            An ib_insync.Contract object if a matching ForecastEx contract is found, else None.
        """
        # Simple mapping from description to symbol_root. This would be more robust in production.
        symbol_root_map = {
            "US CPI YoY": "USCPI",
            "BTC Quarterly": "BTCQ",
            # Add more mappings as needed
        }
        symbol_root = symbol_root_map.get(description)
        if not symbol_root:
            print(f"Error: Unknown description '{description}' for ForecastEx contract mapping.")
            return None
        
        # Convert expiry_date from YYYY-MM-DD to YYYYMMDD
        expiry_ibkr_format = expiry_date.replace('-', '')
        right = 'C' if is_yes else 'P'

        cache_key = f"{symbol_root}-{strike}-{expiry_ibkr_format}-{right}"
        if cache_key in self._contract_cache:
            print(f"Returning cached contract for {cache_key}")
            return self._contract_cache[cache_key]

        contract = self._find_contract(symbol_root, strike, expiry_ibkr_format, right)
        if contract:
            self._contract_cache[cache_key] = contract
        return contract

# Example Usage (for testing)
async def main():
    from src.signal_server.config import settings

    ibkr_client = IBKRClient()

    try:
        await ibkr_client.connect(settings.IB_HOST, settings.IB_PORT, settings.IB_CLIENT_ID)

        factory = ForecastExContractFactory(ibkr_client)

        # Example: Find a 'Yes' contract for "US CPI YoY" expiring on 2026-03-15 with strike 100
        contract_yes = factory.get_forecastex_contract(
            description="US CPI YoY",
            strike=100.0,
            expiry_date="2026-03-15",
            is_yes=True
        )
        if contract_yes:
            print(f"Successfully found 'Yes' contract: {contract_yes.localSymbol}")

        # Example: Find a 'No' contract for "US CPI YoY" expiring on 2026-03-15 with strike 100
        contract_no = factory.get_forecastex_contract(
            description="US CPI YoY",
            strike=100.0,
            expiry_date="2026-03-15",
            is_yes=False
        )
        if contract_no:
            print(f"Successfully found 'No' contract: {contract_no.localSymbol}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        ibkr_client.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
