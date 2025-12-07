#%% AWS Glue Job - Production ETL Template
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from datetime import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

#%% Job Configuration
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'source_bucket',
    'target_bucket',
    'database_name',
    'table_name'
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

#%% ETL Functions
def extract_data():
    """Extract data from S3."""
    source_path = f"s3://{args['source_bucket']}/raw-data/"
    
    dynamic_frame = glueContext.create_dynamic_frame.from_options(
        connection_type="s3",
        connection_options={"paths": [source_path]},
        format="parquet"
    )
    
    logger.info(f"Extracted {dynamic_frame.count()} records")
    return dynamic_frame

def transform_data(dynamic_frame):
    """Transform data with business logic."""
    df = dynamic_frame.toDF()
    
    # Add processing timestamp
    df = df.withColumn("processed_at", current_timestamp())
    
    # Business transformations
    df = df.withColumn(
        "category",
        when(col("amount") > 10000, "High")
        .when(col("amount") > 1000, "Medium")
        .otherwise("Low")
    )
    
    return DynamicFrame.fromDF(df, glueContext, "transformed")

def load_data(dynamic_frame):
    """Load data to target."""
    target_path = f"s3://{args['target_bucket']}/processed-data/"
    
    glueContext.write_dynamic_frame.from_options(
        frame=dynamic_frame,
        connection_type="s3",
        connection_options={"path": target_path},
        format="parquet"
    )
    
    logger.info("Data loaded successfully")

#%% Main Process
try:
    raw_data = extract_data()
    transformed_data = transform_data(raw_data)
    load_data(transformed_data)
    
    logger.info("ETL job completed successfully")
    
except Exception as e:
    logger.error(f"ETL job failed: {str(e)}")
    raise

finally:
    job.commit()