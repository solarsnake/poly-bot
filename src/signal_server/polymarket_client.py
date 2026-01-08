import requests
from typing import Dict, Any, List, Optional
import asyncio
from py_clob_client.clob_client import ClobClient

class PolymarketClient:
    """Client for interacting with Polymarket Gamma API and CLOB public endpoints (read-only)."""

    GAMMA_API_BASE_URL = "https://gamma-api.polymarket.com"
    # Note: For CLOB, typically you'd connect to a specific chain/exchange. 
    # For read-only public data, `py-clob-client` might be used with a default public RPC if available, 
    # or a specific public endpoint. This example assumes a generic read-only setup.
    # In a real scenario, you'd configure the CLOB client more precisely.
    CLOB_RPC_URL = "https://rpc-mainnet.maticvigil.com/"
    CLOB_EXCHANGE_ADDRESS = "0x..."  # Placeholder, usually depends on Polymarket's deployed contracts

    def __init__(self):
        """Initializes the PolymarketClient in read-only mode."""
        # py-clob-client in read-only mode does not require a private key
        # For this example, we'll instantiate it without a signer.
        # A real read-only client might connect to a specific public node.
        try:
            self.clob_client = ClobClient(self.CLOB_RPC_URL, self.CLOB_EXCHANGE_ADDRESS, wallet_private_key=None)
        except Exception as e:
            print(f"Warning: Could not initialize ClobClient. It might not be fully functional for all read operations without proper configuration. Error: {e}")
            self.clob_client = None

    def get_markets(self, closed: bool = False, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetches markets from the Polymarket Gamma API.
        Args:
            closed: Whether to include closed markets.
            tags: List of tags to filter markets by (e.g., ["Crypto", "Economics"]).
        Returns:
            A list of market dictionaries.
        """
        params = {"closed": "true" if closed else "false"}
        if tags:
            params["tags"] = ",".join(tags)

        response = requests.get(f"{self.GAMMA_API_BASE_URL}/markets", params=params)
        response.raise_for_status()
        return response.json()

    async def get_order_book(self, market_id: str, n_levels: int = 3) -> Dict[str, Any]:
        """
        Fetches order book depth for a given market ID from CLOB public endpoints.
        Args:
            market_id: The unique identifier of the market.
            n_levels: Number of top levels to fetch.
        Returns:
            A dictionary containing 'bids' and 'asks', each a list of [price, size].
        """
        if not self.clob_client:
            print("ClobClient not initialized, cannot fetch order book.")
            return {"bids": [], "asks": []}
        
        # py-clob-client typically uses condition_id or market_id, 
        # assuming market_id maps to a known CLOB market identifier.
        # This part might need adjustment based on how Polymarket's CLOB market IDs map.
        # For demonstration, we'll use a placeholder for 'market_id' in a generic call.
        try:
            # This is a simplified call. Real usage might involve mapping Polymarket's market_id
            # to a specific CLOB 'market_hash' or 'token_id'.
            # For now, simulate with a dummy market hash if clob_client needs it, or assume
            # clob_client can resolve directly by a string ID if designed that way.
            # Let's assume a simplified method for demonstration.
            order_book_data = await self.clob_client.get_market_order_book(market_id) # Simplified

            bids = sorted([[float(o['price']), float(o['size'])] for o in order_book_data.get('bids', [])], key=lambda x: x[0], reverse=True)[:n_levels]
            asks = sorted([[float(o['price']), float(o['size'])] for o in order_book_data.get('asks', [])], key=lambda x: x[0])[:n_levels]
            return {"bids": bids, "asks": asks}
        except Exception as e:
            print(f"Error fetching order book for market {market_id}: {e}")
            return {"bids": [], "asks": []}

    def get_liquidity_weighted_probability(self, order_book: Dict[str, Any], n_levels: int = 3) -> Optional[float]:
        """
        Computes a liquidity-weighted probability metric (VWAP) from the order book.
        Args:
            order_book: Dictionary with 'bids' and 'asks'.
            n_levels: Number of top levels to consider for VWAP calculation.
        Returns:
            The liquidity-weighted probability (0-1) or None if no liquidity.
        """
        bids = order_book.get('bids', [])[:n_levels]
        asks = order_book.get('asks', [])[:n_levels]

        total_bid_value = sum(price * size for price, size in bids)
        total_bid_size = sum(size for _, size in bids)

        total_ask_value = sum(price * size for price, size in asks)
        total_ask_size = sum(size for _, size in asks)

        if total_bid_size == 0 and total_ask_size == 0:
            return None

        # Simple average of bid and ask VWAP, or just one if the other is empty
        vwap_bid = total_bid_value / total_bid_size if total_bid_size > 0 else 0
        vwap_ask = total_ask_value / total_ask_size if total_ask_size > 0 else 0

        if total_bid_size > 0 and total_ask_size > 0:
            # Average the VWAP of best N bids and asks to get a midpoint probability
            return (vwap_bid + vwap_ask) / 2
        elif total_bid_size > 0:
            return vwap_bid
        elif total_ask_size > 0:
            return vwap_ask
        else:
            return None

# Example usage (for testing purposes)
async def main():
    client = PolymarketClient()
    print("Fetching open markets...")
    markets = client.get_markets(closed=False, tags=["Crypto", "Economics"])
    if markets:
        print(f"Found {len(markets)} open markets.")
        for market in markets[:2]: # Just process first 2 for brevity
            print(f"\nMarket: {market['question']} (ID: {market['id']})")
            order_book = await client.get_order_book(market['id'])
            print(f"Order Book: {order_book}")
            prob = client.get_liquidity_weighted_probability(order_book)
            print(f"Liquidity-weighted probability: {prob:.4f}")
    else:
        print("No open markets found.")

if __name__ == "__main__":
    asyncio.run(main())
