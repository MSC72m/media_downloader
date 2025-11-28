"""Utility functions for logging."""

import logging
import sys

# Global flag to track if root logger is configured
_root_logger_configured = False


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.
    
    Configures root logger once to prevent duplicate log messages.
    """
    global _root_logger_configured
    
    # Configure root logger only once
    if not _root_logger_configured:
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)
            root_logger.setLevel(logging.INFO)
        _root_logger_configured = True
    
    # Return named logger (will inherit from root)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    return logger
