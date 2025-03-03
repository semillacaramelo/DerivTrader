#!/usr/bin/env python3
"""
Deriv API Connection Test Script

This script tests the API connection module with real credentials to validate
authentication, reconnection logic, and error handling.
"""

import asyncio
import os
import signal
import sys
import time
import re
import logging
from typing import List

from modules.api_connection import DerivAPIConnection
from modules.logger import setup_logger
import config

# Configure logging to handle Unicode characters
def setup_test_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Use simple formatting without Unicode symbols
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    return logger

logger = setup_test_logger('api_test')

# Replace Unicode symbols with ASCII alternatives
STATUS_SYMBOLS = {
    'passed': '[PASS]',
    'failed': '[FAIL]',
    'not_tested': '[SKIP]',
    'testing': '[TEST]'
}

# Global flag to track if we should exit
should_exit = False

def signal_handler(sig, frame):
    """Handle interruption signals for clean shutdown."""
    global should_exit
    logger.info("Test interrupted. Initiating clean shutdown...")
    should_exit = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def validate_environment() -> List[str]:
    """Check if the environment is properly configured for testing."""
    # Verify API tokens are set
    demo_token = os.environ.get("DERIV_API_TOKEN_DEMO", "")
    real_token = os.environ.get("DERIV_API_TOKEN_REAL", "")
    app_id = os.environ.get("APP_ID", "")

    issues = []

    if not demo_token:
        issues.append("DERIV_API_TOKEN_DEMO is not set")
    if not real_token:
        issues.append("DERIV_API_TOKEN_REAL is not set")
    if not app_id:
        issues.append("APP_ID is not set")

    # Verify simulation mode is off for testing
    if config.ENABLE_SIMULATION:
        logger.warning("ENABLE_SIMULATION is set to true, but we'll disable it for this test")

    return issues

import pytest

@pytest.mark.asyncio
async def test_connection(use_demo: bool = True) -> bool:
    """Test the API connection with real credentials."""
    logger.info(f"Testing connection with {'demo' if use_demo else 'real'} account")

    # Explicitly set simulation mode to False for this test
    os.environ["ENABLE_SIMULATION"] = "false"

    # Initialize connection
    api = DerivAPIConnection(use_demo=use_demo)

    # Get token diagnostics without exposing the actual token
    token = config.DERIV_API_TOKEN_DEMO if use_demo else config.DERIV_API_TOKEN_REAL
    logger.info(f"API Token diagnostic: {api.get_token_diagnostic(token)}")

    try:
        # Perform comprehensive connection test
        logger.info("Executing comprehensive API connection test...")
        test_results = await api.test_connection()

        # Log test results in detail
        for test_name, result in test_results.items():
            if test_name != "overall":
                status_symbol = STATUS_SYMBOLS.get(result["status"], '[????]')
                logger.info(f"{status_symbol} {test_name.replace('_', ' ').title()}: {result['details']}")

        # Overall assessment
        if test_results["overall"]["status"] == "passed":
            logger.info("[PASS] ALL TESTS PASSED")
            return True
        elif test_results["overall"]["status"] == "partial":
            logger.warning("[TEST] SOME TESTS PASSED")
            return True
        else:
            logger.error("[FAIL] ALL TESTS FAILED")
            return False

    except Exception as e:
        logger.exception(f"Exception during API testing: {e}")
        return False
    finally:
        # Ensure we're disconnected
        if api.is_connected:
            await api.disconnect()

async def main() -> int:
    """Run a series of tests on the API connection module."""
    logger.info("Starting Deriv API connection tests")

    # Check environment configuration
    env_issues = validate_environment()
    if env_issues:
        logger.error("Environment configuration issues detected:")
        for issue in env_issues:
            logger.error(f"- {issue}")
        logger.error("Please fix these issues before running the tests")
        return 1

    # Test with demo account first
    logger.info("=== TESTING DEMO ACCOUNT ===")
    demo_success = await test_connection(use_demo=True)

    if demo_success:
        logger.info("[PASS] Demo account tests PASSED")
    else:
        logger.error("[FAIL] Demo account tests FAILED")

    # Test with real account if demo was successful
    real_success = False
    if demo_success:
        logger.info("\n=== TESTING REAL ACCOUNT ===")
        real_success = await test_connection(use_demo=False)

        if real_success:
            logger.info("[PASS] Real account tests PASSED")
        else:
            logger.error("[FAIL] Real account tests FAILED")

    # Overall assessment
    logger.info("\n=== TEST SUMMARY ===")
    if demo_success:
        logger.info("Demo account: [PASS] PASSED")
    else:
        logger.info("Demo account: [FAIL] FAILED")

    if demo_success and real_success:
        logger.info("Real account: [PASS] PASSED")
        logger.info("\nOverall status: [PASS] ALL TESTS PASSED")
        return 0
    elif not demo_success:
        logger.info("Real account: [SKIP] NOT TESTED (Demo tests failed)")
        logger.info("\nOverall status: [FAIL] TESTS FAILED")
        return 1
    else:
        logger.info("Real account: [FAIL] FAILED")
        logger.info("\nOverall status: [TEST] PARTIAL SUCCESS")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Tests terminated by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error during tests: {e}")
        sys.exit(1)
