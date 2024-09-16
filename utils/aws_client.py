'''
Created on 13-Sep-2024

@author: ongraph
'''
import boto3
from botocore.exceptions import NoCredentialsError


class AwsClient():
    
    def __init__(self, aws_access_key: str, aws_secret_key: str, aws_region: str):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_region = aws_region

    def get_instance(self, service_name: str):
        return boto3.client(
            service_name,
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.aws_region
        )
        
    # Function to upload file bytes and return the URL
    def upload_file_bytes_to_s3(self, file_bytes, bucket, s3_file_name):
        client = self.get_instance(service_name="s3")
        try:
            # Upload the file bytes to S3
            client.put_object(Bucket=bucket, Key=s3_file_name, Body=file_bytes, ContentDisposition='inline', ContentType='image/png')
            # Construct the file URL
            file_url = f"https://{bucket}.s3.{self.aws_region}.amazonaws.com/{s3_file_name}"
            print(f"File uploaded to: {file_url}")
            return file_url
        except FileNotFoundError:
            print("The file was not found.")
        except NoCredentialsError:
            print("Credentials not available.")
            
    # Function to upload file and return URL
    def upload_file_to_s3(self, file_name, bucket, s3_file_name):
        client = self.get_instance(service_name="s3")
        try:
            # Upload the file to S3
            client.upload_file(file_name, bucket, s3_file_name, ContentDisposition='inline')
            # Construct the file URL
            file_url = f"https://{bucket}.s3.{self.aws_region}.amazonaws.com/{s3_file_name}"
            print(f"File uploaded to: {file_url}")
            return file_url
        except FileNotFoundError:
            raise Exception("The file was not found.")
        except NoCredentialsError:
            raise Exception("Credentials not available.")        
