import uvicorn
import logging.config
from logger_config import get_logging_config
import os

if __name__ == "__main__":
    # The .env file is loaded in main.py, which is the Uvicorn entry point.
    # This ensures it's loaded correctly even when using the reloader.

    # Get the logging configuration dictionary
    log_config_dict = get_logging_config()

    # Apply the logging configuration
    logging.config.dictConfig(log_config_dict)

    # Get a logger to announce the server start
    logger = logging.getLogger(__name__)

    # Get server settings from environment variables
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "False").lower() in ("true", "1", "t")

    logger.info(f"Starting server at http://{host}:{port} with reload={'enabled' if reload else 'disabled'}")

    # Run the Uvicorn server, but prevent it from overriding our logging config
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_config=None  # Important: Prevent Uvicorn from using its own logger
    )
