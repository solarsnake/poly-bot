"""
ForecastEx Execution Engine with yield-adjusted fair value calculation.
Supports both paper and live trading modes.
"""
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from ib_insync import Contract, Order, Ticker
from src.execution.ibkr_client import IBKRClient
from src.execution.forecastex_contracts import ForecastExContractFactory
from src.models.trade_intent import TradeIntent
from src.storage.ledger import TradeLedger
from src.signal_server.config import settings


class ExecutionEngine:
    """
    Execution engine for ForecastEx binary options with yield-adjusted fair value.
    Supports both paper trading (default) and live execution.
    """

    def __init__(
        self,
        ibkr_client: IBKRClient,
        contract_factory: ForecastExContractFactory,
        ledger: TradeLedger,
        mode: str = "paper",
        arb_threshold: float = 0.02,
        risk_free_rate: Optional[float] = None
    ):
        """
        Initializes the ExecutionEngine.
        Args:
            ibkr_client: An IBKRClient instance.
            contract_factory: A ForecastExContractFactory instance.
            ledger: A TradeLedger instance for recording trades.
            mode: Trading mode ('paper' or 'live'). Default is 'paper'.
            arb_threshold: Minimum spread for arb opportunities (e.g., 0.02 = 2%).
            risk_free_rate: Annual risk-free rate (e.g., 0.045 = 4.5%). Defaults to settings.
        """
        self.ibkr_client = ibkr_client
        self.contract_factory = contract_factory
        self.ledger = ledger
        self.mode = mode
        self.arb_threshold = arb_threshold
        self.risk_free_rate = risk_free_rate if risk_free_rate is not None else settings.RISK_FREE_RATE

        # Validate mode
        if mode not in ['paper', 'live']:
            raise ValueError(f"Invalid mode: {mode}. Must be 'paper' or 'live'.")

        # Safety check for live mode
        if mode == 'live' and not settings.ALLOW_US_EXECUTION:
            raise ValueError("Live execution is disabled in settings. Set ALLOW_US_EXECUTION=true to enable.")

        print(f"ExecutionEngine initialized in {mode.upper()} mode with {arb_threshold*100:.1f}% arb threshold.")

    def calculate_yield_adjusted_fair_value(
        self,
        p_poly: float,
        days_to_expiry: int,
        r: Optional[float] = None
    ) -> float:
        """
        Calculates the yield-adjusted fair value for a ForecastEx contract.
        Formula: P_FX = p_poly * (1 + r * t_days / 365)

        Args:
            p_poly: Polymarket probability (0-1).
            days_to_expiry: Number of days until expiry.
            r: Annual risk-free rate (optional, defaults to self.risk_free_rate).
        Returns:
            The yield-adjusted fair value (0-1).
        """
        if r is None:
            r = self.risk_free_rate

        if days_to_expiry < 0:
            days_to_expiry = 0

        p_fx_fair = p_poly * (1 + r * days_to_expiry / 365)

        # Cap at 1.0 since probabilities can't exceed 100%
        return min(p_fx_fair, 1.0)

    def calculate_arb_spread(
        self,
        p_poly: float,
        p_fx_market: float,
        days_to_expiry: int
    ) -> float:
        """
        Calculates the arbitrage spread between Polymarket and ForecastEx.
        Args:
            p_poly: Polymarket probability (0-1).
            p_fx_market: ForecastEx market price (0-1).
            days_to_expiry: Number of days until expiry.
        Returns:
            The arb spread (positive = buy opportunity on ForecastEx).
        """
        p_fx_fair = self.calculate_yield_adjusted_fair_value(p_poly, days_to_expiry)
        spread = p_fx_fair - p_fx_market

        return spread

    async def get_contract_price(self, contract: Contract, timeout: int = 5) -> Optional[float]:
        """
        Gets the current market price (midpoint of bid/ask) for a contract.
        Args:
            contract: The ib_insync.Contract to price.
            timeout: Seconds to wait for market data.
        Returns:
            The midpoint price or None if not available.
        """
        ticker = await self.ibkr_client.req_market_data(contract)

        # Wait for market data to arrive
        for _ in range(timeout * 2):  # Check every 0.5 seconds
            await asyncio.sleep(0.5)
            if ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                midpoint = (ticker.bid + ticker.ask) / 2.0
                print(f"Contract {contract.localSymbol}: bid={ticker.bid:.4f}, ask={ticker.ask:.4f}, mid={midpoint:.4f}")
                return midpoint

        print(f"Warning: Could not get valid market data for {contract.localSymbol} within {timeout}s")
        return None

    def create_trade_intent(
        self,
        description: str,
        strike: float,
        expiry_date: str,
        is_yes: bool,
        side: str,
        quantity: float,
        limit_price: float,
        notes: Optional[str] = None
    ) -> TradeIntent:
        """
        Creates a TradeIntent object for a ForecastEx trade.
        Args:
            description: Human description (e.g., "US CPI YoY").
            strike: Strike price.
            expiry_date: Expiry date in YYYY-MM-DD format.
            is_yes: True for Yes (Call), False for No (Put).
            side: 'BUY' or 'SELL'.
            quantity: Number of contracts.
            limit_price: Limit price (0-1).
            notes: Optional notes.
        Returns:
            A TradeIntent object.
        """
        symbol_root = self.contract_factory.get_forecastex_contract(
            description, strike, expiry_date, is_yes
        )
        if not symbol_root:
            raise ValueError(f"Could not find contract for {description}")

        symbol_root_str = symbol_root.symbol if hasattr(symbol_root, 'symbol') else description

        trade_intent = TradeIntent(
            venue="ForecastEx",
            market_type="Binary Option",
            symbol_root=symbol_root_str,
            strike=strike,
            expiry=expiry_date.replace('-', ''),
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            mode=self.mode,
            notes=notes
        )

        return trade_intent

    async def execute_trade_intent(self, trade_intent: TradeIntent) -> bool:
        """
        Executes a TradeIntent (paper or live).
        Args:
            trade_intent: The TradeIntent to execute.
        Returns:
            True if successful, False otherwise.
        """
        # Record the intent in the ledger
        trade_id = self.ledger.record_trade(trade_intent)

        if self.mode == "paper":
            # Paper trading: just log it as executed
            print(f"[PAPER] Simulating execution: {trade_intent.side} {trade_intent.quantity} {trade_intent.symbol_root} @ {trade_intent.limit_price}")
            self.ledger.update_trade_status(
                trade_id,
                "EXECUTED",
                transaction_id=f"PAPER-{trade_id}",
                notes=f"Paper trade executed at {datetime.now(timezone.utc).isoformat()}"
            )
            return True

        elif self.mode == "live":
            # Live trading: place actual order via IBKR
            print(f"[LIVE] Placing order: {trade_intent.side} {trade_intent.quantity} {trade_intent.symbol_root} @ {trade_intent.limit_price}")

            # Get the contract
            contract = self.contract_factory.get_forecastex_contract(
                trade_intent.symbol_root,
                trade_intent.strike,
                f"{trade_intent.expiry[:4]}-{trade_intent.expiry[4:6]}-{trade_intent.expiry[6:]}",
                is_yes=(trade_intent.side == "BUY")  # Simplified assumption
            )

            if not contract:
                print(f"Error: Could not find contract for {trade_intent.symbol_root}")
                self.ledger.update_trade_status(trade_id, "FAILED", notes="Contract not found")
                return False

            # Create the order
            order = Order(
                action=trade_intent.side,
                totalQuantity=trade_intent.quantity,
                orderType=trade_intent.order_type,
                lmtPrice=trade_intent.limit_price
            )

            # Place the order
            try:
                trade = self.ibkr_client.place_order(contract, order)
                if trade:
                    self.ledger.update_trade_status(
                        trade_id,
                        "EXECUTED",
                        transaction_id=str(trade.order.orderId),
                        notes=f"Live order placed: {trade.orderStatus.status}"
                    )
                    return True
                else:
                    self.ledger.update_trade_status(trade_id, "FAILED", notes="Order placement failed")
                    return False
            except Exception as e:
                print(f"Error placing order: {e}")
                self.ledger.update_trade_status(trade_id, "FAILED", notes=f"Exception: {str(e)}")
                return False

        return False

    async def evaluate_arb_opportunity(
        self,
        description: str,
        strike: float,
        expiry_date: str,
        is_yes: bool,
        p_poly: float,
        days_to_expiry: int,
        quantity: float = 10.0
    ) -> Optional[TradeIntent]:
        """
        Evaluates an arbitrage opportunity and returns a TradeIntent if viable.
        Args:
            description: Human description of the contract.
            strike: Strike price.
            expiry_date: Expiry date in YYYY-MM-DD format.
            is_yes: True for Yes contract, False for No.
            p_poly: Polymarket probability.
            days_to_expiry: Days until expiry.
            quantity: Quantity to trade if opportunity exists.
        Returns:
            A TradeIntent if an arb exists, otherwise None.
        """
        # Get the ForecastEx contract
        contract = self.contract_factory.get_forecastex_contract(
            description, strike, expiry_date, is_yes
        )

        if not contract:
            print(f"Warning: Could not find contract for {description}")
            return None

        # Get current market price
        p_fx_market = await self.get_contract_price(contract)

        if p_fx_market is None:
            print(f"Warning: Could not get market price for {description}")
            return None

        # Calculate arb spread
        arb_spread = self.calculate_arb_spread(p_poly, p_fx_market, days_to_expiry)

        print(f"\nArb Analysis for {description}:")
        print(f"  Polymarket prob: {p_poly:.4f}")
        print(f"  ForecastEx price: {p_fx_market:.4f}")
        print(f"  Yield-adjusted fair: {self.calculate_yield_adjusted_fair_value(p_poly, days_to_expiry):.4f}")
        print(f"  Arb spread: {arb_spread:.4f} ({arb_spread*100:.2f}%)")

        # Check if arb exceeds threshold
        if arb_spread > self.arb_threshold:
            print(f"  -> ARB OPPORTUNITY DETECTED! Spread {arb_spread*100:.2f}% > threshold {self.arb_threshold*100:.2f}%")

            # Create trade intent to buy at ForecastEx (it's undervalued)
            trade_intent = self.create_trade_intent(
                description=description,
                strike=strike,
                expiry_date=expiry_date,
                is_yes=is_yes,
                side="BUY",
                quantity=quantity,
                limit_price=p_fx_market,
                notes=f"Arb opp: spread={arb_spread*100:.2f}%, poly={p_poly:.4f}, fx={p_fx_market:.4f}"
            )

            return trade_intent
        else:
            print(f"  -> No arb: spread {arb_spread*100:.2f}% < threshold {self.arb_threshold*100:.2f}%")
            return None


# Example usage
async def main():
    from src.signal_server.config import settings

    # Initialize components
    ibkr_client = IBKRClient()
    await ibkr_client.connect()

    if not ibkr_client._connected:
        print("Failed to connect to IBKR. Exiting.")
        return

    contract_factory = ForecastExContractFactory(ibkr_client)
    ledger = TradeLedger()

    # Create execution engine in paper mode
    engine = ExecutionEngine(
        ibkr_client=ibkr_client,
        contract_factory=contract_factory,
        ledger=ledger,
        mode="paper",
        arb_threshold=0.02
    )

    # Example: Evaluate an arb opportunity
    # In practice, p_poly would come from the Polymarket MCP server
    example_p_poly = 0.48  # 48% probability from Polymarket
    example_days_to_expiry = 45

    trade_intent = await engine.evaluate_arb_opportunity(
        description="US CPI YoY",
        strike=100.0,
        expiry_date="2026-03-15",
        is_yes=True,
        p_poly=example_p_poly,
        days_to_expiry=example_days_to_expiry,
        quantity=10.0
    )

    if trade_intent:
        # Execute the trade (paper mode)
        success = await engine.execute_trade_intent(trade_intent)
        print(f"\nTrade execution: {'SUCCESS' if success else 'FAILED'}")
    else:
        print("\nNo trade executed - no arb opportunity.")

    # Show recent trades
    recent_trades = ledger.get_trades(limit=5)
    print(f"\nRecent trades ({len(recent_trades)}):")
    for trade in recent_trades:
        print(f"  - {trade['side']} {trade['quantity']} {trade['symbol_root']} @ {trade['limit_price']} [{trade['status']}]")

    ibkr_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
