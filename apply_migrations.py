import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

def apply_migrations():
    """
    Connects to the PostgreSQL database and applies the necessary schema migrations.
    """
    # Load environment variables from .env file
    load_dotenv()

    db_url = os.getenv("DB_URL")
    if not db_url:
        print("Error: DB_URL environment variable is not set.", file=sys.stderr)
        print("Please create a .env file and set the DB_URL.", file=sys.stderr)
        sys.exit(1)

    conn = None
    try:
        # Connect to the database
        print(f"Connecting to the database...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # Create the html_cache table
        # This table will store the HTML content of converted DOCX files,
        # using the file's SHA-256 hash as the primary key to avoid re-conversion.
        print("Creating table: html_cache...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS html_cache (
            hash TEXT PRIMARY KEY,
            html_content TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        cursor.close()
        print("Database migration applied successfully.")

    except psycopg2.OperationalError as e:
        print(f"Error: Could not connect to the database.", file=sys.stderr)
        print(f"Please check your DB_URL and ensure the database server is running.", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    apply_migrations()
