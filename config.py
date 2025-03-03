"""
Configuration module for the Deriv Trading Bot.

This module handles loading environment variables and provides configuration
settings for the application.
"""
import os
import logging
from decimal import Decimal
from typing import Dict, Any, Union, Optional
from dotenv import load_dotenv
load_dotenv()

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('config')

def get_env_var(key: str, default: Any = None, var_type: type = str) -> Any:
    """Safe environment variable getter with type conversion and logging."""
    # Try multiple possible environment variable names
    for possible_key in [key, key.upper(), key.lower()]:
        value = os.getenv(possible_key)
        if value is not None:
            logger.debug(f"Found environment variable {possible_key}")
            try:
                # Strip any whitespace and comments
                value = value.split('#')[0].strip()
                if var_type == bool:
                    return value.lower() == 'true'
                return var_type(value)
            except (ValueError, TypeError) as e:
                logger.debug(f"Error converting {possible_key}={value}: {e}")
                continue

    logger.debug(f"Using default value for {key}: {default}")
    return default

# First try to get the direct API token
DERIV_API_TOKEN = get_env_var("DERIV_API_TOKEN", "")
APP_ID = get_env_var("DERIV_APP_ID", "1089")

# Account Settings
DEFAULT_ACCOUNT_TYPE = get_env_var("DERIV_ACCOUNT_TYPE", "demo").lower()
ENABLE_SIMULATION = get_env_var("ENABLE_SIMULATION", "true", bool)

# Trading Parameters
TRADING_SYMBOL = get_env_var("TRADING_SYMBOL", "R_100")
STAKE_AMOUNT = get_env_var("STAKE_AMOUNT", 10.0, float)
MAX_CONCURRENT_TRADES = get_env_var("MAX_CONCURRENT_TRADES", 1, int)

# Strategy Parameters
SHORT_MA_PERIOD = get_env_var("SHORT_MA_PERIOD", 5, int)
MEDIUM_MA_PERIOD = get_env_var("MEDIUM_MA_PERIOD", 10, int)
LONG_MA_PERIOD = get_env_var("LONG_MA_PERIOD", 20, int)
SIGNAL_THRESHOLD = get_env_var("SIGNAL_THRESHOLD", 0.5, float)

# Risk Management
MAX_DAILY_LOSS = get_env_var("MAX_DAILY_LOSS", 100.0, float)
MAX_DAILY_TRADES = get_env_var("MAX_DAILY_TRADES", 50, int)

# Logging Configuration
LOG_LEVEL = get_env_var("LOG_LEVEL", "INFO").upper()
LOG_FILE = get_env_var("LOG_FILE", "deriv_bot.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# API Endpoints - Using official Deriv endpoint
DERIV_WSS_ENDPOINTS = [
    "wss://ws.derivapi.com/websockets/v3",  # Primary endpoint
    "wss://ws.binaryws.com/websockets/v3",  # Backup endpoint
]
DERIV_WSS_ENDPOINT = get_env_var("DERIV_WSS_ENDPOINT", DERIV_WSS_ENDPOINTS[0])
DERIV_DEMO_WSS_ENDPOINT = get_env_var("DERIV_DEMO_WSS_ENDPOINT", DERIV_WSS_ENDPOINT)

# Connection Settings
CONNECTION_TIMEOUT = 20
RECONNECT_DELAY = 1
MAX_RECONNECT_ATTEMPTS = 5
PING_INTERVAL = 20
PING_TIMEOUT = 10
MAX_MESSAGE_SIZE = 2**20

# WebSocket Settings
WS_HEADERS = {
    "Origin": "https://deriv.app",
    "User-Agent": "DerivBot/1.0"
}
WS_PROTOCOLS = ["binary-v3"]  # Protocol used by Deriv WebSocket API

# Validate and log configuration
if not ENABLE_SIMULATION and DEFAULT_ACCOUNT_TYPE == "demo":
    print(f"DERIV_API_TOKEN_DEMO: {get_env_var('DERIV_API_TOKEN_DEMO')}")
    if not get_env_var("DERIV_API_TOKEN_DEMO"):
        raise ValueError("No API token found for demo account. Set DERIV_API_TOKEN_DEMO environment variable.")
elif not ENABLE_SIMULATION and DEFAULT_ACCOUNT_TYPE != "demo":
    if not get_env_var("DERIV_API_TOKEN_REAL"):
        raise ValueError("No API token found for real account. Set DERIV_API_TOKEN_REAL environment variable.")

logger.info(f"Configuration loaded - Account type: {DEFAULT_ACCOUNT_TYPE}, Simulation mode: {ENABLE_SIMULATION}")
logger.info(f"Trading parameters - Symbol: {TRADING_SYMBOL}, Stake: {STAKE_AMOUNT}")
