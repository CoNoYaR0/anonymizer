import os
import sys

def get_logging_config():
    """
    Creates a logging configuration dictionary.
    This configuration sets up a console logger and, if DEBUG=true,
    a file logger that mirrors the console output.
    """
    LOG_LEVEL = "INFO"
    DEBUG_MODE = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    if DEBUG_MODE:
        LOG_LEVEL = "DEBUG"

    # Base configuration with a console handler
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": LOG_LEVEL,
            "handlers": ["console"],
        },
    }

    if DEBUG_MODE:
        # If in debug mode, add a file handler to mirror the console output.
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": "anonymizer.log",
            "maxBytes": 5 * 1024 * 1024,  # 5 MB
            "backupCount": 3,
            "encoding": "utf-8",
        }
        # Add the file handler to the root logger's list of handlers
        config["root"]["handlers"].append("file")

    return config
