"""
Unit tests for the DerivTrader class.
"""
import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from modules.trader import DerivTrader
from modules.api_connection import DerivAPIConnection

@pytest.fixture
def mock_api():
    api = Mock(spec=DerivAPIConnection)
    api.send_request = Mock()
    api.subscribe = Mock()
    return api

@pytest.fixture
def trader(mock_api):
    return DerivTrader(mock_api, symbol="R_100", stake_amount=10.0)

async def test_subscribe_to_ticks(trader, mock_api):
    mock_api.subscribe.return_value = "test_subscription_id"
    subscription_id = await trader.subscribe_to_ticks()
    
    assert subscription_id == "test_subscription_id"
    mock_api.subscribe.assert_called_once()
    assert mock_api.subscribe.call_args[0][0]["ticks"] == "R_100"

async def test_handle_tick_signal_generation(trader):
    # Mock tick data
    tick_data = {
        "tick": {
            "quote": "100.50",
            "symbol": "R_100"
        }
    }
    
    # Should not trade initially due to insufficient data
    await trader._handle_tick(tick_data)
    assert trader.active_contract is None

    # Feed more ticks to generate signals
    for price in [101.0, 102.0, 103.0, 104.0]:
        await trader._handle_tick({"tick": {"quote": str(price)}})

async def test_execute_trade(trader, mock_api):
    # Mock successful proposal response
    mock_api.send_request.return_value = {
        "proposal": {
            "id": "test_proposal",
            "ask_price": "10.50"
        }
    }
    
    # Execute a buy trade
    await trader._execute_trade("buy", Decimal("100.50"))
    
    # Verify proposal request
    proposal_call = mock_api.send_request.call_args_list[0]
    assert proposal_call[0][0]["contract_type"] == "CALL"
    assert proposal_call[0][0]["amount"] == 10.0

async def test_handle_contract_update(trader):
    # Test contract completion
    contract_update = {
        "proposal_open_contract": {
            "contract_id": "test_contract",
            "is_sold": True,
            "profit": "5.25"
        }
    }
    
    trader.active_contract = {"contract_id": "test_contract"}
    await trader._handle_contract_update(contract_update)
    assert trader.active_contract is None  # Contract should be cleared

async def test_error_handling(trader, mock_api):
    # Test proposal error
    mock_api.send_request.return_value = {
        "error": {
            "message": "Test error"
        }
    }
    
    await trader._execute_trade("buy", Decimal("100.50"))
    assert trader.active_contract is None  # No trade should be executed

async def test_risk_management(trader, mock_api):
    # Mock active contract to test concurrent trade limit
    trader.active_contract = {"contract_id": "existing_contract"}
    await trader._execute_trade("buy", Decimal("100.50"))
    
    # Should not execute new trade while one is active
    mock_api.send_request.assert_not_called()