import os
import logging
from database import get_db_connection, release_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_migrations():
    """
    Connects to the database and applies all SQL migrations from the 'migrations' directory.
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.critical("Could not get a database connection. Aborting migrations.")
            return

        with conn.cursor() as cur:
            migrations_dir = 'migrations'
            logger.info(f"Looking for migrations in '{migrations_dir}' directory...")

            # Get all .sql files and sort them by name to ensure order
            migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])

            if not migration_files:
                logger.warning("No migration files found.")
                return

            logger.info(f"Found {len(migration_files)} migration files to apply.")

            for migration_file in migration_files:
                file_path = os.path.join(migrations_dir, migration_file)
                logger.info(f"Applying migration: {migration_file}...")
                with open(file_path, 'r') as f:
                    sql_script = f.read()
                    if sql_script: # Ensure file is not empty
                        cur.execute(sql_script)
                        logger.info(f"Successfully applied {migration_file}.")
                    else:
                        logger.warning(f"Migration file {migration_file} is empty. Skipping.")

            conn.commit()
            logger.info("All migrations applied successfully.")

    except Exception as e:
        logger.critical(f"An error occurred during migration: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_db_connection(conn)

if __name__ == "__main__":
    apply_migrations()
