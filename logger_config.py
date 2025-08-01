import logging
import os

def setup_logging():
    """
    Configures the root logger for the application.
    """
    # Check for DEBUG environment variable. Default to 'False'.
    debug_mode = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    log_level = logging.DEBUG if debug_mode else logging.INFO

    # Create a custom formatter
    formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a handler to write to standard output (console)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # Add the handler to the root logger
    logger.addHandler(stream_handler)

    # Add a special logger for this setup process if needed
    setup_logger = logging.getLogger(__name__)
    setup_logger.info(f"Logging configured. Level: {'DEBUG' if debug_mode else 'INFO'}.")

# Call the setup function when this module is imported
setup_logging()
