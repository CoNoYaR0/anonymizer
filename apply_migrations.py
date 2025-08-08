import os
import sys
import logging
import psycopg2
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# It's better to import the tested function than to duplicate logic.
# We need to temporarily add `src` to the path to allow the import
# when running this script from the root directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from database import _get_supabase_db_url

def apply_migrations():
    """
    Connects to the PostgreSQL database using Supabase credentials
    and applies the necessary schema migrations.
    """
    # Load environment variables from .env file
    load_dotenv()

    conn = None
    try:
        # Get the connection string from our centralized function
        db_url = _get_supabase_db_url()

        # Connect to the database
        logger.info("Connecting to the database...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # Create the html_cache table
        # This table will store the HTML content of converted DOCX files,
        # using the file's SHA-256 hash as the primary key to avoid re-conversion.
        logger.info("Creating table: html_cache...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS html_cache (
            hash TEXT PRIMARY KEY,
            html_content TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        cursor.close()
        logger.info("Database migration applied successfully.")

    except (ValueError, psycopg2.OperationalError) as e:
        logger.critical("Error: Could not connect to the database.", exc_info=True)
        logger.critical("Please check your Supabase environment variables in the .env file.")
        sys.exit(1)

    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)

    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")

if __name__ == "__main__":
    apply_migrations()
