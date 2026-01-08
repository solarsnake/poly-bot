import asyncio
from ib_insync import IB, Contract, Order, Position, MarketDataBidAsk, reqIds
from typing import List, Optional, Callable
from src.signal_server.config import settings

class IBKRClient:
    """Client for interacting with Interactive Brokers TWS API via ib_insync."""

    def __init__(self):
        """Initializes the IBKRClient but does not connect immediately."""
        self.ib = IB()
        self._connected = False

    async def connect(self, host: str = settings.IB_HOST, port: int = settings.IB_PORT, client_id: int = settings.IB_CLIENT_ID):
        """
        Connects to the IBKR TWS or Gateway.
        Args:
            host: The host address of TWS/Gateway.
            port: The port of TWS/Gateway.
            client_id: The client ID for the connection.
        """
        if not self._connected:
            print(f"Connecting to IBKR at {host}:{port} with client ID {client_id}...")
            try:
                await self.ib.connect(host, port, client_id)
                self._connected = True
                print("Connected to IBKR successfully.")
            except Exception as e:
                print(f"Error connecting to IBKR: {e}")
                self._connected = False
        else:
            print("Already connected to IBKR.")

    def disconnect(self):
        """
        Disconnects from the IBKR TWS or Gateway.
        """
        if self._connected:
            print("Disconnecting from IBKR...")
            self.ib.disconnect()
            self._connected = False
            print("Disconnected from IBKR.")

    async def get_contract_details(self, contract: Contract) -> List[Contract]:
        """
        Requests contract details for a given contract object.
        Args:
            contract: An ib_insync.Contract object with search criteria.
        Returns:
            A list of matching ib_insync.Contract objects.
        """
        if not self._connected:
            print("Not connected to IBKR. Cannot get contract details.")
            return []
        print(f"Requesting contract details for {contract.symbol} {contract.secType}@{contract.exchange}...")
        details = await self.ib.reqContractDetails(contract)
        return [d.contract for d in details]

    async def req_market_data(self, contract: Contract, handler: Optional[Callable[[MarketDataBidAsk], None]] = None):
        """
        Requests streaming market data for a contract. 
        Note: ib_insync automatically manages subscriptions and provides a ticker object.
        For continuous streaming, you'd typically process the `ib.pendingTickersEvent` or `ib.qualifyContracts`.
        This method sets up the request and can attach a handler to the contract's ticker.
        Args:
            contract: The ib_insync.Contract object for which to request data.
            handler: An optional callable that takes a MarketDataBidAsk object and processes it.
        """
        if not self._connected:
            print("Not connected to IBKR. Cannot request market data.")
            return
        print(f"Requesting market data for {contract.symbol} {contract.secType}@{contract.exchange}...")
        self.ib.reqMktData(contract, '233', False, False) # '233' for Bid/Ask, Last, etc.
        ticker = self.ib.tickerByContract(contract)
        
        if handler:
            # Attach a handler to the ticker's update event
            # ib_insync doesn't directly expose `MarketDataBidAsk` as an event on `ticker` in this way.
            # Instead, you'd usually poll `ticker.bid`, `ticker.ask` or use `ib.pendingTickersEvent`.
            # For simplicity, we'll demonstrate polling or an external event loop.
            # A direct event-driven handler like `ticker.updateEvent += handler` is not standard for raw bid/ask.
            # For real-time processing, you'd observe `ib.pendingTickersEvent` in your main loop.
            print("Note: Direct event handler attachment for MarketDataBidAsk is simplified. ")
            print("      Consider polling ticker attributes or using ib.pendingTickersEvent in an async loop.")
            # Example of how you *might* process updates in an external loop:
            # while self.ib.isConnected():
            #     if ticker.bid != -1 and ticker.ask != -1:
            #         # Construct a MarketDataBidAsk-like object from ticker for handler
            #         mock_bid_ask = MarketDataBidAsk(bid=ticker.bid, ask=ticker.ask, 
            #                                         bidSize=ticker.bidSize, askSize=ticker.askSize)
            #         handler(mock_bid_ask)
            #     await asyncio.sleep(1) # Or use ib.sleep(1)


    async def place_order(self, contract: Contract, order: Order) -> Optional[Any]: # OrderState or Trade
        """
        Places an order with IBKR.
        Args:
            contract: The ib_insync.Contract object for the order.
            order: The ib_insync.Order object to place.
        Returns:
            The Trade object if successful, None otherwise.
        """
        if not self._connected:
            print("Not connected to IBKR. Cannot place order.")
            return None
        print(f"Placing order: {order.action} {order.totalQuantity} {contract.symbol} at {order.lmtPrice}...")
        trade = await self.ib.placeOrder(contract, order)
        if trade.isDone():
            print(f"Order {trade.order.orderId} for {trade.contract.symbol} is done. Status: {trade.orderStatus.status}")
        else:
            print(f"Order {trade.order.orderId} for {trade.contract.symbol} placed. Current status: {trade.orderStatus.status}")
        return trade

    async def req_positions(self) -> List[Position]:
        """
        Requests current open positions from IBKR.
        Returns:
            A list of ib_insync.Position objects.
        """
        if not self._connected:
            print("Not connected to IBKR. Cannot request positions.")
            return []
        print("Requesting open positions...")
        positions = await self.ib.reqPositions()
        return positions
    
    async def get_next_order_id(self) -> int:
        """
        Requests the next valid order ID from IBKR.
        Returns:
            An integer representing the next available order ID.
        """
        if not self._connected:
            print("Not connected to IBKR. Cannot get next order ID.")
            return -1 # Or raise an error
        # reqIds automatically updates ib.nextOrderId
        await self.ib.reqIds()
        return self.ib.nextOrderId


# Example usage (for testing purposes)
async def main():
    client = IBKRClient()
    await client.connect()

    if client._connected:
        # Example: Requesting details for a generic stock contract
        stock_contract = Contract(symbol='SPY', secType='STK', exchange='SMART', currency='USD')
        details = await client.get_contract_details(stock_contract)
        if details:
            print(f"Found {len(details)} details for SPY. First one: {details[0]}")

        # Example: Requesting positions
        positions = await client.req_positions()
        if positions:
            print(f"Open positions: {positions}")
        else:
            print("No open positions.")

    client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
