"""
Logger configuration module for Switchwise application
"""
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_logger(name: str) -> logging.Logger:
    """
    Create and return a logger with the given name.
    
    Args:
        name: Name for the logger, typically __name__
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Set log level from environment or default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level))
    
    # Create console handler if not already added
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
    
    return logger