import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Load database connection config from environment
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost") 
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "airflow")

CLEAN_FILE_PATH = os.getenv("CLEAN_FILE_PATH", "data/processed/cleaned_sales_data.csv")
TABLE_NAME = "sales"

def get_db_engine():
    """Create SQLAlchemy engine for PostgreSQL."""
    try:
        url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(url)
        return engine
    except Exception as e:
        logger.error(f"Failed to configure SQL engine: {e}")
        raise

def init_table(engine):
    """Create sales table with schema if it doesn't exist."""
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50),
        sale_date DATE NOT NULL,
        country VARCHAR(50),
        product VARCHAR(100),
        quantity INTEGER,
        unit_price NUMERIC(10, 2),
        total_amount NUMERIC(10, 2),
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(create_table_sql))
        logger.info(f"Table '{TABLE_NAME}' schema validated.")
    except Exception as e:
        logger.error(f"Failed to create table: {e}")
        raise

def clear_existing_data(engine):
    """Truncate table before loading to prevent duplicates."""
    try:
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME};"))
        logger.info(f"Table '{TABLE_NAME}' truncated to prevent duplicates.")
    except Exception as e:
        logger.error(f"Failed to clear table: {e}")
        raise

def load_data_to_postgres(engine):
    """Read cleaned CSV and insert into PostgreSQL."""
    if not os.path.exists(CLEAN_FILE_PATH):
        raise FileNotFoundError(f"Cleaned file not found: {CLEAN_FILE_PATH}")

    logger.info(f"Reading file: {CLEAN_FILE_PATH}")
    df = pd.read_csv(CLEAN_FILE_PATH)

    try:
        logger.info(f"Inserting {len(df)} rows into '{TABLE_NAME}'...")
        
        df.to_sql(TABLE_NAME, engine, if_exists='append', index=False)
        
        logger.info(f"Loading completed successfully.")
    except Exception as e:
        logger.error(f"Failed to insert data: {e}")
        raise

def run_loading_pipeline():
    """Main entry point: load cleaned data into PostgreSQL."""
    logger.info("Starting PostgreSQL load...")
    try:
        engine = get_db_engine()
        
        # Ensure table structure exists
        init_table(engine)
        
        # Clear old data for idempotence
        clear_existing_data(engine)
        
        # Load new data
        load_data_to_postgres(engine)
        
        logger.info("Loading pipeline completed.")
    except Exception as e:
        logger.error(f"Loading pipeline failed.")
        raise

if __name__ == "__main__":
    run_loading_pipeline()