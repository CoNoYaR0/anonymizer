import uvicorn
from logger_config import get_logging_config
import os

if __name__ == "__main__":
    # The .env file is now loaded in main.py, which is the Uvicorn entry point.
    # This ensures it's loaded correctly even when using the reloader.

    # Get the logging configuration
    log_config = get_logging_config()

    # Get server settings from environment variables
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "False").lower() in ("true", "1", "t")

    # Run the Uvicorn server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_config=log_config
    )
