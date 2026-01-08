import asyncio
from typing import Optional
from fastmcp import FastMCP, mcp
from src.signal_server.polymarket_client import PolymarketClient
from src.signal_server.config import settings

mcp_server = FastMCP(name="polymarket_signal_server")

@mcp.resource("polymarket://probability/{condition_id}")
async def get_polymarket_probability(condition_id: str) -> Optional[float]:
    """
    Fetches the liquidity-weighted probability for a given Polymarket condition ID.
    Args:
        condition_id: The unique identifier for the Polymarket condition (market).
    Returns:
        The liquidity-weighted probability (0-1) or None if not found/calculated.
    """
    client = PolymarketClient()
    # In a real scenario, you might need to map condition_id to a market ID that get_markets can use,
    # or directly query the order book if condition_id is directly usable by the CLOB client.
    # For this example, let's assume we can directly use condition_id as market_id for order book fetching.
    order_book = await client.get_order_book(condition_id) # Assuming condition_id works as market_id
    probability = client.get_liquidity_weighted_probability(order_book)
    print(f"Polymarket probability for {condition_id}: {probability}")
    return probability

@mcp.tool("get_arb_spread")
async def get_arb_spread(event_id: str, regulated_price: float, days_to_expiry: int) -> Optional[float]:
    """
    Calculates the yield-adjusted arbitrage spread between Polymarket probability and a regulated venue price.
    Args:
        event_id: The identifier for the event (maps to Polymarket condition_id).
        regulated_price: The observed price from the regulated venue (0-1).
        days_to_expiry: Number of days until the event expires.
    Returns:
        The yield-adjusted arbitrage spread or None if Polymarket probability cannot be fetched.
    """
    p_poly = await get_polymarket_probability(event_id)
    if p_poly is None:
        return None

    # Calculate yield-adjusted fair value for regulated venue
    r = settings.RISK_FREE_RATE
    t_days = days_to_expiry
    p_fx_fair = p_poly * (1 + r * t_days / 365)

    arb_spread = p_fx_fair - regulated_price
    print(f"Polymarket Prob: {p_poly:.4f}, Regulated Price: {regulated_price:.4f}, FX Fair: {p_fx_fair:.4f}, Arb Spread: {arb_spread:.4f}")
    return arb_spread

async def main():
    print("Starting Polymarket FastMCP signal server...")
    # To run this server, you would typically use `mcp_server.run()` in a main entry point.
    # For demonstration, we can simulate a call.
    # await mcp_server.run()
    print("MCP Server setup complete. Ready to receive requests.")

if __name__ == "__main__":
    asyncio.run(main())
