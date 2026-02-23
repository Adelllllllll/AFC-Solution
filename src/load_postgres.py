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

CLEAN_SALES_PATH = os.getenv("CLEAN_SALES_PATH", "data/processed/cleaned_sales_data.csv")
TABLE_SALES_NAME = "sales"
CLEAN_CAMP_PATH = os.getenv("CLEAN_CAMP_PATH", "data/processed/cleaned_campaign_product.csv")
TABLE_CAMP_NAME = "campaign_product"
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
    """Create tables with schema if they don't exist."""
    create_sales_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_SALES_NAME} (
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
    
    create_camp_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_CAMP_NAME} (
        id SERIAL PRIMARY KEY,
        campaign_id VARCHAR(50),
        product VARCHAR(100),
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(create_sales_sql))
            conn.execute(text(create_camp_sql))
        logger.info(f"Tables '{TABLE_SALES_NAME}' and '{TABLE_CAMP_NAME}' schemas validated.")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise

def clear_existing_data(engine):
    """Truncate tables before loading to prevent duplicates."""
    try:
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {TABLE_SALES_NAME};"))
            conn.execute(text(f"TRUNCATE TABLE {TABLE_CAMP_NAME};"))
        logger.info(f"Tables '{TABLE_SALES_NAME}' and '{TABLE_CAMP_NAME}' truncated to prevent duplicates.")
    except Exception as e:
        logger.error(f"Failed to clear tables: {e}")
        raise

def load_data_to_postgres(engine, file_path, table_name):
    """Read cleaned CSV and insert into PostgreSQL."""
    if not os.path.exists(file_path):
        logger.warning(f"Cleaned file not found: {file_path}. Skipping load for this table.")
        return

    logger.info(f"Reading file: {file_path}")
    df = pd.read_csv(file_path)

    try:
        logger.info(f"Inserting {len(df)} rows into '{table_name}'...")
        
        df.to_sql(table_name, engine, if_exists='append', index=False)
        
        logger.info(f"Loading to '{table_name}' completed successfully.")
    except Exception as e:
        logger.error(f"Failed to insert data into '{table_name}': {e}")
        raise

def run_loading_pipeline():
    """Main entry point: load cleaned data into PostgreSQL."""
    logger.info("Starting PostgreSQL load...")
    try:
        engine = get_db_engine()
        
        # Ensure table structures exist
        init_table(engine)
        
        # Clear old data for idempotence
        clear_existing_data(engine)
        
        # Load new data
        load_data_to_postgres(engine, CLEAN_SALES_PATH, TABLE_SALES_NAME)
        load_data_to_postgres(engine, CLEAN_CAMP_PATH, TABLE_CAMP_NAME)
        
        logger.info("Loading pipeline completed.")
    except Exception as e:
        logger.error("Loading pipeline failed.")
        raise

if __name__ == "__main__":
    run_loading_pipeline()