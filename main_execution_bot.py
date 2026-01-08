#!/usr/bin/env python3
"""
Main entry point for the Execution Bot.
This bot pulls signals from Polymarket, prices from IBKR/ForecastEx,
and executes trades based on yield-adjusted arbitrage opportunities.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.execution.ibkr_client import IBKRClient
from src.execution.forecastex_contracts import ForecastExContractFactory
from src.execution.forecastex_execution import ExecutionEngine
from src.signal_server.polymarket_client import PolymarketClient
from src.storage.ledger import TradeLedger
from src.signal_server.config import settings


class ExecutionBot:
    """
    Main execution bot that orchestrates signal → execution flow.
    """

    def __init__(
        self,
        mode: str = "paper",
        arb_threshold: float = 0.02,
        polling_interval: int = 60,
        max_iterations: int = None
    ):
        """
        Initializes the ExecutionBot.
        Args:
            mode: Trading mode ('paper' or 'live').
            arb_threshold: Minimum arb spread to trigger a trade (e.g., 0.02 = 2%).
            polling_interval: Seconds between polling cycles.
            max_iterations: Maximum number of iterations (None = infinite).
        """
        self.mode = mode
        self.arb_threshold = arb_threshold
        self.polling_interval = polling_interval
        self.max_iterations = max_iterations

        # Components
        self.poly_client: Optional[PolymarketClient] = None
        self.ibkr_client: Optional[IBKRClient] = None
        self.contract_factory: Optional[ForecastExContractFactory] = None
        self.execution_engine: Optional[ExecutionEngine] = None
        self.ledger: Optional[TradeLedger] = None

        # Market watchlist: (description, strike, expiry, is_yes, polymarket_condition_id)
        # In production, this would be dynamically populated from Polymarket Gamma API
        self.watchlist: List[Dict[str, Any]] = [
            {
                "description": "US CPI YoY",
                "strike": 100.0,
                "expiry_date": "2026-03-15",
                "is_yes": True,
                "condition_id": "example_cpi_condition_id",  # Placeholder
                "tags": ["Economics"]
            },
            # Add more markets here as needed
        ]

    async def initialize(self):
        """Initializes all components."""
        print("=" * 60)
        print("Execution Bot Initialization")
        print("=" * 60)
        print(f"Mode: {self.mode.upper()}")
        print(f"Arb Threshold: {self.arb_threshold * 100:.1f}%")
        print(f"Polling Interval: {self.polling_interval}s")
        print(f"Max Iterations: {self.max_iterations if self.max_iterations else 'Infinite'}")
        print("=" * 60)
        print()

        # Initialize Polymarket client
        print("Initializing Polymarket client...")
        self.poly_client = PolymarketClient()

        # Initialize IBKR client
        print("Initializing IBKR client...")
        self.ibkr_client = IBKRClient()
        await self.ibkr_client.connect()

        if not self.ibkr_client._connected:
            raise RuntimeError("Failed to connect to IBKR. Please check TWS/Gateway is running.")

        # Initialize contract factory
        print("Initializing ForecastEx contract factory...")
        self.contract_factory = ForecastExContractFactory(self.ibkr_client)

        # Initialize ledger
        print("Initializing trade ledger...")
        self.ledger = TradeLedger()

        # Initialize execution engine
        print("Initializing execution engine...")
        self.execution_engine = ExecutionEngine(
            ibkr_client=self.ibkr_client,
            contract_factory=self.contract_factory,
            ledger=self.ledger,
            mode=self.mode,
            arb_threshold=self.arb_threshold
        )

        print("\nInitialization complete!")
        print()

    async def fetch_polymarket_probability(self, condition_id: str) -> Optional[float]:
        """
        Fetches the liquidity-weighted probability from Polymarket.
        Args:
            condition_id: The Polymarket condition ID.
        Returns:
            Probability (0-1) or None if not available.
        """
        try:
            order_book = await self.poly_client.get_order_book(condition_id)
            probability = self.poly_client.get_liquidity_weighted_probability(order_book)
            return probability
        except Exception as e:
            print(f"Error fetching Polymarket probability for {condition_id}: {e}")
            return None

    def calculate_days_to_expiry(self, expiry_date: str) -> int:
        """
        Calculates days to expiry from current date.
        Args:
            expiry_date: Expiry date in YYYY-MM-DD format.
        Returns:
            Number of days to expiry (minimum 0).
        """
        expiry_dt = datetime.strptime(expiry_date, "%Y-%m-%d")
        today = datetime.now()
        delta = (expiry_dt - today).days
        return max(delta, 0)

    async def process_market(self, market: Dict[str, Any]):
        """
        Processes a single market from the watchlist.
        Args:
            market: Dictionary containing market details.
        """
        print(f"\n{'='*60}")
        print(f"Processing: {market['description']}")
        print(f"{'='*60}")

        # Fetch Polymarket probability
        p_poly = await self.fetch_polymarket_probability(market['condition_id'])

        if p_poly is None:
            print(f"Skipping {market['description']} - could not fetch Polymarket probability.")
            return

        print(f"Polymarket probability: {p_poly:.4f}")

        # Calculate days to expiry
        days_to_expiry = self.calculate_days_to_expiry(market['expiry_date'])
        print(f"Days to expiry: {days_to_expiry}")

        # Evaluate arb opportunity
        trade_intent = await self.execution_engine.evaluate_arb_opportunity(
            description=market['description'],
            strike=market['strike'],
            expiry_date=market['expiry_date'],
            is_yes=market['is_yes'],
            p_poly=p_poly,
            days_to_expiry=days_to_expiry,
            quantity=10.0  # Configurable
        )

        # Execute if opportunity exists
        if trade_intent:
            print(f"\nExecuting trade for {market['description']}...")
            success = await self.execution_engine.execute_trade_intent(trade_intent)
            if success:
                print(f"✓ Trade executed successfully")
            else:
                print(f"✗ Trade execution failed")
        else:
            print(f"No arb opportunity for {market['description']}")

    async def run(self):
        """Main execution loop."""
        print("\n" + "=" * 60)
        print("Starting Execution Bot Main Loop")
        print("=" * 60)
        print("Press Ctrl+C to stop the bot.")
        print()

        iteration = 0

        try:
            while True:
                iteration += 1
                print(f"\n{'#'*60}")
                print(f"Iteration {iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'#'*60}")

                # Process each market in the watchlist
                for market in self.watchlist:
                    try:
                        await self.process_market(market)
                    except Exception as e:
                        print(f"Error processing market {market['description']}: {e}")
                        import traceback
                        traceback.print_exc()

                # Check if we've reached max iterations
                if self.max_iterations and iteration >= self.max_iterations:
                    print(f"\nReached max iterations ({self.max_iterations}). Exiting.")
                    break

                # Sleep until next polling cycle
                print(f"\nSleeping for {self.polling_interval}s until next cycle...")
                await asyncio.sleep(self.polling_interval)

        except KeyboardInterrupt:
            print("\n\nReceived Ctrl+C. Shutting down...")
        except Exception as e:
            print(f"\n\nUnexpected error in main loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup and disconnect."""
        print("\nCleaning up...")

        if self.ibkr_client:
            self.ibkr_client.disconnect()

        # Export trades to CSV
        if self.ledger:
            print("Exporting trades to CSV...")
            self.ledger.export_to_csv()

            # Print PnL summary
            pnl = self.ledger.calculate_pnl()
            print(f"\nPnL Summary:")
            print(f"  Total trades: {pnl['total_trades']}")
            print(f"  Total notional: ${pnl['total_notional']:.2f}")
            if pnl['positions']:
                print(f"  Open positions: {len(pnl['positions'])}")
                for symbol, pos in pnl['positions'].items():
                    print(f"    {symbol}: {pos['quantity']} @ avg ${pos['avg_price']:.4f}")

        print("Cleanup complete. Goodbye!")


async def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Polymarket → ForecastEx Execution Bot")
    parser.add_argument(
        "--mode",
        type=str,
        default="paper",
        choices=["paper", "live"],
        help="Trading mode (default: paper)"
    )
    parser.add_argument(
        "--arb-threshold",
        type=float,
        default=0.02,
        help="Minimum arb spread to trigger trades (default: 0.02 = 2%%)"
    )
    parser.add_argument(
        "--polling-interval",
        type=int,
        default=60,
        help="Seconds between polling cycles (default: 60)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of iterations (default: infinite)"
    )

    args = parser.parse_args()

    # Safety check for live mode
    if args.mode == "live":
        print("\n" + "!" * 60)
        print("WARNING: You are about to run in LIVE trading mode!")
        print("Real orders will be placed on your IBKR account.")
        print("!" * 60)
        response = input("\nType 'YES' to confirm: ")
        if response.strip().upper() != "YES":
            print("Live mode not confirmed. Exiting.")
            return

    # Create and run the bot
    bot = ExecutionBot(
        mode=args.mode,
        arb_threshold=args.arb_threshold,
        polling_interval=args.polling_interval,
        max_iterations=args.max_iterations
    )

    await bot.initialize()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
