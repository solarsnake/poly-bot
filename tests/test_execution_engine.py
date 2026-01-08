"""
Unit tests for execution engine calculations (no IBKR connection required).
"""
import pytest
from unittest.mock import Mock, AsyncMock
from src.execution.forecastex_execution import ExecutionEngine
from src.execution.ibkr_client import IBKRClient
from src.execution.forecastex_contracts import ForecastExContractFactory
from src.storage.ledger import TradeLedger
import tempfile
import os


@pytest.fixture
def mock_components():
    """Create mock components for testing."""
    ibkr_client = Mock(spec=IBKRClient)
    ibkr_client._connected = True

    contract_factory = Mock(spec=ForecastExContractFactory)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_trades.db")
        csv_path = os.path.join(tmpdir, "test_trades.csv")
        ledger = TradeLedger(db_path=db_path, csv_path=csv_path)

        yield ibkr_client, contract_factory, ledger


def test_execution_engine_initialization(mock_components):
    """Test ExecutionEngine initialization."""
    ibkr_client, contract_factory, ledger = mock_components

    engine = ExecutionEngine(
        ibkr_client=ibkr_client,
        contract_factory=contract_factory,
        ledger=ledger,
        mode="paper",
        arb_threshold=0.02
    )

    assert engine.mode == "paper"
    assert engine.arb_threshold == 0.02
    assert engine.risk_free_rate == 0.045  # default


def test_execution_engine_live_mode_safety(mock_components):
    """Test that live mode requires settings permission."""
    ibkr_client, contract_factory, ledger = mock_components

    # This should work (assuming ALLOW_US_EXECUTION is True in settings)
    from src.signal_server.config import settings
    if settings.ALLOW_US_EXECUTION:
        engine = ExecutionEngine(
            ibkr_client=ibkr_client,
            contract_factory=contract_factory,
            ledger=ledger,
            mode="live",
            arb_threshold=0.02
        )
        assert engine.mode == "live"


def test_invalid_mode_raises_error(mock_components):
    """Test that invalid mode raises ValueError."""
    ibkr_client, contract_factory, ledger = mock_components

    with pytest.raises(ValueError, match="Invalid mode"):
        ExecutionEngine(
            ibkr_client=ibkr_client,
            contract_factory=contract_factory,
            ledger=ledger,
            mode="invalid_mode"
        )


def test_yield_adjusted_fair_value_calculation(mock_components):
    """Test yield-adjusted fair value calculation."""
    ibkr_client, contract_factory, ledger = mock_components

    engine = ExecutionEngine(
        ibkr_client=ibkr_client,
        contract_factory=contract_factory,
        ledger=ledger,
        mode="paper",
        risk_free_rate=0.045
    )

    # Test case 1: 45 days to expiry, 48% probability
    p_poly = 0.48
    days_to_expiry = 45
    p_fx_fair = engine.calculate_yield_adjusted_fair_value(p_poly, days_to_expiry)

    # Expected: 0.48 * (1 + 0.045 * 45/365) = 0.48 * 1.00554 ≈ 0.48266
    expected = 0.48 * (1 + 0.045 * 45 / 365)
    assert abs(p_fx_fair - expected) < 0.0001

    # Test case 2: Zero days to expiry
    p_fx_fair_zero = engine.calculate_yield_adjusted_fair_value(p_poly, 0)
    assert abs(p_fx_fair_zero - p_poly) < 0.0001

    # Test case 3: One year to expiry
    p_fx_fair_year = engine.calculate_yield_adjusted_fair_value(p_poly, 365)
    expected_year = 0.48 * (1 + 0.045)
    assert abs(p_fx_fair_year - expected_year) < 0.0001


def test_yield_adjustment_caps_at_one(mock_components):
    """Test that yield adjustment caps at 1.0 (100%)."""
    ibkr_client, contract_factory, ledger = mock_components

    engine = ExecutionEngine(
        ibkr_client=ibkr_client,
        contract_factory=contract_factory,
        ledger=ledger,
        mode="paper",
        risk_free_rate=0.10  # High rate for testing
    )

    # Very high probability with long time to expiry
    p_poly = 0.95
    days_to_expiry = 365

    p_fx_fair = engine.calculate_yield_adjusted_fair_value(p_poly, days_to_expiry)

    # Should be capped at 1.0
    assert p_fx_fair <= 1.0


def test_arb_spread_calculation(mock_components):
    """Test arbitrage spread calculation."""
    ibkr_client, contract_factory, ledger = mock_components

    engine = ExecutionEngine(
        ibkr_client=ibkr_client,
        contract_factory=contract_factory,
        ledger=ledger,
        mode="paper",
        risk_free_rate=0.045
    )

    # Polymarket at 48%, ForecastEx at 46.5%, 45 days to expiry
    p_poly = 0.48
    p_fx_market = 0.465
    days_to_expiry = 45

    arb_spread = engine.calculate_arb_spread(p_poly, p_fx_market, days_to_expiry)

    # Expected: (0.48 * 1.00554) - 0.465 ≈ 0.01766
    expected_fair = 0.48 * (1 + 0.045 * 45 / 365)
    expected_spread = expected_fair - p_fx_market

    assert abs(arb_spread - expected_spread) < 0.0001


def test_arb_spread_positive_opportunity(mock_components):
    """Test detecting positive arb opportunity (buy ForecastEx)."""
    ibkr_client, contract_factory, ledger = mock_components

    engine = ExecutionEngine(
        ibkr_client=ibkr_client,
        contract_factory=contract_factory,
        ledger=ledger,
        mode="paper",
        arb_threshold=0.02
    )

    # Setup: Polymarket higher than ForecastEx
    p_poly = 0.50
    p_fx_market = 0.47  # 3% below
    days_to_expiry = 45

    arb_spread = engine.calculate_arb_spread(p_poly, p_fx_market, days_to_expiry)

    # Should be positive (buy opportunity on FX)
    assert arb_spread > 0
    assert arb_spread > engine.arb_threshold


def test_arb_spread_negative_no_opportunity(mock_components):
    """Test detecting no arb opportunity."""
    ibkr_client, contract_factory, ledger = mock_components

    engine = ExecutionEngine(
        ibkr_client=ibkr_client,
        contract_factory=contract_factory,
        ledger=ledger,
        mode="paper",
        arb_threshold=0.02
    )

    # Setup: ForecastEx higher than yield-adjusted Polymarket
    p_poly = 0.48
    p_fx_market = 0.50  # Above fair value
    days_to_expiry = 45

    arb_spread = engine.calculate_arb_spread(p_poly, p_fx_market, days_to_expiry)

    # Should be negative (no buy opportunity)
    assert arb_spread < 0


def test_arb_spread_with_different_rates(mock_components):
    """Test arb spread calculation with different risk-free rates."""
    ibkr_client, contract_factory, ledger = mock_components

    # Test with multiple rates
    for rate in [0.0, 0.03, 0.05, 0.10]:
        engine = ExecutionEngine(
            ibkr_client=ibkr_client,
            contract_factory=contract_factory,
            ledger=ledger,
            mode="paper",
            risk_free_rate=rate
        )

        p_poly = 0.50
        p_fx_market = 0.50
        days_to_expiry = 365

        arb_spread = engine.calculate_arb_spread(p_poly, p_fx_market, days_to_expiry)

        # With positive rates and time, fair value should be higher
        if rate > 0:
            assert arb_spread > 0
        else:
            assert abs(arb_spread) < 0.0001  # ~0 with 0% rate


def test_negative_days_to_expiry_handled(mock_components):
    """Test that negative days to expiry are handled gracefully."""
    ibkr_client, contract_factory, ledger = mock_components

    engine = ExecutionEngine(
        ibkr_client=ibkr_client,
        contract_factory=contract_factory,
        ledger=ledger,
        mode="paper"
    )

    # Negative days (expired contract)
    p_poly = 0.50
    days_to_expiry = -10

    # Should not crash, should treat as 0 days
    p_fx_fair = engine.calculate_yield_adjusted_fair_value(p_poly, days_to_expiry)
    assert abs(p_fx_fair - p_poly) < 0.0001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
