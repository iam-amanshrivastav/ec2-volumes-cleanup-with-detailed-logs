# AWS EC2 Volume Cleanup with detailed logs via Automation

This project automates the lifecycle of AWS EBS volumes and snapshots to reduce cloud waste and maintain auditability. It:
- Tracks when a volume was last unattached (UnattachedSince)
- Deletes volumes idle for 15+ days — unless tagged with do-not-delete
- Creates snapshots before deleting volumes, and expires them after 15 days
- Logs everything in structured CSV files in S3
- Sends a daily email report using Amazon SNS

#  Features

 - Safe deletion of idle EBS volumes

 - Snapshot backup before deletion
 
 - Automatic cleanup of expired snapshots
 
 - if tag value is under any volume `` do-not-delete `` it'll not delete that volume tag protection
 
 - Fully logged to S3 with CSV files
 
 - Summary email via SNS
 
 - Modular: built with two Lambda functions
 
 - Scheduled using Amazon EventBridge

# Steps for doing this Project

Step 1: Create an S3 Bucket for Storing Logs

Step 2: Create an SNS Topic for Notifications

Step 3: Set Up IAM Role for Lambda

Step 4: Lambda Function to Collect EBS Volume Data

Step 5: Lambda Function to Delete Inactive Volumes & Manage Snapshots

Step 6: Create a EventBridge rule to trigger EBS Volume Data funtion to collect the logs

Step 7: Create a EventBridge rule to trigger Lambda Function to Delete Inactive Volumes & Manage Snapshots.
