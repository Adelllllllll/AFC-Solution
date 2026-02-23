import os
import logging
import boto3
import pandas as pd
from io import StringIO
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment config for S3 and file paths
LOCALSTACK_URL = os.getenv("LOCALSTACK_URL", "http://localstack:4566")
BUCKET_NAME = os.getenv("S3_BUCKET_RAW", "sales-data-raw")
OBJECT_SALES = os.getenv("S3_SALES_OBJECT", "sales_data.csv")
CLEAN_FILE_PATH = os.getenv("CLEAN_FILE_PATH", "data/processed/cleaned_sales_data.csv")
OBJECT_CAMP = os.getenv("S3_CAMP_OBJECT", "campaign_product.csv")
CLEAN_CAMP_PATH = os.getenv("CLEAN_CAMP_PATH", "data/processed/cleaned_campaign_product.csv")

def get_s3_client():
    """Initialize S3 client for LocalStack."""
    return boto3.client(
        "s3",
        endpoint_url=LOCALSTACK_URL,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )

def download_data(s3_client, object_name):
    """Fetch raw CSV from S3 and return as pandas DataFrame."""
    logger.info(f"Downloading {object_name} from bucket {BUCKET_NAME}...")
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=object_name)
        content = response['Body'].read().decode('utf-8')
        df = pd.read_csv(StringIO(content))
        logger.info(f"Data downloaded. Raw shape: {df.shape}")
        return df
    except ClientError as e:
        logger.error(f"S3 download error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}")
        raise

def clean_data(df):
    """Apply data cleaning transformations."""
    logger.info("Starting data cleaning...")
    
    initial_count = len(df)
    
    # Remove duplicate rows
    df = df.drop_duplicates()
    
    # Parse and format date column
    df['sale_date'] = pd.to_datetime(df['sale_date'], errors='coerce')
    
    # Convert numeric columns to proper types
    numeric_cols = ['quantity', 'unit_price', 'total_amount']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # Drop rows with missing values in critical columns
    critical_cols = ['sale_date', 'quantity', 'unit_price', 'total_amount', 'country', 'product']
    
    # Add username if present in data
    if 'username' in df.columns:
        critical_cols.append('username')
        
    df = df.dropna(subset=critical_cols)
    
    # Format date for export
    df['sale_date'] = df['sale_date'].dt.strftime('%Y-%m-%d')

    final_count = len(df)
    deleted = initial_count - final_count
    logger.info(f"Cleaning complete. Rows: {initial_count} -> {final_count} (Deleted: {deleted})")
    
    return df

def clean_campaign(df):
    """Apply data cleaning transformations for campaign product mapping."""
    logger.info("Starting campaign data cleaning...")
    initial_count = len(df)
    
    # Remove duplicate rows
    df = df.drop_duplicates()
    
    # Drop rows with missing values in critical columns
    df = df.dropna(subset=['campaign_id', 'product'])
    
    final_count = len(df)
    deleted = initial_count - final_count
    logger.info(f"Campaign cleaning complete. Rows: {initial_count} -> {final_count} (Deleted: {deleted})")
    
    return df

def save_clean_data_generic(df, path):
    """Localy save the cleaned DataFrame to a specific path."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False)
        logger.info(f"Fichier nettoyé sauvegardé sous: {path}")
    except Exception as e:
        logger.error(f"Impossible de sauvegarder le fichier nettoyé: {e}")
        raise

def save_clean_data(df):
    """Localy save the cleaned DataFrame."""
    try:
        # On s'assure que le dossier 'data/processed' existe
        os.makedirs(os.path.dirname(CLEAN_FILE_PATH), exist_ok=True)
        
        df.to_csv(CLEAN_FILE_PATH, index=False)
        logger.info(f"Fichier nettoyé sauvegardé sous: {CLEAN_FILE_PATH}")
    except Exception as e:
        logger.error(f"Impossible de sauvegarder le fichier nettoyé: {e}")
        raise

def run_cleaning_pipeline():
    """Main entry point: fetch, clean, and save data."""
    try:
        s3 = get_s3_client()
        
        # 1. Clean Sales (Pipeline existante)
        df_raw = download_data(s3, OBJECT_SALES)
        df_clean = clean_data(df_raw)
        save_clean_data_generic(df_clean, CLEAN_FILE_PATH)
        
        # 2. Clean Campaign/Product (Nouvelle Pipeline)
        df_camp_raw = download_data(s3, OBJECT_CAMP)
        df_camp_clean = clean_campaign(df_camp_raw)
        save_clean_data_generic(df_camp_clean, CLEAN_CAMP_PATH)
        
        logger.info("Pipeline de nettoyage terminé avec succès.")
    except Exception as e:
        logger.error(f"Echec du pipeline de nettoyage : {e}")
        raise

if __name__ == "__main__":
    run_cleaning_pipeline()