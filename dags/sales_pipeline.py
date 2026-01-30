import sys
import os
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

# Add src directory to Python path
sys.path.append("/opt/airflow")

# Import pipeline functions
try:
    from src.ingest_s3 import raw_to_s3
    from src.clean_data import run_cleaning_pipeline
    from src.load_postgres import run_loading_pipeline
except ImportError as e:
    # If imports fail, set to None to prevent webserver crash
    print(f"Import error: {e}")
    raw_to_s3 = None
    run_cleaning_pipeline = None
    run_loading_pipeline = None

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'sales_daily_ingest',
    default_args=default_args,
    description='Daily sales ETL pipeline',
    schedule_interval='@daily',
    catchup=False,
    tags=['sales', 'etl', 'afc'],
) as dag:

    # Task 1: Upload raw data to S3
    ingest_task = PythonOperator(
        task_id='ingest_to_s3',
        python_callable=raw_to_s3
    )

    # Task 2: Clean and transform data
    clean_task = PythonOperator(
        task_id='clean_data',
        python_callable=run_cleaning_pipeline
    )

    # Task 3: Load cleaned data to PostgreSQL
    load_task = PythonOperator(
        task_id='load_to_postgres',
        python_callable=run_loading_pipeline
    )

    # Define task dependencies
    ingest_task >> clean_task >> load_task