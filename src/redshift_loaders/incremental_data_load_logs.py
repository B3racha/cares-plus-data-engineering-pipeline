
import os
import logging
from urllib.parse import unquote_plus

import psycopg2

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Redshift configuration from Lambda environment variables
REDSHIFT_HOST = os.environ["REDSHIFT_HOST"]
REDSHIFT_PORT = os.environ.get("REDSHIFT_PORT", "5439")
REDSHIFT_DATABASE = os.environ["REDSHIFT_DATABASE"]
REDSHIFT_USER = os.environ["REDSHIFT_USER"]
REDSHIFT_PASSWORD = os.environ["REDSHIFT_PASSWORD"]
REDSHIFT_TABLE = os.environ.get(
    "REDSHIFT_TABLE", "public.support_logs"
)
IAM_ROLE = os.environ["REDSHIFT_IAM_ROLE"]
AWS_REGION = os.environ.get("AWS_REGION", "eu-north-1")


def lambda_handler(event, context):

    conn = None
    cursor = None

    try:
        # 1. Read the S3 event
        record = event["Records"][0]

        bucket_name = record["s3"]["bucket"]["name"]
        input_key = unquote_plus(record["s3"]["object"]["key"])

        s3_input_path = f"s3://{bucket_name}/{input_key}"

        logger.info("Triggered by: %s", s3_input_path)

        # 2. Connect to Redshift
        conn = psycopg2.connect(
            host=REDSHIFT_HOST,
            port=REDSHIFT_PORT,
            database=REDSHIFT_DATABASE,
            user=REDSHIFT_USER,
            password=REDSHIFT_PASSWORD,
            sslmode="require"
        )

        cursor = conn.cursor()

        # 3. Load the Parquet file into Redshift
        copy_sql = f"""
            COPY {REDSHIFT_TABLE}
            FROM '{s3_input_path}'
            IAM_ROLE '{IAM_ROLE}'
            FORMAT AS PARQUET
            REGION '{AWS_REGION}';
        """

        cursor.execute(copy_sql)
        conn.commit()

        logger.info(
            "Successfully loaded data from %s into %s",
            s3_input_path,
            REDSHIFT_TABLE
        )

    except Exception:
        if conn:
            conn.rollback()

        logger.exception("Redshift data loading failed")
        raise

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()
