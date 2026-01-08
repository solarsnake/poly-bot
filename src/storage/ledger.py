"""
Ledger module for recording and querying paper trades and PnL.
Supports both SQLite database and CSV exports.
"""
import sqlite3
import csv
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path
from src.models.trade_intent import TradeIntent


class TradeLedger:
    """Manages storage and retrieval of trade intents for paper trading."""

    def __init__(self, db_path: str = "data/trades.db", csv_path: str = "data/trades.csv"):
        """
        Initializes the TradeLedger with SQLite and CSV backends.
        Args:
            db_path: Path to the SQLite database file.
            csv_path: Path to the CSV file for exports.
        """
        self.db_path = db_path
        self.csv_path = csv_path

        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venue TEXT NOT NULL,
                market_type TEXT NOT NULL,
                symbol_root TEXT NOT NULL,
                strike REAL NOT NULL,
                expiry TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                limit_price REAL NOT NULL,
                order_type TEXT NOT NULL,
                mode TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                transaction_id TEXT,
                notes TEXT
            )
        """)

        # Create index on timestamp for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)
        """)

        # Create index on status for filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON trades(status)
        """)

        conn.commit()
        conn.close()
        print(f"Initialized trade ledger database at {self.db_path}")

    def record_trade(self, trade: TradeIntent) -> int:
        """
        Records a trade intent to the database.
        Args:
            trade: A TradeIntent object to record.
        Returns:
            The database row ID of the inserted trade.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trades (
                venue, market_type, symbol_root, strike, expiry,
                side, quantity, limit_price, order_type, mode,
                timestamp, status, transaction_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.venue,
            trade.market_type,
            trade.symbol_root,
            trade.strike,
            trade.expiry,
            trade.side,
            trade.quantity,
            trade.limit_price,
            trade.order_type,
            trade.mode,
            trade.timestamp.isoformat(),
            trade.status,
            trade.transaction_id,
            trade.notes
        ))

        row_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"Recorded trade: {trade.side} {trade.quantity} {trade.symbol_root} @ {trade.limit_price} (ID: {row_id})")
        return row_id

    def update_trade_status(self, row_id: int, status: str, transaction_id: Optional[str] = None, notes: Optional[str] = None):
        """
        Updates the status of a trade.
        Args:
            row_id: The database row ID of the trade.
            status: The new status ('PENDING', 'EXECUTED', 'CANCELLED', 'FAILED').
            transaction_id: Optional transaction ID to update.
            notes: Optional notes to append or update.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        update_fields = ["status = ?"]
        update_values = [status]

        if transaction_id is not None:
            update_fields.append("transaction_id = ?")
            update_values.append(transaction_id)

        if notes is not None:
            update_fields.append("notes = ?")
            update_values.append(notes)

        update_values.append(row_id)

        cursor.execute(f"""
            UPDATE trades
            SET {', '.join(update_fields)}
            WHERE id = ?
        """, update_values)

        conn.commit()
        conn.close()

        print(f"Updated trade {row_id}: status={status}")

    def get_trades(
        self,
        status: Optional[str] = None,
        venue: Optional[str] = None,
        symbol_root: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieves trades from the database with optional filters.
        Args:
            status: Filter by status ('PENDING', 'EXECUTED', etc.)
            venue: Filter by venue (e.g., 'ForecastEx')
            symbol_root: Filter by symbol root (e.g., 'USCPI')
            limit: Maximum number of trades to return
        Returns:
            A list of trade dictionaries.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM trades WHERE 1=1"
        params = []

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        if venue is not None:
            query += " AND venue = ?"
            params.append(venue)

        if symbol_root is not None:
            query += " AND symbol_root = ?"
            params.append(symbol_root)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        trades = [dict(row) for row in rows]
        conn.close()

        return trades

    def export_to_csv(self, output_path: Optional[str] = None):
        """
        Exports all trades to a CSV file.
        Args:
            output_path: Optional custom output path. If None, uses self.csv_path.
        """
        if output_path is None:
            output_path = self.csv_path

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC")
        rows = cursor.fetchall()

        if rows:
            with open(output_path, 'w', newline='') as csvfile:
                fieldnames = rows[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))

            print(f"Exported {len(rows)} trades to {output_path}")
        else:
            print("No trades to export.")

        conn.close()

    def calculate_pnl(self, symbol_root: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates simple PnL metrics for executed paper trades.
        Note: This is a simplified PnL calculation for paper trading.
        In production, you'd track fills, actual execution prices, and settlements.

        Args:
            symbol_root: Optional filter by symbol root.
        Returns:
            A dictionary with PnL metrics.
        """
        trades = self.get_trades(status='EXECUTED', symbol_root=symbol_root, limit=10000)

        if not trades:
            return {
                'total_trades': 0,
                'total_notional': 0.0,
                'avg_price': 0.0,
                'positions': {}
            }

        total_notional = 0.0
        positions = {}  # symbol -> {'quantity': X, 'avg_price': Y}

        for trade in trades:
            symbol = f"{trade['symbol_root']}-{trade['strike']}-{trade['expiry']}"
            notional = trade['quantity'] * trade['limit_price']

            if trade['side'] == 'BUY':
                total_notional -= notional
                if symbol not in positions:
                    positions[symbol] = {'quantity': 0.0, 'total_cost': 0.0}
                positions[symbol]['quantity'] += trade['quantity']
                positions[symbol]['total_cost'] += notional
            elif trade['side'] == 'SELL':
                total_notional += notional
                if symbol not in positions:
                    positions[symbol] = {'quantity': 0.0, 'total_cost': 0.0}
                positions[symbol]['quantity'] -= trade['quantity']
                positions[symbol]['total_cost'] -= notional

        # Calculate average price per position
        for symbol in positions:
            if positions[symbol]['quantity'] != 0:
                positions[symbol]['avg_price'] = positions[symbol]['total_cost'] / positions[symbol]['quantity']
            else:
                positions[symbol]['avg_price'] = 0.0

        return {
            'total_trades': len(trades),
            'total_notional': total_notional,
            'positions': positions
        }


# Example usage
if __name__ == "__main__":
    # Create a ledger instance
    ledger = TradeLedger()

    # Create a sample trade
    sample_trade = TradeIntent(
        venue="ForecastEx",
        market_type="Binary Option",
        symbol_root="USCPI",
        strike=100.0,
        expiry="20260315",
        side="BUY",
        quantity=10.0,
        limit_price=0.52,
        mode="paper",
        notes="Test trade"
    )

    # Record the trade
    trade_id = ledger.record_trade(sample_trade)

    # Update its status
    ledger.update_trade_status(trade_id, "EXECUTED", transaction_id="TEST-001")

    # Query trades
    trades = ledger.get_trades(status="EXECUTED")
    print(f"\nFound {len(trades)} executed trades:")
    for trade in trades:
        print(f"  - {trade['side']} {trade['quantity']} {trade['symbol_root']} @ {trade['limit_price']}")

    # Calculate PnL
    pnl = ledger.calculate_pnl()
    print(f"\nPnL Summary:")
    print(f"  Total trades: {pnl['total_trades']}")
    print(f"  Total notional: ${pnl['total_notional']:.2f}")
    print(f"  Positions: {pnl['positions']}")

    # Export to CSV
    ledger.export_to_csv()
