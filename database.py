import os
import logging
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# --- Database Connection Pool ---
connection_pool = None

def get_connection_pool():
    """
    Initializes and returns a singleton connection pool.
    This function will be called once to initialize the pool.
    """
    global connection_pool
    if connection_pool is None:
        try:
            db_url = os.getenv("DB_URL")
            if not db_url:
                logger.error("DB_URL environment variable not set. Cannot initialize database connection.")
                raise ValueError("Database connection URL is not configured.")

            logger.info("Initializing database connection pool...")
            connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=db_url
            )
            logger.info("Database connection pool initialized successfully.")
        except psycopg2.OperationalError as e:
            logger.critical(f"Could not connect to the database: {e}", exc_info=True)
            raise
    return connection_pool

def get_db_connection():
    """
    Gets a connection from the pool.
    This should be used by other modules to interact with the database.
    """
    pool = get_connection_pool()
    if pool:
        return pool.getconn()
    return None

def release_db_connection(conn):
    """
    Releases a connection back to the pool.
    """
    pool = get_connection_pool()
    if pool:
        pool.putconn(conn)

def close_connection_pool():
    """
    Closes all connections in the pool.
    Called on application shutdown.
    """
    global connection_pool
    if connection_pool:
        logger.info("Closing database connection pool.")
        connection_pool.closeall()
        connection_pool = None
