#!/usr/bin/env python3
"""
Unified Trading Bot Orchestrator

Runs three layers in parallel:
1. Polymarket Signal Engine (real-time streaming)
2. Sentiment & Confidence Layer (news + scoring)
3. ForecastEx Execution Engine (trade execution)

Usage:
    python main_bot.py --mode analysis-only  # No execution
    python main_bot.py --mode paper          # Paper trading
    python main_bot.py --mode live           # Real money (requires confirmation)
"""
import asyncio
import argparse
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, '/Users/tippens/solarcode/repos/poly-bot')

from src.signal_server.polymarket_client import PolymarketClient
from src.signal_server.polymarket_stream import PolymarketStream
from src.sentiment_layer.news_client import NewsClient
from src.sentiment_layer.sentiment_scorer import SentimentScorer
from src.execution.ibkr_client import IBKRClient
from src.execution.forecastex_contracts import ForecastExContractFactory
from src.execution.forecastex_execution import ExecutionEngine
from src.storage.ledger import TradeLedger
from src.signal_server.config import settings


class UnifiedTradingBot:
    """
    Orchestrates all three layers of the trading system.
    """

    def __init__(
        self,
        mode: str = "analysis-only",
        polling_interval: int = 60,
        sentiment_enabled: bool = True
    ):
        """
        Initialize the unified bot.

        Args:
            mode: Trading mode (analysis-only, paper, live)
            polling_interval: Seconds between checks (for non-streaming markets)
            sentiment_enabled: Whether to use sentiment analysis
        """
        self.mode = mode
        self.polling_interval = polling_interval
        self.sentiment_enabled = sentiment_enabled

        # Components
        self.poly_client: Optional[PolymarketClient] = None
        self.poly_stream: Optional[PolymarketStream] = None
        self.news_client: Optional[NewsClient] = None
        self.sentiment_scorer: Optional[SentimentScorer] = None
        self.ibkr_client: Optional[IBKRClient] = None
        self.contract_factory: Optional[ForecastExContractFactory] = None
        self.execution_engine: Optional[ExecutionEngine] = None
        self.ledger: Optional[TradeLedger] = None

        # State
        self.running = False
        self.market_signals: Dict[str, Any] = {}

        # Watchlist (markets to monitor)
        self.watchlist: List[Dict[str, Any]] = [
            {
                "description": "US CPI YoY",
                "polymarket_id": "example_condition_id",  # Replace with real ID
                "keywords": ["CPI", "inflation", "consumer price"],
                "strike": 100.0,
                "expiry_date": "2026-03-15",
                "is_yes": True,
                "tags": ["Economics"]
            },
            # Add more markets here
        ]

        print(f"✓ UnifiedTradingBot initialized in {mode.upper()} mode")

    async def initialize(self):
        """Initialize all components."""
        print("\n" + "=" * 70)
        print("INITIALIZING UNIFIED TRADING BOT")
        print("=" * 70)
        print()

        # Layer 1: Polymarket Signal Engine
        print("[Layer 1] Initializing Polymarket signal engine...")
        self.poly_client = PolymarketClient()
        self.poly_stream = PolymarketStream()
        print("✓ Polymarket client ready")

        # Layer 2: Sentiment & Confidence
        if self.sentiment_enabled:
            print("\n[Layer 2] Initializing sentiment layer...")
            self.news_client = NewsClient()
            self.sentiment_scorer = SentimentScorer(method="textblob")  # Can switch to "finbert"
            print("✓ Sentiment analysis ready")
        else:
            print("\n[Layer 2] Sentiment analysis DISABLED")

        # Layer 3: Execution Engine (if not analysis-only)
        if self.mode != "analysis-only":
            print("\n[Layer 3] Initializing execution engine...")

            self.ledger = TradeLedger()

            self.ibkr_client = IBKRClient()
            try:
                await self.ibkr_client.connect()
                print("✓ IBKR connected")

                self.contract_factory = ForecastExContractFactory(self.ibkr_client)

                execution_mode = "paper" if self.mode == "paper" else "live"
                self.execution_engine = ExecutionEngine(
                    ibkr_client=self.ibkr_client,
                    contract_factory=self.contract_factory,
                    ledger=self.ledger,
                    mode=execution_mode,
                    arb_threshold=0.02
                )
                print(f"✓ Execution engine ready ({execution_mode} mode)")

            except Exception as e:
                print(f"⚠ IBKR connection failed: {e}")
                print("  Falling back to analysis-only mode")
                self.mode = "analysis-only"
        else:
            print("\n[Layer 3] Execution engine DISABLED (analysis-only mode)")

        print("\n" + "=" * 70)
        print("INITIALIZATION COMPLETE")
        print("=" * 70)
        print()

    async def run(self):
        """Main run loop - orchestrates all three layers."""
        self.running = True

        print("Starting unified trading bot...")
        print(f"Mode: {self.mode}")
        print(f"Sentiment: {'Enabled' if self.sentiment_enabled else 'Disabled'}")
        print(f"Watchlist: {len(self.watchlist)} markets")
        print()

        # Create tasks for each layer
        tasks = []

        # Layer 1: Polymarket streaming (if markets support WebSocket)
        # For now, we'll use polling since we need to discover market IDs first
        tasks.append(asyncio.create_task(self._run_signal_layer()))

        # Layer 2: Sentiment analysis (periodic)
        if self.sentiment_enabled:
            tasks.append(asyncio.create_task(self._run_sentiment_layer()))

        # Layer 3: Execution logic (periodic)
        if self.mode != "analysis-only":
            tasks.append(asyncio.create_task(self._run_execution_layer()))

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n\nStopping bot...")
            self.running = False
        except Exception as e:
            print(f"\n\nError in main loop: {e}")
            self.running = False
        finally:
            await self.cleanup()

    async def _run_signal_layer(self):
        """Layer 1: Continuously update Polymarket signals."""
        print("[Layer 1] Starting signal monitoring...")

        while self.running:
            try:
                for market in self.watchlist:
                    market_id = market['polymarket_id']

                    # Fetch order book
                    order_book = await self.poly_client.get_order_book(market_id, n_levels=3)

                    # Calculate probability
                    probability = self.poly_client.get_liquidity_weighted_probability(order_book)

                    if probability is not None:
                        # Store signal
                        self.market_signals[market_id] = {
                            'probability': probability,
                            'order_book': order_book,
                            'updated_at': datetime.now(),
                            'market': market
                        }

                        print(f"[Signal] {market['description']}: {probability:.1%}")

            except Exception as e:
                print(f"[Signal] Error: {e}")

            await asyncio.sleep(self.polling_interval)

    async def _run_sentiment_layer(self):
        """Layer 2: Periodically update sentiment scores."""
        print("[Layer 2] Starting sentiment analysis...")

        # Run less frequently than signals (e.g., every 10 minutes)
        sentiment_interval = max(self.polling_interval * 10, 600)

        while self.running:
            try:
                for market in self.watchlist:
                    market_id = market['polymarket_id']

                    # Fetch news
                    keywords = market.get('keywords', [])
                    if not keywords:
                        keywords = self.news_client.match_event_to_keywords(market['description'])

                    articles = self.news_client.fetch_news_for_event(
                        keywords=keywords,
                        from_date=datetime.now() - timedelta(days=3),
                        max_results=5
                    )

                    if articles:
                        # Score sentiment
                        sentiment_result = self.sentiment_scorer.score_articles(articles)

                        # Store sentiment
                        if market_id in self.market_signals:
                            self.market_signals[market_id]['sentiment'] = sentiment_result
                            self.market_signals[market_id]['sentiment_updated_at'] = datetime.now()

                            print(f"[Sentiment] {market['description']}: "
                                  f"{sentiment_result['average_sentiment']:+.2f} "
                                  f"(confidence: {sentiment_result['confidence']:.1%})")

            except Exception as e:
                print(f"[Sentiment] Error: {e}")

            await asyncio.sleep(sentiment_interval)

    async def _run_execution_layer(self):
        """Layer 3: Evaluate opportunities and execute trades."""
        print("[Layer 3] Starting execution monitoring...")

        while self.running:
            try:
                for market in self.watchlist:
                    market_id = market['polymarket_id']

                    # Get current signals
                    if market_id not in self.market_signals:
                        continue

                    signal = self.market_signals[market_id]

                    # Base probability from Polymarket
                    p_poly = signal.get('probability')
                    if p_poly is None:
                        continue

                    # Apply sentiment boost if available
                    p_confidence = p_poly
                    if 'sentiment' in signal and self.sentiment_enabled:
                        sentiment = signal['sentiment']
                        p_confidence = self.sentiment_scorer.calculate_confidence_boost(
                            base_probability=p_poly,
                            sentiment_score=sentiment['average_sentiment'],
                            sentiment_confidence=sentiment['confidence'],
                            max_boost=0.20
                        )

                        boost_pct = (p_confidence - p_poly) / p_poly * 100 if p_poly > 0 else 0
                        print(f"[Execution] {market['description']}: "
                              f"Base {p_poly:.1%} → Boosted {p_confidence:.1%} ({boost_pct:+.1f}%)")

                    # Calculate days to expiry
                    expiry_date = datetime.strptime(market['expiry_date'], "%Y-%m-%d")
                    days_to_expiry = (expiry_date - datetime.now()).days

                    # Evaluate opportunity (using confidence-boosted probability)
                    trade_intent = await self.execution_engine.evaluate_arb_opportunity(
                        description=market['description'],
                        strike=market['strike'],
                        expiry_date=market['expiry_date'],
                        is_yes=market['is_yes'],
                        p_poly=p_confidence,  # Use confidence-boosted probability
                        days_to_expiry=days_to_expiry,
                        quantity=10.0
                    )

                    if trade_intent:
                        # Execute trade
                        success = await self.execution_engine.execute_trade_intent(trade_intent)
                        if success:
                            print(f"[Execution] ✓ Trade executed: {market['description']}")
                        else:
                            print(f"[Execution] ✗ Trade failed: {market['description']}")

            except Exception as e:
                print(f"[Execution] Error: {e}")
                import traceback
                traceback.print_exc()

            await asyncio.sleep(self.polling_interval)

    async def cleanup(self):
        """Cleanup and disconnect."""
        print("\nCleaning up...")

        self.running = False

        if self.poly_stream:
            await self.poly_stream.disconnect()

        if self.ibkr_client and self.ibkr_client._connected:
            self.ibkr_client.disconnect()

        if self.ledger and self.mode != "analysis-only":
            # Export final trades
            self.ledger.export_to_csv()

            # Print PnL summary
            pnl = self.ledger.calculate_pnl()
            print("\n" + "=" * 70)
            print("FINAL PNL SUMMARY")
            print("=" * 70)
            print(f"Total Trades: {pnl['total_trades']}")
            print(f"Total Notional: ${pnl['total_notional']:.2f}")
            if pnl['positions']:
                print(f"\nOpen Positions: {len(pnl['positions'])}")
                for symbol, pos in list(pnl['positions'].items())[:5]:
                    print(f"  {symbol}: {pos['quantity']} @ avg ${pos['avg_price']:.4f}")

        print("\nBot stopped. Goodbye!")


async def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Unified Sentiment-Enhanced Trading Bot")
    parser.add_argument(
        "--mode",
        type=str,
        default="analysis-only",
        choices=["analysis-only", "paper", "live"],
        help="Trading mode (default: analysis-only)"
    )
    parser.add_argument(
        "--polling-interval",
        type=int,
        default=60,
        help="Seconds between signal updates (default: 60)"
    )
    parser.add_argument(
        "--no-sentiment",
        action="store_true",
        help="Disable sentiment analysis"
    )

    args = parser.parse_args()

    # Safety check for live mode
    if args.mode == "live":
        print("\n" + "!" * 70)
        print("WARNING: You are about to run in LIVE trading mode!")
        print("Real orders will be placed with real money.")
        print("!" * 70)
        response = input("\nType 'YES' to confirm: ")
        if response.strip().upper() != "YES":
            print("Live mode not confirmed. Exiting.")
            return

    # Create and run bot
    bot = UnifiedTradingBot(
        mode=args.mode,
        polling_interval=args.polling_interval,
        sentiment_enabled=not args.no_sentiment
    )

    await bot.initialize()
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
