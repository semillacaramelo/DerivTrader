"""
Logging configuration for the Deriv Trading Bot.
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import config

def setup_logger(name: str) -> logging.Logger:
    """
    Set up a logger with both file and console handlers.

    Args:
        name: Name of the logger

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    try:
        # Create logs directory in the project root
        log_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "logs"
        log_dir.mkdir(exist_ok=True)

        # Prevent adding handlers multiple times
        if not logger.handlers:
            # File handler with rotation
            log_file = log_dir / config.LOG_FILE
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=1024 * 1024,  # 1MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
            logger.addHandler(file_handler)

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
            logger.addHandler(console_handler)

    except Exception as e:
        # Fallback to console-only logging if file logging fails
        print(f"Warning: Could not set up file logging: {e}")
        if not logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
            logger.addHandler(console_handler)

    return logger

def log_error_context(logger: logging.Logger, error: Exception, context: dict = None):
    """
    Log an error with additional context information.

    Args:
        logger: Logger instance
        error: The exception to log
        context: Additional context information
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Format the error message
    message = f"Error: {error_type} - {error_msg}"
    
    # Add context if provided
    if context:
        context_str = "\n".join(f"  {k}: {v}" for k, v in context.items())
        message = f"{message}\nContext:\n{context_str}"
    
    logger.error(message, exc_info=True)

# Initialize root logger
root_logger = setup_logger('deriv_bot')
