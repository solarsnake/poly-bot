"""
Unit tests for configuration.
"""
import pytest
import os
from src.signal_server.config import settings


def test_settings_load():
    """Test that settings load successfully."""
    assert settings.USER_REGION is not None
    assert isinstance(settings.ALLOW_POLYMARKET_EXECUTION, bool)
    assert isinstance(settings.ALLOW_US_EXECUTION, bool)
    assert settings.IB_HOST is not None
    assert isinstance(settings.IB_PORT, int)
    assert isinstance(settings.IB_CLIENT_ID, int)
    assert isinstance(settings.RISK_FREE_RATE, float)


def test_default_values():
    """Test default configuration values."""
    assert settings.ALLOW_POLYMARKET_EXECUTION == False  # Must be False
    assert settings.ALLOW_US_EXECUTION == True
    assert settings.IB_HOST == "127.0.0.1"
    assert settings.IB_PORT == 4002
    assert settings.IB_CLIENT_ID == 1
    assert settings.RISK_FREE_RATE == 0.045


def test_polymarket_execution_disabled():
    """Test that Polymarket execution is disabled (safety check)."""
    assert settings.ALLOW_POLYMARKET_EXECUTION == False, \
        "CRITICAL: ALLOW_POLYMARKET_EXECUTION must be False. This is a read-only system."


def test_us_execution_enabled():
    """Test that US execution is enabled."""
    assert settings.ALLOW_US_EXECUTION == True


def test_risk_free_rate_reasonable():
    """Test that risk-free rate is in a reasonable range."""
    assert 0.0 <= settings.RISK_FREE_RATE <= 0.20, \
        f"Risk-free rate {settings.RISK_FREE_RATE} seems unreasonable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
