import os
import logging
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Load S3 and file path config from environment
LOCALSTACK_URL = os.getenv("LOCALSTACK_URL", "http://localstack:4566")
BUCKET_NAME = os.getenv("S3_BUCKET_RAW", "sales-data-raw")
RAW_FILE_PATH = os.getenv("RAW_FILE_PATH", "data/raw/sales_data.csv")
OBJECT_SALES = os.getenv("S3_SALES_OBJECT", "sales_data.csv")
RAW_CAMP_PATH = os.getenv("RAW_CAMP_PATH", "data/raw/campaign_product.csv")
OBJECT_CAMP = os.getenv("S3_CAMP_OBJECT", "campaign_product.csv")

def create_s3_client():
    """Initialize S3 client connected to LocalStack."""
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=LOCALSTACK_URL,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            verify=False
        )
        logger.info("Connected to LocalStack S3 at %s", LOCALSTACK_URL)
        return s3_client
    except Exception as e:
        logger.error("Failed to create S3 client: %s", e)
        raise


def ensure_bucket_exists(s3_client, bucket_name):
    """Create bucket if it doesn't exist."""
    try:
        buckets = [b["Name"] for b in s3_client.list_buckets().get("Buckets", [])]
        if bucket_name not in buckets:
            s3_client.create_bucket(Bucket=bucket_name)
            logger.info("Bucket '%s' created successfully.", bucket_name)
        else:
            logger.info("Bucket '%s' already exists.", bucket_name)
    except ClientError as e:
        logger.error("Failed to create or access bucket '%s': %s", bucket_name, e)
        raise


def upload_file_to_s3(s3_client, file_path, bucket_name, object_name):
    """Upload local file to S3."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        s3_client.upload_file(file_path, bucket_name, object_name)
        logger.info("File '%s' uploaded to s3://%s/%s", file_path, bucket_name, object_name)
    except NoCredentialsError:
        logger.error("AWS credentials not found.")
        raise
    except ClientError as e:
        logger.error("S3 upload failed: %s", e)
        raise


def verify_upload(s3_client, bucket_name, object_name):
    """Check if file was successfully uploaded to S3."""
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    contents = [obj["Key"] for obj in response.get("Contents", [])]
    if object_name in contents:
        logger.info("Verification successful: '%s' found in bucket '%s'.", object_name, bucket_name)
    else:
        logger.warning("Verification failed: '%s' not found in bucket '%s'.", object_name, bucket_name)


def raw_to_s3():
    """Main entry point: upload raw data to S3."""
    logger.info("Starting raw data upload to S3")

    try:
        s3_client = create_s3_client()
        ensure_bucket_exists(s3_client, BUCKET_NAME)
        upload_file_to_s3(s3_client, RAW_FILE_PATH, BUCKET_NAME, OBJECT_SALES)
        verify_upload(s3_client, BUCKET_NAME, OBJECT_SALES)
        upload_file_to_s3(s3_client, RAW_CAMP_PATH, BUCKET_NAME, OBJECT_CAMP)
        verify_upload(s3_client, BUCKET_NAME, OBJECT_CAMP)
        logger.info("Step 1 completed successfully.")
    except Exception as e:
        logger.error("Step 1 failed: %s", e)
        raise

if __name__ == "__main__":
    raw_to_s3()
    