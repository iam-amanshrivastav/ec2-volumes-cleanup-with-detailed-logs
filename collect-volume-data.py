
# Lambda Function to Collect EBS Volume Metadata
# This Lambda function includes:

# Lists all EBS volumes (Active & Unattached).
# Extracts Volume ID, State, Last Activity & Tags.
# Stores data in a new CSV file with timestamp in S3


import boto3
import csv
from datetime import datetime

ec2 = boto3.client('ec2')
s3 = boto3.client('s3')

S3_BUCKET = 'ebs-volume-logs-automation'
execution_time = datetime.today().strftime('%Y-%m-%d_%H-%M-%S')
FILE_NAME = f'volume_report_{execution_time}.csv'

volumes = ec2.describe_volumes()['Volumes']
data = []

for vol in volumes:
    vol_id = vol['VolumeId']
    state = vol['State']
    create_date = vol['CreateTime'].strftime('%Y-%m-%d')
    tags = {tag['Key']: tag['Value'] for tag in vol.get('Tags', [])}
    attached = state not in ['available', 'inactive']

    # Apply or remove 'UnattachedSince' tag
    if not attached and 'UnattachedSince' not in tags:
        today = datetime.today().strftime('%Y-%m-%d')
        ec2.create_tags(Resources=[vol_id], Tags=[{'Key': 'UnattachedSince', 'Value': today}])
        tags['UnattachedSince'] = today

    if attached and 'UnattachedSince' in tags:
        ec2.delete_tags(Resources=[vol_id], Tags=[{'Key': 'UnattachedSince'}])
        tags.pop('UnattachedSince')

    data.append([
        vol_id,
        state,
        create_date,
        tags.get('UnattachedSince', ''),  # new column
        str(tags)
    ])

# Write CSV to S3
with open('/tmp/' + FILE_NAME, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Volume ID', 'State', 'CreateTime', 'Unattached Since', 'Tags'])
    writer.writerows(data)

s3.upload_file('/tmp/' + FILE_NAME, S3_BUCKET, FILE_NAME)

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': f"Volume report {FILE_NAME} uploaded to S3"
    }
