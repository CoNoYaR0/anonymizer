import os
import psycopg2
import logging
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import Optional

# Load environment variables at the module level
load_dotenv(verbose=True)
logger = logging.getLogger(__name__)

# --- Database Connection Pool ---
connection_pool = None

def _get_supabase_db_url() -> str:
    """
    Constructs the PostgreSQL connection string from Supabase environment variables.
    """
    db_host = os.getenv("DB_HOST")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    if not all([db_host, db_user, db_password]):
        raise ValueError(
            "Missing required Supabase database environment variables: "
            "DB_HOST, DB_USER, DB_PASSWORD."
        )

    return f"postgresql://{db_user}:{db_password}@{db_host}:6543/postgres"


def initialize_connection_pool():
    """
    Initializes the PostgreSQL connection pool.
    """
    global connection_pool
    if connection_pool:
        return

    try:
        db_url = _get_supabase_db_url()
        logger.info("Initializing database connection pool...")
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1, maxconn=10, dsn=db_url
        )
        logger.info("Database connection pool initialized successfully.")
    except Exception as e:
        logger.critical(f"Could not initialize database connection pool: {e}", exc_info=True)
        # Propagate the exception to let the application decide how to handle a startup failure.
        raise


def get_db_connection():
    """
    Gets a connection from the pool.
    """
    if connection_pool is None:
        initialize_connection_pool()
    return connection_pool.getconn()

def release_db_connection(conn):
    """
    Releases a connection back to the pool.
    """
    if connection_pool:
        connection_pool.putconn(conn)

# --- Caching Logic ---

def get_cached_html(file_hash: str) -> Optional[str]:
    """
    Retrieves cached HTML content from the database for a given file hash.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT html_content FROM html_cache WHERE hash = %s",
                (file_hash,)
            )
            result = cursor.fetchone()
            if result:
                logger.debug(f"Cache hit for hash: {file_hash}")
                return result[0]
            else:
                logger.info(f"Cache miss for hash: {file_hash}")
                return None
    except Exception as e:
        logger.error(f"Error getting cached HTML for hash {file_hash}: {e}", exc_info=True)
        return None
    finally:
        if conn:
            release_db_connection(conn)

def cache_html(file_hash: str, html_content: str) -> None:
    """
    Saves new HTML content to the database cache.
    Uses INSERT ... ON CONFLICT to prevent errors on duplicate entries.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Upsert operation: insert or update if the hash already exists
            cursor.execute(
                """
                INSERT INTO html_cache (hash, html_content)
                VALUES (%s, %s)
                ON CONFLICT (hash) DO UPDATE SET
                html_content = EXCLUDED.html_content;
                """,
                (file_hash, html_content)
            )
            conn.commit()
            logger.info(f"Successfully cached HTML for hash: {file_hash}")
    except Exception as e:
        logger.error(f"Error caching HTML for hash {file_hash}: {e}", exc_info=True)
        if conn:
            conn.rollback() # Roll back the transaction on error
    finally:
        if conn:
            release_db_connection(conn)

# Initialize the pool when the module is loaded
initialize_connection_pool()
