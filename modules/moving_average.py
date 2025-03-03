"""
Moving Average Strategy Module.
"""
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger('strategy')

class MovingAverageStrategy:
    def __init__(self, short_period: int = 5, medium_period: int = 10, long_period: int = 20):
        """Initialize the 3 MA strategy."""
        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period
        self.prices: List[float] = []
        logger.info(f"Strategy initialized with periods: {short_period}/{medium_period}/{long_period}")

    def calculate_ma(self, period: int) -> Optional[float]:
        """Calculate moving average for the given period."""
        if len(self.prices) < period:
            logger.debug(f"Insufficient data for {period} period MA. Need {period}, have {len(self.prices)}")
            return None
            
        ma_value = np.mean(self.prices[-period:])
        logger.debug(f"{period} period MA: {ma_value:.5f}")
        return ma_value

    def update(self, price: float) -> Dict[str, float]:
        """Update strategy with new price data."""
        self.prices.append(price)
        logger.debug(f"New price: {price:.5f}, Total prices: {len(self.prices)}")
        
        ma_short = self.calculate_ma(self.short_period)
        ma_medium = self.calculate_ma(self.medium_period)
        ma_long = self.calculate_ma(self.long_period)

        return {
            "short_ma": ma_short if ma_short is not None else 0.0,
            "medium_ma": ma_medium if ma_medium is not None else 0.0,
            "long_ma": ma_long if ma_long is not None else 0.0
        }

    def generate_signal(self) -> Tuple[str, float]:
        """Generate trading signal based on MA crossovers."""
        if len(self.prices) < self.long_period:
            logger.debug(f"Waiting for more data. Have {len(self.prices)}/{self.long_period} required prices")
            return "hold", 0.0

        ma_values = self.update(self.prices[-1])
        short_ma = ma_values["short_ma"]
        medium_ma = ma_values["medium_ma"]
        long_ma = ma_values["long_ma"]

        # Calculate signal strength based on MA differences
        strength = min(abs(short_ma - long_ma) / long_ma, 1.0) if long_ma > 0 else 0.0
        logger.debug(f"MAs - Short: {short_ma:.5f}, Medium: {medium_ma:.5f}, Long: {long_ma:.5f}, Strength: {strength:.5f}")

        # Generate signal based on MA crossovers
        if short_ma > medium_ma > long_ma:
            logger.info(f"BUY signal generated with strength {strength:.5f}")
            return "buy", strength
        elif short_ma < medium_ma < long_ma:
            logger.info(f"SELL signal generated with strength {strength:.5f}")
            return "sell", strength
        
        logger.debug("No signal - MAs not aligned for trade")
        return "hold", 0.0

    def reset(self):
        """Reset the strategy data."""
        self.prices = []
        logger.info("Strategy data reset")