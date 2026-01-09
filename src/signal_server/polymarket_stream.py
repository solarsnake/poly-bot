"""
Real-time Polymarket CLOB WebSocket streaming client.
Streams live order book updates for continuous VWAP calculation.
"""
import asyncio
import json
import websockets
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime


class PolymarketStream:
    """
    WebSocket client for Polymarket CLOB real-time order book streaming.

    WebSocket endpoint: wss://ws-subscriptions-clob.polymarket.com/ws
    """

    def __init__(self, url: str = "wss://ws-subscriptions-clob.polymarket.com/ws"):
        """
        Initialize Polymarket streaming client.

        Args:
            url: WebSocket endpoint URL
        """
        self.url = url
        self.ws = None
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.running = False

    async def connect(self):
        """Establish WebSocket connection."""
        try:
            self.ws = await websockets.connect(self.url)
            self.running = True
            print(f"✓ Connected to Polymarket WebSocket: {self.url}")
        except Exception as e:
            print(f"✗ Failed to connect to Polymarket WebSocket: {e}")
            raise

    async def disconnect(self):
        """Close WebSocket connection."""
        self.running = False
        if self.ws:
            await self.ws.close()
            print("Disconnected from Polymarket WebSocket")

    async def subscribe_to_market(
        self,
        market_id: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Subscribe to a specific market's order book updates.

        Args:
            market_id: The market ID (condition_id or token_id)
            callback: Function to call when updates arrive

        Example message format:
        {
            "type": "subscribe",
            "market": "0x123abc...",
            "asset_id": "456def..."
        }
        """
        if not self.ws or not self.running:
            print("Not connected. Call connect() first.")
            return

        subscription_msg = {
            "type": "subscribe",
            "market": market_id
        }

        await self.ws.send(json.dumps(subscription_msg))

        self.subscriptions[market_id] = {
            'callback': callback,
            'subscribed_at': datetime.now(),
            'last_update': None,
            'order_book': {'bids': [], 'asks': []}
        }

        print(f"✓ Subscribed to market: {market_id}")

    async def unsubscribe_from_market(self, market_id: str):
        """Unsubscribe from a market."""
        if not self.ws or not self.running:
            return

        unsubscribe_msg = {
            "type": "unsubscribe",
            "market": market_id
        }

        await self.ws.send(json.dumps(unsubscribe_msg))

        if market_id in self.subscriptions:
            del self.subscriptions[market_id]

        print(f"Unsubscribed from market: {market_id}")

    async def listen(self):
        """
        Listen for incoming WebSocket messages and dispatch to callbacks.
        This should run in a background task.
        """
        if not self.ws:
            print("Not connected. Call connect() first.")
            return

        print("Listening for market updates...")

        try:
            async for message in self.ws:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
            self.running = False
        except Exception as e:
            print(f"Error in listen loop: {e}")
            self.running = False

    async def _handle_message(self, message: str):
        """
        Handle incoming WebSocket message.

        Expected message types:
        - orderbook: Full order book snapshot
        - trade: Individual trade execution
        - update: Order book update (add/remove orders)
        """
        try:
            data = json.loads(message)

            msg_type = data.get('type')
            market_id = data.get('market')

            if not market_id or market_id not in self.subscriptions:
                return

            subscription = self.subscriptions[market_id]
            subscription['last_update'] = datetime.now()

            # Update local order book
            if msg_type == 'orderbook':
                # Full snapshot
                subscription['order_book'] = {
                    'bids': data.get('bids', []),
                    'asks': data.get('asks', [])
                }
            elif msg_type == 'update':
                # Incremental update
                self._apply_order_book_update(subscription['order_book'], data)

            # Call user callback
            if subscription['callback']:
                await subscription['callback'](data)

        except json.JSONDecodeError:
            print(f"Failed to parse message: {message[:100]}...")
        except Exception as e:
            print(f"Error handling message: {e}")

    def _apply_order_book_update(self, order_book: Dict[str, List], update: Dict[str, Any]):
        """
        Apply incremental order book update.

        Updates can be:
        - Add order: {'side': 'bid', 'price': '0.52', 'size': '100'}
        - Remove order: {'side': 'ask', 'price': '0.54', 'size': '0'}
        - Modify order: {'side': 'bid', 'price': '0.52', 'size': '50'}
        """
        side = update.get('side', '').lower()
        price = float(update.get('price', 0))
        size = float(update.get('size', 0))

        if side not in ['bid', 'ask']:
            return

        orders = order_book.get(f"{side}s", [])

        # Find existing order at this price
        existing_index = None
        for i, order in enumerate(orders):
            if abs(float(order[0]) - price) < 0.0001:  # Price match with tolerance
                existing_index = i
                break

        if size == 0:
            # Remove order
            if existing_index is not None:
                orders.pop(existing_index)
        else:
            # Add or update order
            if existing_index is not None:
                orders[existing_index] = [price, size]
            else:
                orders.append([price, size])
                # Re-sort
                reverse = (side == 'bid')  # Bids descending, asks ascending
                orders.sort(key=lambda x: x[0], reverse=reverse)

    def get_current_order_book(self, market_id: str, n_levels: int = 3) -> Dict[str, List]:
        """
        Get current order book for a market.

        Args:
            market_id: Market ID
            n_levels: Number of price levels to return

        Returns:
            Dict with 'bids' and 'asks', each a list of [price, size]
        """
        if market_id not in self.subscriptions:
            return {'bids': [], 'asks': []}

        order_book = self.subscriptions[market_id]['order_book']

        return {
            'bids': order_book['bids'][:n_levels],
            'asks': order_book['asks'][:n_levels]
        }

    def calculate_vwap(self, market_id: str, n_levels: int = 3) -> Optional[float]:
        """
        Calculate VWAP from current order book.

        Args:
            market_id: Market ID
            n_levels: Number of levels for VWAP calculation

        Returns:
            VWAP probability (0-1) or None if no liquidity
        """
        order_book = self.get_current_order_book(market_id, n_levels)

        bids = order_book['bids']
        asks = order_book['asks']

        total_bid_value = sum(float(price) * float(size) for price, size in bids)
        total_bid_size = sum(float(size) for _, size in bids)

        total_ask_value = sum(float(price) * float(size) for price, size in asks)
        total_ask_size = sum(float(size) for _, size in asks)

        if total_bid_size == 0 and total_ask_size == 0:
            return None

        vwap_bid = total_bid_value / total_bid_size if total_bid_size > 0 else 0
        vwap_ask = total_ask_value / total_ask_size if total_ask_size > 0 else 0

        if total_bid_size > 0 and total_ask_size > 0:
            return (vwap_bid + vwap_ask) / 2
        elif total_bid_size > 0:
            return vwap_bid
        else:
            return vwap_ask


# Example usage
async def main():
    """Example of streaming Polymarket order books."""
    print("=" * 70)
    print("POLYMARKET WEBSOCKET STREAMING DEMO")
    print("=" * 70)
    print()

    stream = PolymarketStream()

    # Callback for market updates
    async def on_market_update(data: Dict[str, Any]):
        market_id = data.get('market', 'unknown')[:8]
        msg_type = data.get('type', 'unknown')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Market {market_id}... - Type: {msg_type}")

        # Calculate and print VWAP
        vwap = stream.calculate_vwap(data.get('market'))
        if vwap:
            print(f"  Current VWAP: {vwap:.4f} ({vwap*100:.2f}%)")

    try:
        # Connect
        await stream.connect()

        # Subscribe to example markets (replace with real market IDs)
        example_markets = [
            "0x1234abcd...",  # Replace with real Polymarket market ID
            # Add more markets here
        ]

        for market_id in example_markets:
            await stream.subscribe_to_market(market_id, on_market_update)

        # Listen for updates (this runs continuously)
        print()
        print("Streaming updates... (Ctrl+C to stop)")
        print()

        await stream.listen()

    except KeyboardInterrupt:
        print("\n\nStopping stream...")
    except Exception as e:
        print(f"\n\nError: {e}")
    finally:
        await stream.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
