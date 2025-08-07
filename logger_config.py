import logging
import os
from logging.handlers import RotatingFileHandler

# --- Basic Configuration ---
LOG_LEVEL = logging.INFO
LOG_FORMAT = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Get the root logger
root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)

# --- Console Handler (for standard output) ---
# This handler prints logs to the console.
console_handler = logging.StreamHandler()
console_handler.setFormatter(LOG_FORMAT)
root_logger.addHandler(console_handler)

# --- Debug File Handler (only active if DEBUG=true) ---
# This handler writes all logs (from DEBUG level up) to 'anonymizer.log'
# if the DEBUG environment variable is set to "true".

DEBUG_MODE = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

if DEBUG_MODE:
    # If in debug mode, set the root logger level to DEBUG to capture everything.
    root_logger.setLevel(logging.DEBUG)

    # Create a file handler that logs even debug messages.
    # The log file will be in the project's root directory.
    log_file_path = 'anonymizer.log'

    # Use RotatingFileHandler to prevent the log file from growing indefinitely.
    # Max size: 5MB, keep 3 backup files.
    debug_file_handler = RotatingFileHandler(
        log_file_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    debug_file_handler.setFormatter(LOG_FORMAT)
    debug_file_handler.setLevel(logging.DEBUG)

    # Add the handler to the root logger
    root_logger.addHandler(debug_file_handler)

    root_logger.info("DEBUG mode is active. Logging all levels to %s", log_file_path)
else:
    root_logger.info("Running in standard mode. Logging INFO and above to console.")

# --- Example Usage (for testing the configuration) ---
# If you run this file directly, it will demonstrate the logging setup.
if __name__ == '__main__':
    logging.debug("This is a debug message. It will only appear in the file if DEBUG=true.")
    logging.info("This is an info message. It will always appear in the console.")
    logging.warning("This is a warning message.")
    logging.error("This is an error message.")
    logging.critical("This is a critical message.")
