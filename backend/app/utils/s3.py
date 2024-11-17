import boto3
from botocore.client import Config
from config import S3_ACCESS_KEY, S3_SECRET_KEY, S3_ENDPOINT, S3_BUCKET_NAME, S3_REGION

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        config=Config(signature_version='s3v4')
    )

def init_s3():
    """Initialize S3 bucket if it doesn't exist"""
    s3_client = get_s3_client()
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
    except:
        s3_client.create_bucket(
            Bucket=S3_BUCKET_NAME,
            CreateBucketConfiguration={'LocationConstraint': S3_REGION}
        )
        # Make bucket public
        s3_client.put_bucket_policy(
            Bucket=S3_BUCKET_NAME,
            Policy=f'''{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Sid": "PublicRead",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": ["arn:aws:s3:::{S3_BUCKET_NAME}/*"]
                    }}
                ]
            }}'''
        )

def upload_file(file_data: bytes, file_name: str, content_type: str) -> str:
    """Upload file to S3 and return its URL"""
    s3_client = get_s3_client()
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=file_name,
        Body=file_data,
        ContentType=content_type
    )
    return f"{S3_ENDPOINT}/{S3_BUCKET_NAME}/{file_name}"

def delete_file(file_name: str):
    """Delete file from S3"""
    s3_client = get_s3_client()
    s3_client.delete_object(
        Bucket=S3_BUCKET_NAME,
        Key=file_name
    ) 