import os
import sys
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from typing import Optional
from urllib.parse import urlparse

# Load environment variables at the module level
load_dotenv()

# --- Database Connection Pool ---
connection_pool = None

def _get_supabase_db_url() -> str:
    """
    Constructs the PostgreSQL connection string from Supabase environment variables.

    Returns:
        The full PostgreSQL DSN.

    Raises:
        ValueError: If any of the required Supabase environment variables are missing.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    db_password = os.getenv("DB_PASSWORD")

    if not all([supabase_url, db_password]):
        raise ValueError(
            "Missing one or more required Supabase environment variables: "
            "SUPABASE_URL, DB_PASSWORD"
        )

    # The project reference is the subdomain in the Supabase URL
    project_ref = urlparse(supabase_url).hostname.split('.')[0]

    # Supabase PostgreSQL connection string format
    return f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:5432/postgres"


def initialize_connection_pool():
    """
    Initializes the PostgreSQL connection pool using Supabase credentials.
    This should be called once when the application starts up.
    """
    global connection_pool
    if connection_pool:
        return

    try:
        db_url = _get_supabase_db_url()
        print("Initializing database connection pool...")
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=db_url
        )
        print("Database connection pool initialized successfully.")
    except (ValueError, psycopg2.OperationalError) as e:
        print(f"Error: Could not connect to the database and initialize pool.", file=sys.stderr)
        print(f"Please check your Supabase environment variables in the .env file.", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)


def get_db_connection():
    """
    Gets a connection from the pool.
    """
    if connection_pool is None:
        # This should ideally not be hit if startup event is handled correctly
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
    # TODO: Implement the database query logic.
    print(f"TODO: Checking cache for hash: {file_hash}")
    conn = None
    try:
        conn = get_db_connection()
        # Placeholder
    finally:
        if conn:
            release_db_connection(conn)
    return None

def cache_html(file_hash: str, html_content: str) -> None:
    """
    Saves new HTML content to the database cache.
    """
    # TODO: Implement the database insertion logic.
    print(f"TODO: Caching HTML for hash: {file_hash}")
    conn = None
    try:
        conn = get_db_connection()
        # Placeholder
    finally:
        if conn:
            release_db_connection(conn)
    pass

# Initialize the pool when the module is loaded for simplicity.
# FastAPI startup event will ensure it's ready.
initialize_connection_pool()
