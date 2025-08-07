import os
import logging

def get_logging_config():
    """
    Creates a logging configuration dictionary for Uvicorn.
    """
    LOG_LEVEL = "INFO"
    DEBUG_MODE = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    if DEBUG_MODE:
        LOG_LEVEL = "DEBUG"

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(asctime)s - %(name)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            "": {"handlers": ["default"], "level": LOG_LEVEL},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
        },
    }

    if DEBUG_MODE:
        # Add a file handler only when DEBUG is true
        config["handlers"]["debug_file"] = {
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "anonymizer.log",
            "maxBytes": 5 * 1024 * 1024,  # 5 MB
            "backupCount": 3,
            "encoding": "utf-8",
        }
        # Add the file handler to the root logger
        config["loggers"][""]["handlers"].append("debug_file")
        logging.getLogger().info("DEBUG mode is active. Logging all levels to anonymizer.log")


    return config
