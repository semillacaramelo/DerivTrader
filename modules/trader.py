"""
Trading Module for Deriv Bot.

This module handles trade execution and management based on strategy signals.
"""
import asyncio
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, date

from modules.api_connection import DerivAPIConnection
from modules.logger import setup_logger
from modules.moving_average import MovingAverageStrategy
from utils.helpers import (
    calculate_daily_stats,
    check_risk_limits,
    calculate_optimal_stake,
    validate_trade_parameters,
    extract_error_message
)
import config

logger = setup_logger('trader')

class DerivTrader:
    def __init__(self, 
                 api: DerivAPIConnection, 
                 symbol: str = config.TRADING_SYMBOL, 
                 stake_amount: float = config.STAKE_AMOUNT):
        """Initialize the trader."""
        self.api = api
        self.symbol = symbol
        self.stake_amount = stake_amount
        self.strategy = MovingAverageStrategy(
            short_period=config.SHORT_MA_PERIOD,
            medium_period=config.MEDIUM_MA_PERIOD,
            long_period=config.LONG_MA_PERIOD
        )
        self.active_contract = None
        self.daily_trades: List[Dict[str, Any]] = []
        self.last_trade_date = date.today()
        self.running = False
        self.account_balance: Optional[Decimal] = None

    async def subscribe_to_ticks(self) -> Optional[str]:
        """Subscribe to price updates for the symbol."""
        return await self.api.subscribe({
            "ticks": self.symbol
        }, self._handle_tick)

    async def _handle_tick(self, response: Dict[str, Any]):
        """Handle incoming tick data."""
        if "tick" not in response:
            return
        
        # Reset daily stats if it's a new day
        current_date = date.today()
        if current_date != self.last_trade_date:
            self.daily_trades = []
            self.last_trade_date = current_date
        
        # Check risk limits before processing tick
        daily_stats = calculate_daily_stats(self.daily_trades)
        if not check_risk_limits(daily_stats):
            logger.warning("Risk limits reached, stopping trading for today")
            self.running = False
            return
        
        tick = response["tick"]
        price = Decimal(str(tick["quote"]))
        
        # Update strategy with new price
        self.strategy.update(float(price))
        signal, strength = self.strategy.generate_signal()
        
        # Execute trades based on signals if strength meets threshold
        if signal != "hold" and strength >= config.SIGNAL_THRESHOLD:
            await self._execute_trade(signal, price)

    async def _execute_trade(self, signal: str, price: Decimal):
        """Execute a trade based on the signal."""
        if self.active_contract:
            logger.info("Skipping signal - active contract exists")
            return

        if len(self.daily_trades) >= config.MAX_DAILY_TRADES:
            logger.warning("Maximum daily trades reached")
            return

        contract_type = "CALL" if signal == "buy" else "PUT"
        duration = 1  # 1 minute trades
        
        # Calculate optimal stake based on account balance
        if self.account_balance:
            stake = calculate_optimal_stake(self.account_balance)
        else:
            stake = Decimal(str(self.stake_amount))

        # Validate trade parameters
        if not validate_trade_parameters(contract_type, duration, stake):
            logger.error("Invalid trade parameters")
            return
        
        # Request contract proposal
        proposal = await self.api.send_request({
            "proposal": 1,
            "amount": float(stake),
            "basis": "stake",
            "contract_type": contract_type,
            "currency": "USD",
            "duration": duration,
            "duration_unit": "m",
            "symbol": self.symbol
        })

        if "error" in proposal:
            error_msg = extract_error_message(proposal)
            logger.error(f"Proposal error: {error_msg}")
            return

        # Buy the contract
        buy_response = await self.api.send_request({
            "buy": proposal["proposal"]["id"],
            "price": proposal["proposal"]["ask_price"]
        })

        if "error" in buy_response:
            error_msg = extract_error_message(buy_response)
            logger.error(f"Buy error: {error_msg}")
            return

        logger.info(f"Executed {contract_type} trade at {price} with stake {stake}")
        self.active_contract = buy_response["buy"]
        
        # Set up contract monitoring
        asyncio.create_task(self._monitor_contract(self.active_contract["contract_id"]))

    async def _monitor_contract(self, contract_id: str):
        """Monitor an active contract until completion."""
        subscription = await self.api.subscribe({
            "proposal_open_contract": 1,
            "contract_id": contract_id
        }, self._handle_contract_update)

        if not subscription:
            logger.error("Failed to subscribe to contract updates")
            # Reset active contract if we can't monitor it
            self.active_contract = None

    async def _handle_contract_update(self, response: Dict[str, Any]):
        """Handle contract status updates."""
        if "proposal_open_contract" not in response:
            return

        contract = response["proposal_open_contract"]
        
        if contract["is_sold"]:
            profit = Decimal(str(contract["profit"]))
            logger.info(f"Contract completed. Profit: {profit}")
            
            # Update daily trades list
            self.daily_trades.append({
                "contract_id": contract["contract_id"],
                "profit": profit,
                "timestamp": datetime.now(),
                "symbol": contract.get("symbol"),
                "entry_spot": contract.get("entry_spot"),
                "exit_spot": contract.get("exit_spot")
            })
            
            # Update account balance
            self.account_balance = Decimal(str(contract["balance_after"]))
            
            self.active_contract = None
            
            # Log daily statistics
            daily_stats = calculate_daily_stats(self.daily_trades)
            logger.info(f"Daily stats: Win rate: {daily_stats['win_rate']:.1f}%, "
                       f"Total profit: {daily_stats['total_profit']}, "
                       f"Trades: {daily_stats['total_trades']}")

    async def _handle_error(self, response: Dict[str, Any]):
        """Handle error response from the API."""
        error_msg = extract_error_message(response)
        logger.error(f"API error: {error_msg}")
        return None

    async def _update_account_balance(self):
        """Update the account balance."""
        response = await self.api.get_account_info()
        if response and "authorize" in response:
            self.account_balance = Decimal(str(response["authorize"]["balance"]))
            logger.info(f"Account balance updated: {self.account_balance}")
        else:
            logger.warning("Failed to update account balance")

    async def start(self):
        """Start the trading bot."""
        self.running = True
        logger.info(f"Starting trader for {self.symbol}")
        
        # Get initial account balance
        await self._update_account_balance()
        
        await self.subscribe_to_ticks()
        logger.info(f"Bot started - Trading {self.symbol} with initial stake {self.stake_amount}")

    async def stop(self):
        """Stop the trading bot."""
        self.running = False
        logger.info("Stopping trader")