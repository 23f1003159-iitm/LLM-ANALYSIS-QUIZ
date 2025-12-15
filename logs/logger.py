"""Professional logging system with session-based logs.

Provides both file and console logging with formatted output,
session tracking, and color-coded terminal display.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color coding for terminal output."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        """Format log record with colors for terminal."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{self.BOLD}{levelname}{self.RESET}"

        # Format the message
        formatted = super().format(record)

        return formatted


def setup_logger(name: str = "quiz_solver", log_file: str = "logs/app.log") -> logging.Logger:
    """Set up logger with file and console handlers.

    Creates a session-based log file with timestamp and configures
    both file and console output with appropriate formatting.

    Args:
        name: Logger name (default: "quiz_solver").
        log_file: Path to log file (default: "logs/app.log").

    Returns:
        logging.Logger: Configured logger instance.

    Example:
        >>> logger = setup_logger()
        >>> logger.info("Starting quiz solver")
        2024-01-15 10:30:45 - INFO - Starting quiz solver
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Session separator with timestamp
    session_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session_separator = f"\n{'=' * 80}\nSESSION STARTED: {session_time}\n{'=' * 80}\n"

    # Write session separator to file
    with open(log_file, "a") as f:
        f.write(session_separator)

    # File handler - detailed logs
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # Console handler - cleaner output with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Global logger instance
logger = setup_logger()


def get_logger(name: str = None) -> logging.Logger:
    """Get logger instance.

    Args:
        name: Optional logger name (returns main logger if None).

    Returns:
        logging.Logger: Logger instance.
    """
    if name:
        return logging.getLogger(f"quiz_solver.{name}")
    return logger
