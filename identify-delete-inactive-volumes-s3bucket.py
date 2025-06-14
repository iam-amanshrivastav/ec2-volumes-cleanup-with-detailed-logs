# Reads latest volume report from S3 dynamically.
# Filters inactive volumes (older than 15 days), creates snapshots before deletion.
# Stores deletion logs in S3 (including snapshot expiration dates).
# Sends a single SNS email notifications containing volumed id, snapshot id, snapshot expiration date.
# Deletes snapshots automatically after 15 days.

import boto3
import csv
import os
from datetime import datetime, timedelta

ec2 = boto3.client('ec2')
s3 = boto3.client('s3')
sns = boto3.client('sns')

S3_BUCKET = 'ebs-volume-logs-automation'
SNS_TOPIC_ARN = 'arn:aws:sns:eu-west-1:619071349184:EBS-Deletion-Alerts'
execution_time = datetime.today().strftime('%Y-%m-%d_%H-%M-%S')
threshold_date = datetime.today() - timedelta(days=15)
OUTPUT_FILE = f"/tmp/deleted_volumes_{execution_time}.csv"

# Load latest volume report
files = [obj['Key'] for obj in s3.list_objects_v2(Bucket=S3_BUCKET)['Contents'] if obj['Key'].startswith('volume_report_')]
latest = sorted(files, key=lambda x: x.split('_')[-1], reverse=True)[0]
lines = s3.get_object(Bucket=S3_BUCKET, Key=latest)['Body'].read().decode('utf-8').splitlines()
reader = csv.reader(lines)
next(reader)

deleted_volumes = []
expired_snapshots = []
sns_lines = [f"EBS Cleanup Summary - {execution_time}", ""]

# Process volume rows
for row in reader:
    vol_id, state, _, unattached_since, tags_raw = row
    tags = eval(tags_raw) if tags_raw else {}

    # 🛡️ Skip any volume tagged with value 'do-not-delete'
    if 'do-not-delete' in [v.lower() for v in tags.values()]:
        continue

    if state == 'available' and unattached_since:
        age = (datetime.today().date() - datetime.strptime(unattached_since, '%Y-%m-%d').date()).days
        if age >= 15:
            # Create snapshot before deletion
            snapshot = ec2.create_snapshot(
                VolumeId=vol_id,
                Description=f"Snapshot before deleting Volume {vol_id} on {execution_time}"
            )
            snapshot_id = snapshot['SnapshotId']
            snapshot_exp = (datetime.today() + timedelta(days=15)).strftime('%Y-%m-%d')

            ec2.delete_volume(VolumeId=vol_id)
            deleted_volumes.append([vol_id, state, unattached_since, snapshot_id, snapshot_exp])
            sns_lines.append(f"🗑️ Volume {vol_id} → Snapshot {snapshot_id} (expires: {snapshot_exp})")

# Cleanup expired snapshots
snapshots = ec2.describe_snapshots(OwnerIds=['self'])['Snapshots']
for snap in snapshots:
    if "Snapshot before deleting Volume" not in snap.get('Description', ''):
        continue

    snap_time = snap['StartTime'].replace(tzinfo=None)
    expired_date = (snap_time + timedelta(days=15)).date()
    today = datetime.today().date()

    if expired_date < today:
        ec2.delete_snapshot(SnapshotId=snap['SnapshotId'])
        expired_snapshots.append([snap['SnapshotId'], expired_date.strftime('%Y-%m-%d'), "Deleted"])
        sns_lines.append(f"⚠️ Expired Snapshot: {snap['SnapshotId']} (expired: {expired_date.strftime('%Y-%m-%d')})")

# Write deletion log to CSV
with open(OUTPUT_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Volume ID', 'State', 'Unattached Since', 'Snapshot ID', 'Snapshot Expiration'])
    writer.writerows(deleted_volumes)
    writer.writerow([])
    writer.writerow(['Snapshot ID', 'Expiration Date', 'Status'])
    writer.writerows(expired_snapshots)

s3.upload_file(OUTPUT_FILE, S3_BUCKET, OUTPUT_FILE.split('/')[-1])

# Send SNS notification
sns.publish(
    TopicArn=SNS_TOPIC_ARN,
    Message="\n".join(sns_lines) if deleted_volumes or expired_snapshots else "No cleanup needed.",
    Subject="EBS Cleanup Summary Report"
)

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': f"Cleanup report {OUTPUT_FILE.split('/')[-1]} uploaded"
    }
