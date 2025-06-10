import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """
    Configure the NovaPipe logger.
    - level: root log level (e.g., DEBUG, INFO, WARNING, ERROR)
    """
    logger = logging.getLogger("novapipe")
    logger.setLevel(level.upper())

    # If handlers are already configured, skip
    if logger.hasHandlers():
        return

    # Create console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level.upper())

    # Formatter: time, level, logger name, and message
    fmt = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)
    ch.setFormatter(formatter)

    logger.addHandler(ch)
