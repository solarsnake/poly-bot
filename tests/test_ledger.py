"""
Unit tests for trade ledger.
"""
import pytest
import os
import tempfile
from pathlib import Path
from src.storage.ledger import TradeLedger
from src.models.trade_intent import TradeIntent


@pytest.fixture
def temp_ledger():
    """Create a temporary ledger for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_trades.db")
        csv_path = os.path.join(tmpdir, "test_trades.csv")
        ledger = TradeLedger(db_path=db_path, csv_path=csv_path)
        yield ledger


def test_ledger_initialization(temp_ledger):
    """Test ledger database initialization."""
    assert os.path.exists(temp_ledger.db_path)

    # Verify tables were created
    import sqlite3
    conn = sqlite3.connect(temp_ledger.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == "trades"


def test_record_trade(temp_ledger):
    """Test recording a trade."""
    trade = TradeIntent(
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

    trade_id = temp_ledger.record_trade(trade)
    assert trade_id > 0


def test_update_trade_status(temp_ledger):
    """Test updating trade status."""
    trade = TradeIntent(
        venue="ForecastEx",
        market_type="Binary Option",
        symbol_root="USCPI",
        strike=100.0,
        expiry="20260315",
        side="BUY",
        quantity=10.0,
        limit_price=0.52,
        mode="paper"
    )

    trade_id = temp_ledger.record_trade(trade)
    temp_ledger.update_trade_status(trade_id, "EXECUTED", transaction_id="TEST-001")

    # Verify update
    trades = temp_ledger.get_trades(status="EXECUTED")
    assert len(trades) == 1
    assert trades[0]['status'] == "EXECUTED"
    assert trades[0]['transaction_id'] == "TEST-001"


def test_get_trades_filter_by_status(temp_ledger):
    """Test filtering trades by status."""
    # Create multiple trades with different statuses
    for i, status in enumerate(['PENDING', 'EXECUTED', 'CANCELLED']):
        trade = TradeIntent(
            venue="ForecastEx",
            market_type="Binary Option",
            symbol_root=f"SYM{i}",
            strike=100.0,
            expiry="20260315",
            side="BUY",
            quantity=10.0,
            limit_price=0.52,
            mode="paper",
            status=status
        )
        temp_ledger.record_trade(trade)

    # Filter by each status
    pending = temp_ledger.get_trades(status="PENDING")
    assert len(pending) == 1

    executed = temp_ledger.get_trades(status="EXECUTED")
    assert len(executed) == 1

    cancelled = temp_ledger.get_trades(status="CANCELLED")
    assert len(cancelled) == 1


def test_get_trades_filter_by_venue(temp_ledger):
    """Test filtering trades by venue."""
    trade1 = TradeIntent(
        venue="ForecastEx",
        market_type="Binary Option",
        symbol_root="USCPI",
        strike=100.0,
        expiry="20260315",
        side="BUY",
        quantity=10.0,
        limit_price=0.52,
        mode="paper"
    )

    trade2 = TradeIntent(
        venue="OtherVenue",
        market_type="Binary Option",
        symbol_root="BTCQ",
        strike=100.0,
        expiry="20260315",
        side="BUY",
        quantity=5.0,
        limit_price=0.65,
        mode="paper"
    )

    temp_ledger.record_trade(trade1)
    temp_ledger.record_trade(trade2)

    fx_trades = temp_ledger.get_trades(venue="ForecastEx")
    assert len(fx_trades) == 1
    assert fx_trades[0]['venue'] == "ForecastEx"


def test_export_to_csv(temp_ledger):
    """Test CSV export functionality."""
    # Create a few trades
    for i in range(3):
        trade = TradeIntent(
            venue="ForecastEx",
            market_type="Binary Option",
            symbol_root=f"SYM{i}",
            strike=100.0,
            expiry="20260315",
            side="BUY",
            quantity=10.0,
            limit_price=0.52,
            mode="paper"
        )
        temp_ledger.record_trade(trade)

    # Export to CSV
    temp_ledger.export_to_csv()

    # Verify CSV was created
    assert os.path.exists(temp_ledger.csv_path)

    # Verify CSV contents
    import csv
    with open(temp_ledger.csv_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 3


def test_calculate_pnl_simple(temp_ledger):
    """Test simple PnL calculation."""
    # Create and execute a buy trade
    trade1 = TradeIntent(
        venue="ForecastEx",
        market_type="Binary Option",
        symbol_root="USCPI",
        strike=100.0,
        expiry="20260315",
        side="BUY",
        quantity=10.0,
        limit_price=0.52,
        mode="paper",
        status="EXECUTED"
    )
    temp_ledger.record_trade(trade1)

    # Calculate PnL
    pnl = temp_ledger.calculate_pnl()

    assert pnl['total_trades'] == 1
    assert pnl['total_notional'] == -5.2  # -10 * 0.52
    assert len(pnl['positions']) == 1


def test_calculate_pnl_multiple_trades(temp_ledger):
    """Test PnL calculation with multiple trades."""
    # Buy 10 @ 0.52
    trade1 = TradeIntent(
        venue="ForecastEx",
        market_type="Binary Option",
        symbol_root="USCPI",
        strike=100.0,
        expiry="20260315",
        side="BUY",
        quantity=10.0,
        limit_price=0.52,
        mode="paper",
        status="EXECUTED"
    )
    temp_ledger.record_trade(trade1)

    # Sell 5 @ 0.58
    trade2 = TradeIntent(
        venue="ForecastEx",
        market_type="Binary Option",
        symbol_root="USCPI",
        strike=100.0,
        expiry="20260315",
        side="SELL",
        quantity=5.0,
        limit_price=0.58,
        mode="paper",
        status="EXECUTED"
    )
    temp_ledger.record_trade(trade2)

    # Calculate PnL
    pnl = temp_ledger.calculate_pnl()

    assert pnl['total_trades'] == 2
    # -10*0.52 + 5*0.58 = -5.2 + 2.9 = -2.3
    assert abs(pnl['total_notional'] - (-2.3)) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
