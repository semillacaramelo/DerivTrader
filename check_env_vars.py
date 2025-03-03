#!/usr/bin/env python3
"""
Utility script to check environment variables and their values.
"""
import os

def check_env_vars():
    env_vars = [
        "DERIV_APP_ID",
        "DERIV_API_TOKEN_DEMO",
        "DERIV_API_TOKEN_REAL",
        "DEFAULT_ACCOUNT_TYPE",
        "ENABLE_SIMULATION",
        "TRADING_SYMBOL",
        "STAKE_AMOUNT",
        "MAX_CONCURRENT_TRADES",
        "SHORT_MA_PERIOD",
        "MEDIUM_MA_PERIOD",
        "LONG_MA_PERIOD",
        "SIGNAL_THRESHOLD",
        "MAX_DAILY_LOSS",
        "MAX_DAILY_TRADES",
        "LOG_LEVEL",
        "LOG_FILE"
    ]

    print("Environment Variables Check:")
    print("-" * 50)
    for var in env_vars:
        value = os.getenv(var)
        print(f"{var}: '{value}'")
        if value and '#' in value:
            print(f"WARNING: Variable {var} contains a comment character '#'")

if __name__ == "__main__":
    check_env_vars()
