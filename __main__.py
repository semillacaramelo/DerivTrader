#!/usr/bin/env python3
"""
Main entry point for the Deriv Trading Bot.
"""
import asyncio
import signal
from modules.api_connection import DerivAPIConnection
from modules.trader import DerivTrader
from modules.logger import setup_logger
import config

logger = setup_logger('main')

async def main():
    """Main function to run the trading bot."""
    # Initialize API connection
    api = DerivAPIConnection(use_demo=config.DEFAULT_ACCOUNT_TYPE == "demo")

    # Initialize trader
    trader = DerivTrader(
        api=api,
        symbol=config.TRADING_SYMBOL,
        stake_amount=config.STAKE_AMOUNT
    )

    # Set up signal handlers for graceful shutdown
    def handle_shutdown(signum, frame):
        logger.info("Shutdown signal received")
        asyncio.create_task(shutdown(trader))

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        logger.info("Connecting to Deriv API...")
        if not await api.connect():
            logger.error("Failed to connect to Deriv API")
            return

        # Start the trading bot
        await trader.start()

        # Keep the bot running
        while trader.running:
            await asyncio.sleep(1)

    except Exception as e:
        logger.exception(f"Error in main loop: {e}")
    finally:
        await shutdown(trader)

async def shutdown(trader: DerivTrader):
    """Gracefully shutdown the bot."""
    await trader.stop()
    logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())