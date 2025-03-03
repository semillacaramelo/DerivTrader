"""
Unit tests for the MovingAverageStrategy class.
"""
import pytest
import numpy as np
from modules.moving_average import MovingAverageStrategy

def test_ma_calculation():
    strategy = MovingAverageStrategy(short_period=2, medium_period=3, long_period=4)
    
    # Test with simple sequence
    prices = [1.0, 2.0, 3.0, 4.0, 5.0]
    for price in prices:
        strategy.update(price)
    
    ma_values = strategy.update(prices[-1])
    assert ma_values["short_ma"] == pytest.approx(4.5)  # Average of [4, 5]
    assert ma_values["medium_ma"] == pytest.approx(4.0)  # Average of [3, 4, 5]
    assert ma_values["long_ma"] == pytest.approx(3.5)   # Average of [2, 3, 4, 5]

def test_signal_generation():
    strategy = MovingAverageStrategy(short_period=2, medium_period=3, long_period=4)
    
    # Setup for buy signal (short > medium > long)
    prices = [1.0, 2.0, 3.0, 5.0, 8.0]
    for price in prices:
        strategy.update(price)
    
    signal, strength = strategy.generate_signal()
    assert signal == "buy"
    assert 0 <= strength <= 1.0
    
    # Setup for sell signal (short < medium < long)
    prices = [8.0, 5.0, 3.0, 2.0, 1.0]
    strategy.reset()
    for price in prices:
        strategy.update(price)
    
    signal, strength = strategy.generate_signal()
    assert signal == "sell"
    assert 0 <= strength <= 1.0

def test_insufficient_data():
    strategy = MovingAverageStrategy()
    
    # Test with insufficient data
    strategy.update(1.0)
    ma_values = strategy.update(2.0)
    
    assert ma_values["short_ma"] == 0.0
    assert ma_values["medium_ma"] == 0.0
    assert ma_values["long_ma"] == 0.0
    
    signal, strength = strategy.generate_signal()
    assert signal == "hold"
    assert strength == 0.0

def test_signal_strength():
    strategy = MovingAverageStrategy(short_period=2, medium_period=3, long_period=4)
    
    # Large price movement
    prices = [10.0, 10.0, 10.0, 15.0, 20.0]
    for price in prices:
        strategy.update(price)
    
    signal, strength = strategy.generate_signal()
    assert signal == "buy"
    assert strength > 0.5  # Strong signal due to large movement

    # Small price movement
    strategy.reset()
    prices = [10.0, 10.1, 10.2, 10.3, 10.4]
    for price in prices:
        strategy.update(price)
    
    signal, strength = strategy.generate_signal()
    assert signal == "buy"
    assert strength < 0.5  # Weak signal due to small movement