"""
Helper functions for Deriv Trading Bot.
"""
import time
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal
import config

def format_currency(amount: Union[float, int, Decimal], currency: str = 'USD') -> str:
    """Format currency amount with symbol."""
    return f"{currency} {amount:.2f}"

def calculate_time_diff(timestamp1: float, timestamp2: Optional[float] = None) -> str:
    """Calculate human-readable time difference."""
    if timestamp2 is None:
        timestamp2 = time.time()
    diff = abs(timestamp2 - timestamp1)
    if diff < 60:
        return f"{diff:.1f} seconds"
    elif diff < 3600:
        return f"{diff/60:.1f} minutes"
    else:
        return f"{diff/3600:.1f} hours"

def extract_error_message(response: Dict[str, Any]) -> Optional[str]:
    """Extract error message from API response."""
    if isinstance(response, dict):
        error = response.get('error', {})
        if isinstance(error, dict):
            return error.get('message')
    return None

def handle_api_error(error_code: str, error_message: str) -> str:
    """
    Handle specific Deriv API error codes and provide actionable messages.
    
    Args:
        error_code: The API error code
        error_message: The original error message

    Returns:
        str: A user-friendly error message with suggested actions
    """
    error_handlers = {
        'AuthorizationRequired': 'API token authorization required. Please check your token.',
        'InvalidToken': 'Invalid API token. Please check your token or generate a new one.',
        'InputValidationFailed': 'Invalid request parameters. Please check your input values.',
        'MarketIsClosed': 'The market is currently closed. Please try again during market hours.',
        'RateLimit': 'Request limit reached. Please wait before sending more requests.',
        'ContractBuyValidationError': 'Unable to purchase contract. Please check trade parameters.',
        'BalanceError': 'Insufficient balance for the requested trade.',
        'MarketNotOpen': 'This market is not currently open for trading.',
        'SymbolValidationError': 'Invalid trading symbol specified.',
    }

    # Return specific handling message if available, otherwise return original message
    return error_handlers.get(error_code, error_message)

def calculate_daily_stats(trades: List[Dict[str, Any]]) -> Dict[str, Union[int, float]]:
    """
    Calculate daily trading statistics.

    Args:
        trades: List of completed trades for the day

    Returns:
        Dict with statistics including:
        - total_trades: Number of trades
        - win_count: Number of winning trades
        - loss_count: Number of losing trades
        - total_profit: Total profit/loss
        - win_rate: Win rate percentage
    """
    stats = {
        "total_trades": len(trades),
        "win_count": 0,
        "loss_count": 0,
        "total_profit": Decimal('0.0'),
        "win_rate": 0.0
    }

    for trade in trades:
        profit = Decimal(str(trade.get('profit', '0')))
        if profit > 0:
            stats["win_count"] += 1
        elif profit < 0:
            stats["loss_count"] += 1
        stats["total_profit"] += profit

    if stats["total_trades"] > 0:
        stats["win_rate"] = (stats["win_count"] / stats["total_trades"]) * 100

    return stats

def check_risk_limits(daily_stats: Dict[str, Union[int, float]]) -> bool:
    """
    Check if trading should continue based on risk management rules.

    Args:
        daily_stats: Dictionary with daily trading statistics

    Returns:
        bool: True if trading can continue, False if limits exceeded
    """
    # Check maximum daily loss
    if daily_stats["total_profit"] < -config.MAX_DAILY_LOSS:
        return False

    # Check maximum number of trades
    if daily_stats["total_trades"] >= config.MAX_DAILY_TRADES:
        return False

    return True

def calculate_optimal_stake(account_balance: Decimal, risk_percentage: float = 1.0) -> Decimal:
    """
    Calculate optimal stake amount based on account balance and risk percentage.

    Args:
        account_balance: Current account balance
        risk_percentage: Percentage of balance to risk (default: 1%)

    Returns:
        Decimal: Optimal stake amount
    """
    max_stake = account_balance * Decimal(str(risk_percentage / 100))
    # Round down to nearest 0.1
    optimal_stake = Decimal(str(float(max_stake) // 0.1 * 0.1))
    return max(min(optimal_stake, config.STAKE_AMOUNT), Decimal('1.0'))

def validate_trade_parameters(contract_type: str, duration: int, amount: Union[float, Decimal]) -> bool:
    """
    Validate trade parameters before execution.

    Args:
        contract_type: Type of contract (e.g., 'CALL' or 'PUT')
        duration: Trade duration in minutes
        amount: Stake amount

    Returns:
        bool: True if parameters are valid
    """
    valid_types = ['CALL', 'PUT']
    if contract_type not in valid_types:
        return False
    
    if duration <= 0:
        return False

    if amount <= 0:
        return False

    return True