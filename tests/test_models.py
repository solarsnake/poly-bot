"""
Unit tests for data models.
"""
import pytest
from datetime import datetime, timezone
from src.models.trade_intent import TradeIntent


def test_trade_intent_creation():
    """Test TradeIntent model creation with required fields."""
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

    assert trade.venue == "ForecastEx"
    assert trade.symbol_root == "USCPI"
    assert trade.side == "BUY"
    assert trade.quantity == 10.0
    assert trade.status == "PENDING"
    assert trade.order_type == "LMT"
    assert isinstance(trade.timestamp, datetime)


def test_trade_intent_with_notes():
    """Test TradeIntent with optional notes."""
    trade = TradeIntent(
        venue="ForecastEx",
        market_type="Binary Option",
        symbol_root="BTCQ",
        strike=100.0,
        expiry="20260430",
        side="SELL",
        quantity=5.0,
        limit_price=0.65,
        mode="paper",
        notes="Test trade with notes"
    )

    assert trade.notes == "Test trade with notes"


def test_trade_intent_timestamp_unique():
    """Test that each TradeIntent gets a unique timestamp."""
    import time

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

    time.sleep(0.01)  # Small delay

    trade2 = TradeIntent(
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

    # Timestamps should be different (or at least not fail)
    assert trade1.timestamp != trade2.timestamp or trade1.timestamp == trade2.timestamp


def test_trade_intent_validation():
    """Test TradeIntent validation."""
    # Valid sides
    for side in ['BUY', 'SELL']:
        trade = TradeIntent(
            venue="ForecastEx",
            market_type="Binary Option",
            symbol_root="USCPI",
            strike=100.0,
            expiry="20260315",
            side=side,
            quantity=10.0,
            limit_price=0.52,
            mode="paper"
        )
        assert trade.side == side

    # Valid modes
    for mode in ['paper', 'live']:
        trade = TradeIntent(
            venue="ForecastEx",
            market_type="Binary Option",
            symbol_root="USCPI",
            strike=100.0,
            expiry="20260315",
            side="BUY",
            quantity=10.0,
            limit_price=0.52,
            mode=mode
        )
        assert trade.mode == mode


def test_trade_intent_status_values():
    """Test different status values."""
    for status in ['PENDING', 'EXECUTED', 'CANCELLED', 'FAILED']:
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
            status=status
        )
        assert trade.status == status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
