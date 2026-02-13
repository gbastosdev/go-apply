import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    """
    Configure and return a logger with console output

    Args:
        name: Logger name (typically __name__ of calling module)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    # Format: timestamp - logger name - level - message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger
