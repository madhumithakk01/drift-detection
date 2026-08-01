"""
ConfigSync Dashboard - Flask Backend
A professional web application for multi-cloud resource monitoring

To run the application:
1. Ensure AWS CLI is configured with proper credentials
2. Run: python app.py
3. Open browser and navigate to: http://localhost:5000

The application will automatically create the DynamoDB table if it doesn't exist.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask.json.provider import DefaultJSONProvider
import boto3
from botocore.exceptions import ClientError
import os
import logging
import time
import json
import hashlib
import re
import uuid
import copy
from decimal import Decimal
from datetime import datetime
import threading
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DecimalSafeJSONProvider(DefaultJSONProvider):
    """
    DynamoDB always returns numeric attributes as Decimal, which Flask's default
    JSON encoder can't serialize. This converts Decimal -> int (when whole) or
    float, applied globally so every route that returns DynamoDB data (baseline
    summaries, drift status, incidents, the reliability scorecard, etc.) works
    correctly without each function having to handle it individually.
    """
    @staticmethod
    def default(obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return DefaultJSONProvider.default(obj)


app = Flask(__name__)
app.json = DecimalSafeJSONProvider(app)
app.secret_key = 'configsync-dashboard-secret-key-2024'

# Configure APScheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Drift detection configuration
DRIFT_CHECK_INTERVAL = 5  # minutes
SES_SENDER_EMAIL = 'kkmadhumitha01@gmail.com'
SES_RECEIVER_EMAIL = 'madhumithakk1504@gmail.com'
DEMO_USER_EMAIL = 'madhumithakk1504@gmail.com'

# AWS Configuration
AWS_REGION = 'eu-north-1'

# Optional override so the app can run against DynamoDB Local (or any other
# DynamoDB-compatible endpoint) for offline demos/testing. Leave unset to use
# real AWS DynamoDB as before. Example: DYNAMODB_ENDPOINT_URL=http://localhost:8000
DYNAMODB_ENDPOINT_URL = os.environ.get('DYNAMODB_ENDPOINT_URL')
DYNAMODB_TABLE_NAME = 'Users'
SNAPSHOTS_TABLE_NAME = 'Snapshots'
INCIDENTS_TABLE_NAME = 'Incidents'

# Initialize DynamoDB client
try:
    if DYNAMODB_ENDPOINT_URL:
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION, endpoint_url=DYNAMODB_ENDPOINT_URL)
        logger.info(f"Using custom DynamoDB endpoint: {DYNAMODB_ENDPOINT_URL}")
    else:
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    snapshots_table = dynamodb.Table(SNAPSHOTS_TABLE_NAME)
    incidents_table = dynamodb.Table(INCIDENTS_TABLE_NAME)
    logger.info(f"Connected to DynamoDB table: {DYNAMODB_TABLE_NAME}")
    logger.info(f"Connected to DynamoDB table: {SNAPSHOTS_TABLE_NAME}")
    logger.info(f"Connected to DynamoDB table: {INCIDENTS_TABLE_NAME}")
except Exception as e:
    logger.error(f"Failed to connect to DynamoDB: {str(e)}")
    dynamodb = None
    table = None
    snapshots_table = None
    incidents_table = None

def create_table_if_not_exists():
    """Create the Users, Snapshots, and Incidents tables if they don't exist"""
    global table, snapshots_table, incidents_table  # Use the global table variables
    
    # Create Users table
    try:
        table.load()
        logger.info(f"Table {DYNAMODB_TABLE_NAME} already exists")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            try:
                logger.info(f"Creating table {DYNAMODB_TABLE_NAME}...")
                table = dynamodb.create_table(
                    TableName=DYNAMODB_TABLE_NAME,
                    KeySchema=[
                        {
                            'AttributeName': 'email',
                            'KeyType': 'HASH'  # Partition key
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'email',
                            'AttributeType': 'S'
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                table.wait_until_exists()
                logger.info(f"Successfully created table: {DYNAMODB_TABLE_NAME}")
            except Exception as create_error:
                logger.error(f"Failed to create table: {str(create_error)}")
                raise create_error
        else:
            logger.error(f"Error checking table existence: {str(e)}")
            raise e
    
    # Create Snapshots table
    try:
        snapshots_table.load()
        logger.info(f"Table {SNAPSHOTS_TABLE_NAME} already exists")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            try:
                logger.info(f"Creating table {SNAPSHOTS_TABLE_NAME}...")
                snapshots_table = dynamodb.create_table(
                    TableName=SNAPSHOTS_TABLE_NAME,
                    KeySchema=[
                        {
                            'AttributeName': 'user_email',
                            'KeyType': 'HASH'  # Partition key
                        },
                        {
                            'AttributeName': 'snapshot_id',
                            'KeyType': 'RANGE'  # Sort key
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'user_email',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'snapshot_id',
                            'AttributeType': 'S'
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                snapshots_table.wait_until_exists()
                logger.info(f"Successfully created table: {SNAPSHOTS_TABLE_NAME}")
            except Exception as create_error:
                logger.error(f"Failed to create snapshots table: {str(create_error)}")
                raise create_error
        else:
            logger.error(f"Error checking snapshots table existence: {str(e)}")
            raise e

    # Create Incidents table
    try:
        incidents_table.load()
        logger.info(f"Table {INCIDENTS_TABLE_NAME} already exists")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            try:
                logger.info(f"Creating table {INCIDENTS_TABLE_NAME}...")
                incidents_table = dynamodb.create_table(
                    TableName=INCIDENTS_TABLE_NAME,
                    KeySchema=[
                        {
                            'AttributeName': 'user_email',
                            'KeyType': 'HASH'  # Partition key
                        },
                        {
                            'AttributeName': 'incident_id',
                            'KeyType': 'RANGE'  # Sort key
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'user_email',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'incident_id',
                            'AttributeType': 'S'
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                incidents_table.wait_until_exists()
                logger.info(f"Successfully created table: {INCIDENTS_TABLE_NAME}")
            except Exception as create_error:
                logger.error(f"Failed to create incidents table: {str(create_error)}")
                raise create_error
        else:
            logger.error(f"Error checking incidents table existence: {str(e)}")
            raise e

def validate_user_credentials(email, password):
    """Validate user credentials against DynamoDB"""
    try:
        response = table.get_item(Key={'email': email})
        if 'Item' in response:
            stored_password = response['Item'].get('password', '')
            return stored_password == password
        return False
    except Exception as e:
        logger.error(f"Error validating credentials: {str(e)}")
        return False

def create_user(email, password):
    """Create a new user in DynamoDB"""
    try:
        # Check if user already exists
        response = table.get_item(Key={'email': email})
        if 'Item' in response:
            return False, "User already exists"
        
        # Create new user with initial baseline summary
            table.put_item(
                Item={
                    'email': email,
                    'password': password,
                    'last_baseline_summary': {
                        'aws_count': 0,
                        'gcp_count': 0,
                        'azure_count': 0
                    },
                    'detection_status': 'Stopped',
                    'drift_status': {
                        'last_check': None,
                        'drifts_detected': [],
                        'total_drifts': 0
                    },
                    'updated_at': str(int(time.time()))
                }
            )
        logger.info(f"Successfully created user: {email}")
        return True, "User created successfully"
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return False, f"Error creating user: {str(e)}"

def update_baseline_summary(user_email, cloud_counts):
    """Update the last_baseline_summary for a user"""
    try:
        table.update_item(
            Key={'email': user_email},
            UpdateExpression='SET last_baseline_summary = :lbs, updated_at = :ua',
            ExpressionAttributeValues={
                ':lbs': cloud_counts,
                ':ua': str(int(time.time()))
            }
        )
        logger.info(f"Updated baseline summary for user {user_email}: {cloud_counts}")
        return True
    except Exception as e:
        logger.error(f"Error updating baseline summary: {str(e)}")
        return False

def get_baseline_summary(user_email):
    """Get the last baseline summary for a user"""
    try:
        response = table.get_item(Key={'email': user_email})
        if 'Item' in response:
            return response['Item'].get('last_baseline_summary', {
                'aws_count': 0,
                'gcp_count': 0,
                'azure_count': 0
            })
        return {'aws_count': 0, 'gcp_count': 0, 'azure_count': 0}
    except Exception as e:
        logger.error(f"Error getting baseline summary: {str(e)}")
        return {'aws_count': 0, 'gcp_count': 0, 'azure_count': 0}

def create_snapshot(user_email, cloud, resource_type, resource_id, resource_name, config, editable_metadata=None):
    """Create a resource snapshot"""
    try:
        import hashlib
        import json
        
        # Create snapshot ID
        snapshot_id = f"{cloud}#{resource_type}#{resource_id}"
        
        # Create config hash
        config_json = json.dumps(config, sort_keys=True) if isinstance(config, dict) else str(config)
        config_hash = hashlib.sha256(config_json.encode()).hexdigest()
        
        # Create snapshot item
        snapshot_item = {
            'user_email': user_email,
            'snapshot_id': snapshot_id,
            'cloud': cloud,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'resource_name': resource_name,
            'config': config_json,
            'config_hash': config_hash,
            'captured_at': int(time.time()),
            'source': 'baseline'
        }
        
        if editable_metadata:
            snapshot_item['editable_metadata'] = editable_metadata
        
        snapshots_table.put_item(Item=snapshot_item)
        logger.info(f"Created snapshot for {user_email}: {snapshot_id}")
        return True
    except Exception as e:
        logger.error(f"Error creating snapshot: {str(e)}")
        return False

def get_cloud_resource_counts(user_email):
    """Get resource counts per cloud for a user"""
    try:
        response = snapshots_table.query(
            KeyConditionExpression='user_email = :ue',
            ExpressionAttributeValues={':ue': user_email}
        )
        
        counts = {'aws_count': 0, 'gcp_count': 0, 'azure_count': 0}
        
        for item in response['Items']:
            cloud = item.get('cloud', '').upper()
            if cloud == 'AWS':
                counts['aws_count'] += 1
            elif cloud == 'GCP':
                counts['gcp_count'] += 1
            elif cloud == 'AZURE':
                counts['azure_count'] += 1
        
        return counts
    except Exception as e:
        logger.error(f"Error getting cloud resource counts: {str(e)}")
        return {'aws_count': 0, 'gcp_count': 0, 'azure_count': 0}

def run_baseline_collection(user_email):
    """Run baseline collection for all configured cloud providers"""
    try:
        # Get user's cloud credentials
        response = table.get_item(Key={'email': user_email})
        if 'Item' not in response:
            return {'success': False, 'errors': ['User not found']}
        
        user_data = response['Item']
        cloud_credentials = user_data.get('cloud_credentials', {})
        
        if not cloud_credentials:
            return {'success': False, 'errors': ['No cloud credentials configured']}
        
        baseline_counts = {'aws_count': 0, 'gcp_count': 0, 'azure_count': 0}
        clouds_processed = []
        errors = []
        
        # Process each cloud provider
        for cloud in ['aws', 'gcp', 'azure']:
            if cloud in cloud_credentials:
                try:
                    logger.info(f"Starting baseline collection for {cloud.upper()}")
                    cloud_counts = collect_cloud_resources(user_email, cloud, cloud_credentials[cloud])
                    baseline_counts[f'{cloud}_count'] = cloud_counts
                    clouds_processed.append(cloud.upper())
                    logger.info(f"Completed baseline collection for {cloud.upper()}: {cloud_counts} resources")
                except Exception as e:
                    error_msg = f"Failed to collect {cloud.upper()} resources: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        
        # Update baseline summary
        update_baseline_summary(user_email, baseline_counts)
        
        return {
            'success': True,
            'counts': baseline_counts,
            'clouds_processed': clouds_processed,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Error during baseline collection: {str(e)}")
        return {'success': False, 'errors': [f'Baseline collection failed: {str(e)}']}

def collect_cloud_resources(user_email, cloud, credentials):
    """Collect resources from a specific cloud provider"""
    if cloud == 'aws':
        return collect_aws_resources(user_email, credentials)
    elif cloud == 'gcp':
        return collect_gcp_resources(user_email, credentials)
    elif cloud == 'azure':
        return collect_azure_resources(user_email, credentials)
    else:
        raise ValueError(f"Unsupported cloud provider: {cloud}")

def collect_aws_resources(user_email, credentials):
    """Collect AWS resources (EC2, S3, RDS)"""
    try:
        # Initialize AWS clients
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        s3_client = boto3.client('s3')
        rds_client = boto3.client('rds', region_name='us-east-1')
        
        resource_count = 0
        
        # Collect EC2 instances
        try:
            ec2_response = ec2_client.describe_instances()
            for reservation in ec2_response['Reservations']:
                for instance in reservation['Instances']:
                    if instance['State']['Name'] != 'terminated':
                        config = canonicalize_aws_ec2_config(instance)
                        create_snapshot(
                            user_email, 'AWS', 'EC2', instance['InstanceId'],
                            get_instance_name(instance), config,
                            {'environment': 'production', 'region': 'us-east-1'}
                        )
                        resource_count += 1
        except Exception as e:
            logger.warning(f"Failed to collect EC2 instances: {e}")
        
        # Collect S3 buckets
        try:
            s3_response = s3_client.list_buckets()
            for bucket in s3_response['Buckets']:
                config = canonicalize_aws_s3_config(bucket)
                create_snapshot(
                    user_email, 'AWS', 'S3', bucket['Name'],
                    bucket['Name'], config,
                    {'environment': 'production', 'region': 'us-east-1'}
                )
                resource_count += 1
        except Exception as e:
            logger.warning(f"Failed to collect S3 buckets: {e}")
        
        # Collect RDS instances
        try:
            rds_response = rds_client.describe_db_instances()
            for db_instance in rds_response['DBInstances']:
                config = canonicalize_aws_rds_config(db_instance)
                create_snapshot(
                    user_email, 'AWS', 'RDS', db_instance['DBInstanceIdentifier'],
                    db_instance['DBInstanceIdentifier'], config,
                    {'environment': 'production', 'region': 'us-east-1'}
                )
                resource_count += 1
        except Exception as e:
            logger.warning(f"Failed to collect RDS instances: {e}")
        
        return resource_count
        
    except Exception as e:
        logger.error(f"Error collecting AWS resources: {e}")
        raise e

def collect_gcp_resources(user_email, credentials):
    """Collect GCP resources (Compute Engine VMs, Storage buckets)"""
    try:
        # For demo purposes, create simulated GCP resources
        # In production, use google-cloud SDKs
        gcp_resources = [
            {
                'type': 'VM',
                'id': 'gcp-vm-1',
                'name': 'web-server-gcp',
                'config': {'machine_type': 'e2-medium', 'zone': 'us-central1-a', 'status': 'running'}
            },
            {
                'type': 'StorageBucket',
                'id': 'gcp-bucket-1',
                'name': 'my-gcp-bucket',
                'config': {'location': 'US', 'storage_class': 'STANDARD', 'status': 'active'}
            }
        ]
        
        resource_count = 0
        for resource in gcp_resources:
            config = canonicalize_gcp_config(resource['config'])
            create_snapshot(
                user_email, 'GCP', resource['type'], resource['id'],
                resource['name'], config,
                {'environment': 'production', 'zone': 'us-central1-a'}
            )
            resource_count += 1
        
        return resource_count
        
    except Exception as e:
        logger.error(f"Error collecting GCP resources: {e}")
        raise e

def collect_azure_resources(user_email, credentials):
    """Collect Azure resources (Resource Groups, VMs, Storage Accounts)"""
    try:
        # For demo purposes, create simulated Azure resources
        # In production, use azure-identity + azure-mgmt SDKs
        azure_resources = [
            {
                'type': 'ResourceGroup',
                'id': 'rg-1',
                'name': 'my-resource-group',
                'config': {'location': 'East US', 'status': 'active'}
            },
            {
                'type': 'VM',
                'id': 'azure-vm-1',
                'name': 'web-server-azure',
                'config': {'vm_size': 'Standard_B1s', 'location': 'East US', 'status': 'running'}
            },
            {
                'type': 'StorageAccount',
                'id': 'storage-1',
                'name': 'mystorageaccount',
                'config': {'location': 'East US', 'sku': 'Standard_LRS', 'status': 'active'}
            }
        ]
        
        resource_count = 0
        for resource in azure_resources:
            config = canonicalize_azure_config(resource['config'])
            create_snapshot(
                user_email, 'AZURE', resource['type'], resource['id'],
                resource['name'], config,
                {'environment': 'production', 'location': 'East US'}
            )
            resource_count += 1
        
        return resource_count
        
    except Exception as e:
        logger.error(f"Error collecting Azure resources: {e}")
        raise e

def canonicalize_aws_ec2_config(instance):
    """Canonicalize AWS EC2 instance configuration"""
    return {
        'instance_type': instance.get('InstanceType'),
        'state': instance.get('State', {}).get('Name'),
        'image_id': instance.get('ImageId'),
        'vpc_id': instance.get('VpcId'),
        'subnet_id': instance.get('SubnetId'),
        'security_groups': [sg['GroupId'] for sg in instance.get('SecurityGroups', [])],
        'key_name': instance.get('KeyName'),
        'launch_time': instance.get('LaunchTime', '').isoformat() if instance.get('LaunchTime') else None
    }

def canonicalize_aws_s3_config(bucket):
    """Canonicalize AWS S3 bucket configuration"""
    return {
        'name': bucket.get('Name'),
        'creation_date': bucket.get('CreationDate', '').isoformat() if bucket.get('CreationDate') else None,
        'region': 'us-east-1'  # Default region for S3
    }

def canonicalize_aws_rds_config(db_instance):
    """Canonicalize AWS RDS instance configuration"""
    return {
        'db_instance_class': db_instance.get('DBInstanceClass'),
        'engine': db_instance.get('Engine'),
        'engine_version': db_instance.get('EngineVersion'),
        'db_instance_status': db_instance.get('DBInstanceStatus'),
        'allocated_storage': db_instance.get('AllocatedStorage'),
        'storage_type': db_instance.get('StorageType'),
        'vpc_id': db_instance.get('DBSubnetGroup', {}).get('VpcId'),
        'availability_zone': db_instance.get('AvailabilityZone')
    }

def canonicalize_gcp_config(config):
    """Canonicalize GCP resource configuration"""
    return {
        'status': config.get('status'),
        'location': config.get('location') or config.get('zone'),
        'machine_type': config.get('machine_type'),
        'storage_class': config.get('storage_class')
    }

def canonicalize_azure_config(config):
    """Canonicalize Azure resource configuration"""
    return {
        'status': config.get('status'),
        'location': config.get('location'),
        'vm_size': config.get('vm_size'),
        'sku': config.get('sku')
    }

def get_instance_name(instance):
    """Get instance name from tags or use instance ID"""
    for tag in instance.get('Tags', []):
        if tag['Key'] == 'Name':
            return tag['Value']
    return instance['InstanceId']

# =============================================================================
# DRIFT DETECTION FUNCTIONS
# =============================================================================

def start_drift_detection(user_email):
    """Start periodic drift detection for a user"""
    try:
        # Update detection status
        table.update_item(
            Key={'email': user_email},
            UpdateExpression='SET detection_status = :ds, updated_at = :ua',
            ExpressionAttributeValues={
                ':ds': 'Running',
                ':ua': str(int(time.time()))
            }
        )
        
        # Add job to scheduler if not already exists
        job_id = f'drift_detection_{user_email}'
        if not scheduler.get_job(job_id):
            scheduler.add_job(
                func=run_drift_detection,
                trigger=IntervalTrigger(minutes=DRIFT_CHECK_INTERVAL),
                args=[user_email],
                id=job_id,
                replace_existing=True
            )
            logger.info(f"Started drift detection for user: {user_email}")
        
        return True
    except Exception as e:
        logger.error(f"Error starting drift detection: {str(e)}")
        return False

def stop_drift_detection(user_email):
    """Stop periodic drift detection for a user"""
    try:
        # Update detection status
        table.update_item(
            Key={'email': user_email},
            UpdateExpression='SET detection_status = :ds, updated_at = :ua',
            ExpressionAttributeValues={
                ':ds': 'Stopped',
                ':ua': str(int(time.time()))
            }
        )
        
        # Remove job from scheduler
        job_id = f'drift_detection_{user_email}'
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"Stopped drift detection for user: {user_email}")
        
        return True
    except Exception as e:
        logger.error(f"Error stopping drift detection: {str(e)}")
        return False

def run_drift_detection(user_email):
    """Run drift detection for a specific user"""
    try:
        logger.info(f"Running drift detection for user: {user_email}")
        
        # Get user's cloud credentials
        response = table.get_item(Key={'email': user_email})
        if 'Item' not in response:
            logger.error(f"User not found: {user_email}")
            return
        
        user_data = response['Item']
        cloud_credentials = user_data.get('cloud_credentials', {})
        
        if not cloud_credentials:
            logger.warning(f"No cloud credentials found for user: {user_email}")
            return
        
        # Get baseline snapshots
        baseline_snapshots = get_baseline_snapshots(user_email)
        
        # Collect current resources
        current_resources = {}
        clouds_processed = []
        
        # AWS
        if 'aws' in cloud_credentials:
            try:
                aws_resources = collect_aws_current(cloud_credentials['aws'])
                current_resources['aws'] = aws_resources
                clouds_processed.append('AWS')
            except Exception as e:
                logger.error(f"Error collecting AWS resources: {e}")
        
        # GCP
        if 'gcp' in cloud_credentials:
            try:
                gcp_resources = collect_gcp_current(cloud_credentials['gcp'])
                current_resources['gcp'] = gcp_resources
                clouds_processed.append('GCP')
            except Exception as e:
                logger.error(f"Error collecting GCP resources: {e}")
        
        # Azure
        if 'azure' in cloud_credentials:
            try:
                azure_resources = collect_azure_current(cloud_credentials['azure'])
                current_resources['azure'] = azure_resources
                clouds_processed.append('AZURE')
            except Exception as e:
                logger.error(f"Error collecting Azure resources: {e}")
        
        # Compare with baseline and detect drift
        drift_summary = compare_with_baseline(baseline_snapshots, current_resources)
        
        # Build and store a postmortem-style incident record for this run, even if
        # no drift was found, so there's a complete audit trail to review later.
        incident_record = build_incident_record(user_email, drift_summary)
        save_incident(incident_record)
        
        # Update dashboard with drift status
        update_dashboard(user_email, drift_summary, 'Running')
        
        # Send email notification if drift detected
        if drift_summary['total_drifts'] > 0:
            send_ses_notification(
                SES_SENDER_EMAIL,
                SES_RECEIVER_EMAIL,
                drift_summary,
                executive_summary=incident_record['executive_summary']
            )
        
        logger.info(f"Drift detection completed for {user_email}: {drift_summary['total_drifts']} drifts detected")
        
    except Exception as e:
        logger.error(f"Error in drift detection: {str(e)}")

def get_baseline_snapshots(user_email):
    """Get baseline snapshots for a user"""
    try:
        response = snapshots_table.query(
            KeyConditionExpression='user_email = :ue',
            ExpressionAttributeValues={':ue': user_email}
        )
        
        snapshots = {}
        for item in response['Items']:
            cloud = item.get('cloud', '').lower()
            if cloud not in snapshots:
                snapshots[cloud] = {}
            
            resource_key = item.get('snapshot_id', '')
            snapshots[cloud][resource_key] = {
                'config': item.get('config', '{}'),
                'config_hash': item.get('config_hash', ''),
                'resource_type': item.get('resource_type', ''),
                'resource_id': item.get('resource_id', ''),
                'resource_name': item.get('resource_name', '')
            }
        
        return snapshots
    except Exception as e:
        logger.error(f"Error getting baseline snapshots: {str(e)}")
        return {}

def collect_aws_current(credentials):
    """Collect current AWS resources"""
    try:
        # Initialize AWS clients
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        s3_client = boto3.client('s3')
        rds_client = boto3.client('rds', region_name='us-east-1')
        
        resources = {}
        
        # Collect EC2 instances
        try:
            ec2_response = ec2_client.describe_instances()
            for reservation in ec2_response['Reservations']:
                for instance in reservation['Instances']:
                    if instance['State']['Name'] != 'terminated':
                        resource_key = f"AWS#EC2#{instance['InstanceId']}"
                        config = canonicalize_aws_ec2_config(instance)
                        config_json = json.dumps(config, sort_keys=True)
                        config_hash = hashlib.sha256(config_json.encode()).hexdigest()
                        
                        resources[resource_key] = {
                            'config': config_json,
                            'config_hash': config_hash,
                            'resource_type': 'EC2',
                            'resource_id': instance['InstanceId'],
                            'resource_name': get_instance_name(instance)
                        }
        except Exception as e:
            logger.warning(f"Failed to collect EC2 instances: {e}")
        
        # Collect S3 buckets
        try:
            s3_response = s3_client.list_buckets()
            for bucket in s3_response['Buckets']:
                resource_key = f"AWS#S3#{bucket['Name']}"
                config = canonicalize_aws_s3_config(bucket)
                config_json = json.dumps(config, sort_keys=True)
                config_hash = hashlib.sha256(config_json.encode()).hexdigest()
                
                resources[resource_key] = {
                    'config': config_json,
                    'config_hash': config_hash,
                    'resource_type': 'S3',
                    'resource_id': bucket['Name'],
                    'resource_name': bucket['Name']
                }
        except Exception as e:
            logger.warning(f"Failed to collect S3 buckets: {e}")
        
        # Collect RDS instances
        try:
            rds_response = rds_client.describe_db_instances()
            for db_instance in rds_response['DBInstances']:
                resource_key = f"AWS#RDS#{db_instance['DBInstanceIdentifier']}"
                config = canonicalize_aws_rds_config(db_instance)
                config_json = json.dumps(config, sort_keys=True)
                config_hash = hashlib.sha256(config_json.encode()).hexdigest()
                
                resources[resource_key] = {
                    'config': config_json,
                    'config_hash': config_hash,
                    'resource_type': 'RDS',
                    'resource_id': db_instance['DBInstanceIdentifier'],
                    'resource_name': db_instance['DBInstanceIdentifier']
                }
        except Exception as e:
            logger.warning(f"Failed to collect RDS instances: {e}")
        
        return resources
        
    except Exception as e:
        logger.error(f"Error collecting AWS resources: {e}")
        return {}

def collect_gcp_current(credentials):
    """Collect current GCP resources"""
    try:
        # For demo purposes, simulate GCP resources
        # In production, use google-cloud SDKs
        resources = {}
        
        gcp_resources = [
            {
                'type': 'VM',
                'id': 'gcp-vm-1',
                'name': 'web-server-gcp',
                'config': {'machine_type': 'e2-medium', 'zone': 'us-central1-a', 'status': 'running'}
            },
            {
                'type': 'StorageBucket',
                'id': 'gcp-bucket-1',
                'name': 'my-gcp-bucket',
                'config': {'location': 'US', 'storage_class': 'STANDARD', 'status': 'active'}
            }
        ]
        
        for resource in gcp_resources:
            resource_key = f"GCP#{resource['type']}#{resource['id']}"
            config = canonicalize_gcp_config(resource['config'])
            config_json = json.dumps(config, sort_keys=True)
            config_hash = hashlib.sha256(config_json.encode()).hexdigest()
            
            resources[resource_key] = {
                'config': config_json,
                'config_hash': config_hash,
                'resource_type': resource['type'],
                'resource_id': resource['id'],
                'resource_name': resource['name']
            }
        
        return resources
        
    except Exception as e:
        logger.error(f"Error collecting GCP resources: {e}")
        return {}

def collect_azure_current(credentials):
    """Collect current Azure resources"""
    try:
        # For demo purposes, simulate Azure resources
        # In production, use azure-identity + azure-mgmt SDKs
        resources = {}
        
        azure_resources = [
            {
                'type': 'ResourceGroup',
                'id': 'rg-1',
                'name': 'my-resource-group',
                'config': {'location': 'East US', 'status': 'active'}
            },
            {
                'type': 'VM',
                'id': 'azure-vm-1',
                'name': 'web-server-azure',
                'config': {'vm_size': 'Standard_B1s', 'location': 'East US', 'status': 'running'}
            },
            {
                'type': 'StorageAccount',
                'id': 'storage-1',
                'name': 'mystorageaccount',
                'config': {'location': 'East US', 'sku': 'Standard_LRS', 'status': 'active'}
            }
        ]
        
        for resource in azure_resources:
            resource_key = f"AZURE#{resource['type']}#{resource['id']}"
            config = canonicalize_azure_config(resource['config'])
            config_json = json.dumps(config, sort_keys=True)
            config_hash = hashlib.sha256(config_json.encode()).hexdigest()
            
            resources[resource_key] = {
                'config': config_json,
                'config_hash': config_hash,
                'resource_type': resource['type'],
                'resource_id': resource['id'],
                'resource_name': resource['name']
            }
        
        return resources
        
    except Exception as e:
        logger.error(f"Error collecting Azure resources: {e}")
        return {}

# =============================================================================
# DRIFT DIAGNOSTICS: FIELD-LEVEL DIFFING, SEVERITY, ROOT CAUSE
# =============================================================================

# Relative ranking used to pick the "worst" severity when a resource has
# multiple field-level changes in a single drift event.
SEVERITY_ORDER = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'CRITICAL': 3}

# Maps a canonical config field name to (severity, likely_cause, recommended_action).
# This is the rule table an on-call engineer would use to triage a drift without
# having to inspect the raw resource manually.
FIELD_SEVERITY_RULES = {
    'security_groups': (
        'CRITICAL',
        "The security group(s) attached to this resource changed, which can widen or "
        "restrict network access.",
        "Diff the security group's ingress/egress rules against the baseline and revert "
        "any unauthorized changes immediately."
    ),
    'key_name': (
        'CRITICAL',
        "The SSH key pair associated with the instance changed, affecting who can log in to it.",
        "Confirm the key change was authorized. If not, rotate access and investigate how it happened."
    ),
    'image_id': (
        'HIGH',
        "The base image (AMI) backing the instance changed.",
        "Confirm the new image is from an approved, trusted source before allowing it to remain."
    ),
    'state': (
        'HIGH',
        "The resource's runtime state changed (e.g. stopped/terminated), which can indicate "
        "an outage or an unplanned shutdown.",
        "Confirm whether this was planned maintenance. If not, investigate who/what changed the "
        "state and restart the resource if required."
    ),
    'status': (
        'HIGH',
        "The resource's status changed, which can indicate an outage or an unplanned change.",
        "Confirm whether this was planned. If not, investigate the cause and restore service."
    ),
    'db_instance_status': (
        'HIGH',
        "The database instance status changed, which can indicate a database outage.",
        "Check database availability immediately and confirm whether the change was planned."
    ),
    'vpc_id': (
        'HIGH',
        "The resource's VPC (network placement) changed.",
        "Confirm the resource is still in the intended network segment; re-associate it if this was unintended."
    ),
    'subnet_id': (
        'MEDIUM',
        "The resource's subnet changed, which can affect network routing and reachability.",
        "Confirm the new subnet still meets connectivity and security requirements."
    ),
    'instance_type': (
        'MEDIUM',
        "Compute sizing (instance type) changed, which affects cost and performance.",
        "Confirm this resize was intentional; revert if it was not requested."
    ),
    'db_instance_class': (
        'MEDIUM',
        "Database instance sizing changed, which affects cost and performance.",
        "Confirm this resize was intentional; revert if it was not requested."
    ),
    'machine_type': (
        'MEDIUM',
        "Compute sizing (machine type) changed, which affects cost and performance.",
        "Confirm this resize was intentional; revert if it was not requested."
    ),
    'vm_size': (
        'MEDIUM',
        "VM sizing changed, which affects cost and performance.",
        "Confirm this resize was intentional; revert if it was not requested."
    ),
    'engine_version': (
        'MEDIUM',
        "The database engine version changed.",
        "Validate application compatibility and confirm this was a planned upgrade."
    ),
    'allocated_storage': (
        'MEDIUM',
        "Allocated storage capacity changed.",
        "Confirm this was an intentional resize; unexpected shrinkage can risk data loss."
    ),
    'storage_type': (
        'MEDIUM',
        "The underlying storage type changed, which can affect performance and cost.",
        "Confirm this change was intentional and still meets performance requirements."
    ),
    'sku': (
        'MEDIUM',
        "The resource's SKU/tier changed, which affects cost and available features.",
        "Confirm this change was intentional."
    ),
    'region': (
        'MEDIUM',
        "The resource's region changed.",
        "Confirm this reflects an intentional migration; unexpected region changes can affect "
        "latency, cost, and data residency compliance."
    ),
    'location': (
        'MEDIUM',
        "The resource's location changed.",
        "Confirm this reflects an intentional migration; unexpected location changes can affect "
        "latency, cost, and data residency compliance."
    ),
    'availability_zone': (
        'LOW',
        "The resource's availability zone changed.",
        "Usually low risk; confirm it doesn't break any zone-pinned dependencies."
    ),
    'storage_class': (
        'LOW',
        "The storage class changed, which affects cost and retrieval performance.",
        "Confirm the new class still meets access-pattern requirements."
    ),
    'name': (
        'LOW',
        "The resource's display name changed.",
        "Usually cosmetic; confirm it still matches your naming convention."
    ),
}

# Default treatment for fields not explicitly covered above.
DEFAULT_FIELD_SEVERITY = 'MEDIUM'
DEFAULT_FIELD_CAUSE = "This field changed from its baseline value."
DEFAULT_FIELD_ACTION = "Review whether this change was intentional and refresh the baseline if approved."

# Resource types that should always be treated as high-severity when newly
# discovered, since they typically control access or expose data.
SENSITIVE_NEW_RESOURCE_TYPES = {'SECURITYGROUP', 'IAMROLE', 'STORAGEACCOUNT', 'S3'}


def compute_field_diff(old_config, new_config):
    """
    Compute a field-level diff between two canonical config JSON strings (or dicts).
    Returns a list of {field, old_value, new_value, change} entries, where change is
    one of 'added', 'removed', or 'modified'. This is what lets a drift alert say
    exactly *what* changed instead of just *that* something changed.
    """
    try:
        old_dict = json.loads(old_config) if isinstance(old_config, str) else (old_config or {})
    except (json.JSONDecodeError, TypeError):
        old_dict = {}
    try:
        new_dict = json.loads(new_config) if isinstance(new_config, str) else (new_config or {})
    except (json.JSONDecodeError, TypeError):
        new_dict = {}

    if not isinstance(old_dict, dict):
        old_dict = {}
    if not isinstance(new_dict, dict):
        new_dict = {}

    diffs = []
    for field in sorted(set(old_dict.keys()) | set(new_dict.keys())):
        old_value = old_dict.get(field)
        new_value = new_dict.get(field)

        if old_value == new_value:
            continue

        if field not in old_dict:
            change = 'added'
        elif field not in new_dict:
            change = 'removed'
        else:
            change = 'modified'

        diffs.append({
            'field': field,
            'old_value': old_value,
            'new_value': new_value,
            'change': change
        })

    return diffs


def classify_drift_severity(drift):
    """
    Classify a drift dict into 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' severity.
    For field_change drifts, severity is the worst severity among the individual
    field-level changes. Other drift types use fixed risk-based defaults.
    """
    drift_type = drift.get('type')

    if drift_type == 'field_change':
        field_diff = drift.get('field_diff') or []
        if not field_diff:
            return DEFAULT_FIELD_SEVERITY

        worst = 'LOW'
        for entry in field_diff:
            rule = FIELD_SEVERITY_RULES.get(entry.get('field'))
            severity = rule[0] if rule else DEFAULT_FIELD_SEVERITY
            if SEVERITY_ORDER[severity] > SEVERITY_ORDER[worst]:
                worst = severity
        return worst

    if drift_type == 'new_resource':
        resource_type = (drift.get('resource_type') or '').upper()
        return 'HIGH' if resource_type in SENSITIVE_NEW_RESOURCE_TYPES else 'MEDIUM'

    if drift_type == 'deleted_resource':
        # A resource disappearing from a cloud is always worth immediate attention -
        # it may be an outage or an unauthorized deletion.
        return 'HIGH'

    if drift_type == 's3_parity':
        # Same bucket name, different configuration across clouds is a governance
        # and potential data-exposure risk.
        return 'HIGH'

    return DEFAULT_FIELD_SEVERITY


def suggest_root_cause_and_fix(drift):
    """
    Return a (likely_cause, recommended_action) tuple in plain English for a drift,
    written the way a support engineer would document it in an incident/postmortem.
    """
    drift_type = drift.get('type')

    if drift_type == 'field_change':
        field_diff = drift.get('field_diff') or []
        if not field_diff:
            return (
                "The configuration hash changed but the specific fields could not be "
                "determined from the stored snapshot.",
                "Re-run baseline collection and compare the resource manually."
            )

        # Explain using the single field with the highest severity, since that's
        # the one that actually drives the overall severity rating.
        worst_entry = None
        worst_severity = 'LOW'
        for entry in field_diff:
            rule = FIELD_SEVERITY_RULES.get(entry.get('field'))
            severity = rule[0] if rule else DEFAULT_FIELD_SEVERITY
            if worst_entry is None or SEVERITY_ORDER[severity] >= SEVERITY_ORDER[worst_severity]:
                worst_severity = severity
                worst_entry = entry

        rule = FIELD_SEVERITY_RULES.get(worst_entry.get('field'))
        if rule:
            cause, action = rule[1], rule[2]
        else:
            cause = (
                f"The '{worst_entry.get('field')}' field changed from "
                f"'{worst_entry.get('old_value')}' to '{worst_entry.get('new_value')}'."
            )
            action = DEFAULT_FIELD_ACTION

        if len(field_diff) > 1:
            cause += f" ({len(field_diff)} fields changed in total.)"

        return cause, action

    if drift_type == 'new_resource':
        return (
            "A new, previously unseen resource was detected that is not part of the baseline.",
            "Confirm this resource was provisioned intentionally (e.g. via IaC or an approved "
            "console action), then re-run baseline collection to include it if approved."
        )

    if drift_type == 'deleted_resource':
        return (
            "A previously baselined resource is no longer present, which may indicate an "
            "outage or an unauthorized deletion.",
            "Confirm whether the deletion was intentional. If not, restore the resource from "
            "backups/IaC and audit who removed it."
        )

    if drift_type == 's3_parity':
        return (
            "Two clouds have a storage bucket with the same name but different "
            "configurations, risking accidental data exposure or a governance gap.",
            "Reconcile the conflicting configurations or rename one bucket so naming and "
            "policy stay consistent across clouds."
        )

    return ("Unclassified change detected.", "Review this drift manually.")


def enrich_drift_with_diagnostics(drift):
    """Attach severity, likely_cause, and recommended_action to a drift dict in place."""
    drift['severity'] = classify_drift_severity(drift)
    likely_cause, recommended_action = suggest_root_cause_and_fix(drift)
    drift['likely_cause'] = likely_cause
    drift['recommended_action'] = recommended_action
    return drift


def build_incident_record(user_email, drift_summary):
    """
    Build a postmortem-style incident record from a drift_summary produced by
    compare_with_baseline(). This is the audit trail an SRE would file after
    triaging a drift check, and is stored on every run - even clean ones - so
    there's a complete history to review.
    """
    severity_breakdown = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    all_drifts = list(drift_summary.get('drifts_detected', [])) + list(drift_summary.get('s3_parity_drifts', []))

    for drift in all_drifts:
        severity = drift.get('severity', DEFAULT_FIELD_SEVERITY)
        severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1

    total_drifts = drift_summary.get('total_drifts', 0) + drift_summary.get('total_s3_parity_drifts', 0)
    clouds_checked = drift_summary.get('clouds_checked', [])
    clouds_label = ', '.join(clouds_checked) if clouds_checked else 'configured clouds'

    if total_drifts == 0:
        executive_summary = f"No drift detected across {clouds_label}."
    else:
        breakdown_parts = [f"{count} {severity}" for severity, count in severity_breakdown.items() if count > 0]
        executive_summary = (
            f"{total_drifts} drift(s) detected across {clouds_label}: {', '.join(breakdown_parts)}."
        )

    incident_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"

    return {
        'user_email': user_email,
        'incident_id': incident_id,
        'timestamp': drift_summary.get('timestamp', datetime.now().isoformat()),
        'total_drifts': total_drifts,
        'severity_breakdown': severity_breakdown,
        'clouds_checked': clouds_checked,
        'executive_summary': executive_summary,
        'drifts': all_drifts,
        'created_at': int(time.time())
    }


def save_incident(incident_record):
    """Persist an incident/postmortem record to the Incidents table."""
    try:
        incidents_table.put_item(Item=incident_record)
        logger.info(f"Saved incident {incident_record['incident_id']} for {incident_record['user_email']}")
        return True
    except Exception as e:
        logger.error(f"Error saving incident record: {str(e)}")
        return False


def get_incident_history(user_email, limit=20):
    """Return the most recent incident/postmortem records for a user."""
    try:
        response = incidents_table.query(
            KeyConditionExpression='user_email = :ue',
            ExpressionAttributeValues={':ue': user_email},
            ScanIndexForward=False,  # incident_id starts with an epoch timestamp, so this gives newest-first
            Limit=limit
        )
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Error getting incident history: {str(e)}")
        return []


def get_incident_detail(user_email, incident_id):
    """Fetch a single incident/postmortem record by ID."""
    try:
        response = incidents_table.get_item(Key={'user_email': user_email, 'incident_id': incident_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error getting incident detail: {str(e)}")
        return None


# =============================================================================
# DEMO WALKTHROUGH: SCRIPTED DRIFT SCENARIOS FOR RELIABLE, OFFLINE-SAFE DEMOS
# =============================================================================
# These functions build synthetic baseline/current resource sets in exactly the
# same shape that get_baseline_snapshots()/collect_*_current() produce, then run
# them through the real compare_with_baseline() -> diagnostics -> incident
# pipeline. Nothing here is faked at the drift-detection layer - only the
# input resources are scripted, so a demo behaves identically to a real run
# without depending on live cloud credentials or network access.

DEMO_SCENARIO_LABELS = {
    'critical': 'Security Group Widened (CRITICAL)',
    'high': 'Instance Deleted (HIGH)',
    'medium': 'Instance Resized (MEDIUM)',
    'clean': 'Clean Run (No Drift)'
}


def _demo_resource(resource_type, resource_id, resource_name, config_dict):
    """Build a resource entry in the same shape used by the real collectors."""
    config_json = json.dumps(config_dict, sort_keys=True)
    config_hash = hashlib.sha256(config_json.encode()).hexdigest()
    return {
        'config': config_json,
        'config_hash': config_hash,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'resource_name': resource_name
    }


def _update_demo_resource_config(entry, new_config_dict):
    """Mutate a demo resource entry's config in place and recompute its hash."""
    config_json = json.dumps(new_config_dict, sort_keys=True)
    entry['config'] = config_json
    entry['config_hash'] = hashlib.sha256(config_json.encode()).hexdigest()


def _get_demo_fleet_baseline():
    """
    A small, realistic multi-cloud 'fleet' used as the baseline for every demo
    scenario. Most resources stay identical between baseline and current so a
    demo run looks like a real environment check, not a single isolated diff.
    """
    return {
        'aws': {
            'AWS#EC2#i-demo-101': _demo_resource('EC2', 'i-demo-101', 'checkout-api', {
                'instance_type': 't3.medium',
                'state': 'running',
                'security_groups': ['sg-demo-safe'],
                'image_id': 'ami-demo-001'
            }),
            'AWS#EC2#i-demo-102': _demo_resource('EC2', 'i-demo-102', 'payments-worker', {
                'instance_type': 't3.small',
                'state': 'running',
                'security_groups': ['sg-demo-safe'],
                'image_id': 'ami-demo-002'
            })
        },
        'gcp': {
            'GCP#VM#demo-vm-201': _demo_resource('VM', 'demo-vm-201', 'analytics-batch', {
                'machine_type': 'e2-small',
                'zone': 'us-central1-a',
                'status': 'running'
            })
        },
        'azure': {
            'AZURE#VM#azure-vm-demo-1': _demo_resource('VM', 'azure-vm-demo-1', 'auth-service', {
                'vm_size': 'Standard_B1s',
                'location': 'East US',
                'status': 'running'
            })
        }
    }


def get_demo_scenario_data(scenario):
    """
    Return (baseline_snapshots, current_resources) for a named demo scenario.
    Both are deep copies of the same fleet baseline, so only the scripted
    change for that scenario differs between the two.
    """
    if scenario not in DEMO_SCENARIO_LABELS:
        raise ValueError(f"Unknown demo scenario: {scenario}")

    baseline = copy.deepcopy(_get_demo_fleet_baseline())
    current = copy.deepcopy(_get_demo_fleet_baseline())

    if scenario == 'critical':
        entry = current['aws']['AWS#EC2#i-demo-101']
        cfg = json.loads(entry['config'])
        cfg['security_groups'] = cfg['security_groups'] + ['sg-demo-open-all']
        _update_demo_resource_config(entry, cfg)

    elif scenario == 'high':
        del current['aws']['AWS#EC2#i-demo-102']

    elif scenario == 'medium':
        entry = current['azure']['AZURE#VM#azure-vm-demo-1']
        cfg = json.loads(entry['config'])
        cfg['vm_size'] = 'Standard_D2s_v3'
        _update_demo_resource_config(entry, cfg)

    # 'clean' scenario intentionally makes no changes.

    return baseline, current


# =============================================================================
# RELIABILITY SCORECARD
# =============================================================================

def get_reliability_scorecard(user_email, history_limit=50):
    """
    Compute a lightweight reliability scorecard purely from stored incident
    records - no new data pipeline required. Summarizes check volume, how
    often checks come back clean, and the all-time severity distribution.
    """
    incidents = get_incident_history(user_email, limit=history_limit)

    total_checks = len(incidents)
    clean_runs = sum(1 for incident in incidents if incident.get('total_drifts', 0) == 0)
    clean_run_rate = round((clean_runs / total_checks) * 100, 1) if total_checks else 0.0

    severity_totals = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for incident in incidents:
        breakdown = incident.get('severity_breakdown', {}) or {}
        for severity in severity_totals:
            severity_totals[severity] += breakdown.get(severity, 0)

    last_check = incidents[0].get('timestamp') if incidents else None

    return {
        'total_checks': total_checks,
        'clean_runs': clean_runs,
        'clean_run_rate': clean_run_rate,
        'severity_totals': severity_totals,
        'last_check': last_check
    }


def compare_with_baseline(baseline_snapshots, current_resources):
    """Compare current resources with baseline and detect drift"""
    drift_summary = {
        'timestamp': datetime.now().isoformat(),
        'drifts_detected': [],
        'total_drifts': 0,
        'clouds_checked': list(current_resources.keys())
    }
    
    try:
        # Check for field changes
        for cloud, resources in current_resources.items():
            baseline_cloud = baseline_snapshots.get(cloud, {})
            
            for resource_key, current_resource in resources.items():
                baseline_resource = baseline_cloud.get(resource_key)
                
                if baseline_resource:
                    # Resource exists in baseline, check for changes
                    if current_resource['config_hash'] != baseline_resource['config_hash']:
                        drift = {
                            'type': 'field_change',
                            'cloud': cloud.upper(),
                            'resource_type': current_resource['resource_type'],
                            'resource_id': current_resource['resource_id'],
                            'resource_name': current_resource['resource_name'],
                            'change_type': 'Configuration modified',
                            'timestamp': drift_summary['timestamp'],
                            'field_diff': compute_field_diff(
                                baseline_resource.get('config', '{}'),
                                current_resource.get('config', '{}')
                            )
                        }
                        enrich_drift_with_diagnostics(drift)
                        drift_summary['drifts_detected'].append(drift)
                        drift_summary['total_drifts'] += 1
                else:
                    # New resource detected
                    drift = {
                        'type': 'new_resource',
                        'cloud': cloud.upper(),
                        'resource_type': current_resource['resource_type'],
                        'resource_id': current_resource['resource_id'],
                        'resource_name': current_resource['resource_name'],
                        'change_type': 'New resource created',
                        'timestamp': drift_summary['timestamp']
                    }
                    enrich_drift_with_diagnostics(drift)
                    drift_summary['drifts_detected'].append(drift)
                    drift_summary['total_drifts'] += 1
        
        # Check for deleted resources
        for cloud, baseline_cloud in baseline_snapshots.items():
            current_cloud = current_resources.get(cloud, {})
            
            for resource_key, baseline_resource in baseline_cloud.items():
                if resource_key not in current_cloud:
                    drift = {
                        'type': 'deleted_resource',
                        'cloud': cloud.upper(),
                        'resource_type': baseline_resource['resource_type'],
                        'resource_id': baseline_resource['resource_id'],
                        'resource_name': baseline_resource['resource_name'],
                        'change_type': 'Resource deleted',
                        'timestamp': drift_summary['timestamp']
                    }
                    enrich_drift_with_diagnostics(drift)
                    drift_summary['drifts_detected'].append(drift)
                    drift_summary['total_drifts'] += 1
        
        # Check for S3 cross-cloud parity
        drift_summary.update(check_s3_cross_cloud_parity(baseline_snapshots, current_resources))
        
        return drift_summary
        
    except Exception as e:
        logger.error(f"Error comparing with baseline: {str(e)}")
        return drift_summary

def check_s3_cross_cloud_parity(baseline_snapshots, current_resources):
    """Check for S3 cross-cloud parity issues"""
    s3_parity_drifts = []
    
    try:
        # Get S3/Storage buckets from all clouds
        s3_buckets = {}
        for cloud, resources in current_resources.items():
            for resource_key, resource in resources.items():
                if resource['resource_type'] in ['S3', 'StorageBucket', 'StorageAccount']:
                    bucket_name = resource['resource_name']
                    if bucket_name not in s3_buckets:
                        s3_buckets[bucket_name] = []
                    s3_buckets[bucket_name].append({
                        'cloud': cloud,
                        'resource': resource,
                        'resource_key': resource_key
                    })
        
        # Check for parity issues
        for bucket_name, cloud_resources in s3_buckets.items():
            if len(cloud_resources) > 1:
                # Same bucket name across multiple clouds
                config_hashes = [r['resource']['config_hash'] for r in cloud_resources]
                if len(set(config_hashes)) > 1:
                    # Different configurations for same bucket name
                    drift = {
                        'type': 's3_parity',
                        'bucket_name': bucket_name,
                        'clouds_affected': [r['cloud'].upper() for r in cloud_resources],
                        'change_type': 'S3 cross-cloud parity violation',
                        'timestamp': datetime.now().isoformat()
                    }
                    enrich_drift_with_diagnostics(drift)
                    s3_parity_drifts.append(drift)
        
        return {
            's3_parity_drifts': s3_parity_drifts,
            'total_s3_parity_drifts': len(s3_parity_drifts)
        }
        
    except Exception as e:
        logger.error(f"Error checking S3 cross-cloud parity: {str(e)}")
        return {'s3_parity_drifts': [], 'total_s3_parity_drifts': 0}

def send_ses_notification(sender, receiver, drift_summary, executive_summary=None):
    """Send SES email notification for drift detection"""
    try:
        # Initialize SES client
        ses_client = boto3.client('ses', region_name='eu-north-1')
        
        # Prepare email content
        subject = f"ConfigSync Drift Alert - {drift_summary['total_drifts']} Changes Detected"
        
        body = "\nConfigSync Dashboard - Drift Detection Alert\n\n"

        if executive_summary:
            body += f"Summary: {executive_summary}\n\n"

        body += f"""Timestamp: {drift_summary['timestamp']}
Total Drifts Detected: {drift_summary['total_drifts']}
Clouds Checked: {', '.join(drift_summary['clouds_checked'])}

DETAILED CHANGES:
"""
        
        for i, drift in enumerate(drift_summary['drifts_detected'], 1):
            body += f"""
{i}. [{drift.get('severity', 'MEDIUM')}] {drift['change_type']}
   Cloud: {drift['cloud']}
   Resource Type: {drift['resource_type']}
   Resource ID: {drift['resource_id']}
   Resource Name: {drift['resource_name']}
   Timestamp: {drift['timestamp']}"""

            if drift.get('likely_cause'):
                body += f"""
   Likely Cause: {drift['likely_cause']}
   Recommended Action: {drift.get('recommended_action', 'Review manually.')}"""
            
            # Add specific details for S3 versioning
            if drift.get('type') == 's3_versioning' and 'details' in drift:
                body += f"""
   Details: {drift['details']}"""
            
            body += "\n"
        
        # Add S3 parity drifts if any
        if drift_summary.get('s3_parity_drifts'):
            body += f"\nS3 CROSS-CLOUD PARITY VIOLATIONS:\n"
            for i, drift in enumerate(drift_summary['s3_parity_drifts'], 1):
                body += f"""
{i}. [{drift.get('severity', 'HIGH')}] {drift['change_type']}
   Bucket Name: {drift['bucket_name']}
   Clouds Affected: {', '.join(drift['clouds_affected'])}
   Timestamp: {drift['timestamp']}"""
                if drift.get('likely_cause'):
                    body += f"""
   Likely Cause: {drift['likely_cause']}
   Recommended Action: {drift.get('recommended_action', 'Review manually.')}"""
                body += "\n"
        
        body += f"""

Please review these changes, including the full field-level diffs and incident
history, in your ConfigSync Dashboard.

Best regards,
ConfigSync Monitoring System
"""
        
        # Send email
        response = ses_client.send_email(
            Source=sender,
            Destination={'ToAddresses': [receiver]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        
        logger.info(f"SES notification sent successfully. MessageId: {response['MessageId']}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending SES notification: {str(e)}")
        return False

def update_dashboard(user_email, drift_summary, detection_status):
    """Update dashboard with drift status"""
    try:
        table.update_item(
            Key={'email': user_email},
            UpdateExpression='SET drift_status = :ds, detection_status = :det, updated_at = :ua',
            ExpressionAttributeValues={
                ':ds': drift_summary,
                ':det': detection_status,
                ':ua': str(int(time.time()))
            }
        )
        logger.info(f"Updated dashboard for user {user_email}")
        return True
    except Exception as e:
        logger.error(f"Error updating dashboard: {str(e)}")
        return False

@app.route('/')
def index():
    """Redirect to login page"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        if validate_user_credentials(email, password):
            session['user_email'] = email
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user registration"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not email or not password or not confirm_password:
            flash('Please fill in all fields', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('signup.html')
        
        success, message = create_user(email, password)
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
            return render_template('signup.html')
    
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    """Display the main dashboard"""
    if 'user_email' not in session:
        flash('Please log in to access the dashboard', 'error')
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', user_email=session['user_email'])

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.pop('user_email', None)
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/cloud-credentials')
def cloud_credentials():
    """Display cloud credentials configuration page"""
    if 'user_email' not in session:
        flash('Please log in to access cloud credentials', 'error')
        return redirect(url_for('login'))
    
    return render_template('cloud-credentials.html', user_email=session['user_email'])

@app.route('/save-cloud-credentials', methods=['POST'])
def save_cloud_credentials():
    """Save cloud provider credentials to DynamoDB"""
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in to save credentials'}, 401
    
    try:
        user_email = session['user_email']
        
        # Get form data
        aws_account_id = request.form.get('aws_account_id', '').strip()
        aws_role_arn = request.form.get('aws_role_arn', '').strip()
        gcp_service_account = request.form.get('gcp_service_account', '').strip()
        azure_tenant_id = request.form.get('azure_tenant_id', '').strip()
        azure_client_id = request.form.get('azure_client_id', '').strip()
        azure_client_secret = request.form.get('azure_client_secret', '').strip()
        
        # Validate required fields
        if not all([aws_account_id, aws_role_arn, gcp_service_account, azure_tenant_id, azure_client_id, azure_client_secret]):
            return {'success': False, 'message': 'All fields are required'}, 400
        
        # Validate AWS Account ID format
        if not aws_account_id.isdigit() or len(aws_account_id) != 12:
            return {'success': False, 'message': 'AWS Account ID must be exactly 12 digits'}, 400
        
        # Validate AWS Role ARN format
        if not aws_role_arn.startswith('arn:aws:iam::') or ':role/' not in aws_role_arn:
            return {'success': False, 'message': 'Invalid AWS Role ARN format'}, 400
        
        # Validate GCP Service Account JSON
        try:
            import json
            gcp_json = json.loads(gcp_service_account)
            required_gcp_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
            if not all(field in gcp_json for field in required_gcp_fields):
                return {'success': False, 'message': 'Invalid GCP Service Account JSON - missing required fields'}, 400
        except json.JSONDecodeError:
            return {'success': False, 'message': 'Invalid JSON format for GCP Service Account'}, 400
        
        # Validate Azure GUIDs
        import re
        guid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(guid_pattern, azure_tenant_id, re.IGNORECASE):
            return {'success': False, 'message': 'Invalid Azure Tenant ID format'}, 400
        if not re.match(guid_pattern, azure_client_id, re.IGNORECASE):
            return {'success': False, 'message': 'Invalid Azure Client ID format'}, 400
        
        # Prepare cloud credentials data
        cloud_credentials = {
            'aws': {
                'account_id': aws_account_id,
                'role_arn': aws_role_arn
            },
            'gcp': {
                'service_account': gcp_json  # Store as parsed JSON object
            },
            'azure': {
                'tenant_id': azure_tenant_id,
                'client_id': azure_client_id,
                'client_secret': azure_client_secret
            }
        }
        
        # Update user record in DynamoDB
        table.update_item(
            Key={'email': user_email},
            UpdateExpression='SET cloud_credentials = :cc, updated_at = :ua',
            ExpressionAttributeValues={
                ':cc': cloud_credentials,
                ':ua': str(int(time.time()))
            }
        )
        
        logger.info(f"Successfully saved cloud credentials for user: {user_email}")
        return {'success': True, 'message': 'Cloud credentials saved successfully!', 'next_step': 'notification_email'}
        
    except Exception as e:
        logger.error(f"Error saving cloud credentials: {str(e)}")
        return {'success': False, 'message': f'Error saving credentials: {str(e)}'}, 500

@app.route('/trigger-baseline', methods=['POST'])
def trigger_baseline():
    """Trigger baseline collection for all configured cloud providers"""
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in to trigger baseline collection'}, 401
    
    try:
        user_email = session['user_email']
        
        # Get user's cloud credentials
        response = table.get_item(Key={'email': user_email})
        if 'Item' not in response:
            return {'success': False, 'message': 'User not found'}, 404
        
        user_data = response['Item']
        cloud_credentials = user_data.get('cloud_credentials', {})
        
        if not cloud_credentials:
            return {'success': False, 'message': 'No cloud credentials configured'}, 400
        
        # Simulate baseline collection (in real implementation, this would call cloud APIs)
        baseline_counts = {'aws_count': 0, 'gcp_count': 0, 'azure_count': 0}
        
        # Simulate AWS resources
        if 'aws' in cloud_credentials:
            aws_resources = [
                {'type': 'EC2', 'id': 'i-1234567890abcdef0', 'name': 'web-server-1'},
                {'type': 'S3', 'id': 'my-bucket-1', 'name': 'my-bucket-1'},
                {'type': 'RDS', 'id': 'db-instance-1', 'name': 'production-db'}
            ]
            for resource in aws_resources:
                create_snapshot(
                    user_email, 'AWS', resource['type'], resource['id'], 
                    resource['name'], {'status': 'running', 'region': 'us-east-1'}
                )
            baseline_counts['aws_count'] = len(aws_resources)
        
        # Simulate GCP resources
        if 'gcp' in cloud_credentials:
            gcp_resources = [
                {'type': 'VM', 'id': 'vm-1', 'name': 'gcp-vm-1'},
                {'type': 'StorageBucket', 'id': 'bucket-1', 'name': 'gcp-bucket-1'}
            ]
            for resource in gcp_resources:
                create_snapshot(
                    user_email, 'GCP', resource['type'], resource['id'], 
                    resource['name'], {'status': 'running', 'zone': 'us-central1-a'}
                )
            baseline_counts['gcp_count'] = len(gcp_resources)
        
        # Simulate Azure resources
        if 'azure' in cloud_credentials:
            azure_resources = [
                {'type': 'VM', 'id': 'vm-1', 'name': 'azure-vm-1'},
                {'type': 'StorageAccount', 'id': 'storage-1', 'name': 'azure-storage-1'},
                {'type': 'SQLDatabase', 'id': 'db-1', 'name': 'azure-db-1'}
            ]
            for resource in azure_resources:
                create_snapshot(
                    user_email, 'AZURE', resource['type'], resource['id'], 
                    resource['name'], {'status': 'running', 'location': 'eastus'}
                )
            baseline_counts['azure_count'] = len(azure_resources)
        
        # Update baseline summary
        update_baseline_summary(user_email, baseline_counts)
        
        logger.info(f"Baseline collection completed for {user_email}: {baseline_counts}")
        return {'success': True, 'message': 'Baseline collection completed', 'counts': baseline_counts}
        
    except Exception as e:
        logger.error(f"Error during baseline collection: {str(e)}")
        return {'success': False, 'message': f'Error during baseline collection: {str(e)}'}, 500

@app.route('/get-baseline-summary')
def get_baseline_summary_api():
    """Get baseline summary for the current user"""
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in'}, 401
    
    try:
        user_email = session['user_email']
        summary = get_baseline_summary(user_email)
        return {'success': True, 'summary': summary}
    except Exception as e:
        logger.error(f"Error getting baseline summary: {str(e)}")
        return {'success': False, 'message': f'Error getting baseline summary: {str(e)}'}, 500

# =============================================================================
# DRIFT DETECTION API ROUTES
# =============================================================================

@app.route('/start-drift-detection', methods=['POST'])
def start_drift_detection_api():
    """Start drift detection for the current user"""
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in'}, 401
    
    try:
        user_email = session['user_email']
        success = start_drift_detection(user_email)
        
        if success:
            return {'success': True, 'message': 'Drift detection started successfully'}
        else:
            return {'success': False, 'message': 'Failed to start drift detection'}, 500
            
    except Exception as e:
        logger.error(f"Error starting drift detection: {str(e)}")
        return {'success': False, 'message': f'Error starting drift detection: {str(e)}'}, 500

@app.route('/stop-drift-detection', methods=['POST'])
def stop_drift_detection_api():
    """Stop drift detection for the current user"""
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in'}, 401
    
    try:
        user_email = session['user_email']
        success = stop_drift_detection(user_email)
        
        if success:
            return {'success': True, 'message': 'Drift detection stopped successfully'}
        else:
            return {'success': False, 'message': 'Failed to stop drift detection'}, 500
            
    except Exception as e:
        logger.error(f"Error stopping drift detection: {str(e)}")
        return {'success': False, 'message': f'Error stopping drift detection: {str(e)}'}, 500

@app.route('/get-drift-status')
def get_drift_status_api():
    """Get drift detection status for the current user"""
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in'}, 401
    
    try:
        user_email = session['user_email']
        response = table.get_item(Key={'email': user_email})
        
        if 'Item' in response:
            user_data = response['Item']
            drift_status = user_data.get('drift_status', {
                'last_check': None,
                'drifts_detected': [],
                'total_drifts': 0
            })
            detection_status = user_data.get('detection_status', 'Stopped')
            
            return {
                'success': True,
                'detection_status': detection_status,
                'drift_status': drift_status
            }
        else:
            return {'success': False, 'message': 'User not found'}, 404
            
    except Exception as e:
        logger.error(f"Error getting drift status: {str(e)}")
        return {'success': False, 'message': f'Error getting drift status: {str(e)}'}, 500

@app.route('/run-drift-check', methods=['POST'])
def run_drift_check_api():
    """Manually run a drift check for the current user"""
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in'}, 401
    
    try:
        user_email = session['user_email']
        
        # Run drift detection in a separate thread to avoid blocking
        thread = threading.Thread(target=run_drift_detection, args=[user_email])
        thread.daemon = True
        thread.start()
        
        return {'success': True, 'message': 'Drift check initiated. Results will be available shortly.'}
        
    except Exception as e:
        logger.error(f"Error running drift check: {str(e)}")
        return {'success': False, 'message': f'Error running drift check: {str(e)}'}, 500

@app.route('/get-incident-history')
def get_incident_history_api():
    """Get the most recent drift-check incident/postmortem records for the current user"""
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in'}, 401

    try:
        user_email = session['user_email']
        incidents = get_incident_history(user_email, limit=20)

        return {
            'success': True,
            'incidents': incidents
        }

    except Exception as e:
        logger.error(f"Error getting incident history: {str(e)}")
        return {'success': False, 'message': f'Error getting incident history: {str(e)}'}, 500


@app.route('/get-incident/<incident_id>')
def get_incident_detail_api(incident_id):
    """Get the full detail of a single incident/postmortem record"""
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in'}, 401

    try:
        user_email = session['user_email']
        incident = get_incident_detail(user_email, incident_id)

        if incident is None:
            return {'success': False, 'message': 'Incident not found'}, 404

        return {
            'success': True,
            'incident': incident
        }

    except Exception as e:
        logger.error(f"Error getting incident detail: {str(e)}")
        return {'success': False, 'message': f'Error getting incident detail: {str(e)}'}, 500


@app.route('/run-demo-scenario', methods=['POST'])
def run_demo_scenario_api():
    """
    Run a scripted demo scenario through the real drift-detection pipeline.
    Intended for walkthroughs/demos where live cloud credentials aren't
    available - the resource data is scripted, but detection, diffing,
    severity classification, root-cause suggestions, and incident storage
    all execute exactly as they would for a real check.
    """
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in'}, 401

    try:
        data = request.get_json(silent=True) or {}
        scenario = data.get('scenario', 'critical')

        if scenario not in DEMO_SCENARIO_LABELS:
            return {
                'success': False,
                'message': f"Unknown demo scenario '{scenario}'. Valid options: {', '.join(DEMO_SCENARIO_LABELS.keys())}"
            }, 400

        user_email = session['user_email']
        baseline_snapshots, current_resources = get_demo_scenario_data(scenario)

        drift_summary = compare_with_baseline(baseline_snapshots, current_resources)
        drift_summary['demo_scenario'] = DEMO_SCENARIO_LABELS[scenario]

        incident_record = build_incident_record(user_email, drift_summary)
        incident_record['demo_scenario'] = DEMO_SCENARIO_LABELS[scenario]
        save_incident(incident_record)

        update_dashboard(user_email, drift_summary, 'Running')

        logger.info(f"Ran demo scenario '{scenario}' for {user_email}: {drift_summary['total_drifts']} drift(s)")

        return {
            'success': True,
            'message': f"Demo scenario completed: {DEMO_SCENARIO_LABELS[scenario]}",
            'drift_status': drift_summary,
            'incident': incident_record
        }

    except Exception as e:
        logger.error(f"Error running demo scenario: {str(e)}")
        return {'success': False, 'message': f'Error running demo scenario: {str(e)}'}, 500


@app.route('/get-reliability-scorecard')
def get_reliability_scorecard_api():
    """Get the reliability scorecard (check volume, clean-run rate, severity totals)"""
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in'}, 401

    try:
        user_email = session['user_email']
        scorecard = get_reliability_scorecard(user_email)

        return {
            'success': True,
            'scorecard': scorecard
        }

    except Exception as e:
        logger.error(f"Error getting reliability scorecard: {str(e)}")
        return {'success': False, 'message': f'Error getting reliability scorecard: {str(e)}'}, 500


@app.route('/test-s3-versioning-email', methods=['POST'])
def test_s3_versioning_email():
    """Send a test email about S3 bucket versioning being disabled"""
    try:
        # Create a test drift summary for S3 versioning
        drift_summary = {
            'timestamp': datetime.now().isoformat(),
            'drifts_detected': [
                {
                    'type': 's3_versioning',
                    'cloud': 'AWS',
                    'resource_type': 'S3',
                    'resource_id': 'test-bucket-versioning',
                    'resource_name': 'test-bucket-versioning',
                    'change_type': 'S3 Bucket Versioning Disabled',
                    'timestamp': datetime.now().isoformat(),
                    'details': 'Bucket versioning is currently disabled, which may pose a risk for data protection and recovery.'
                }
            ],
            'total_drifts': 1,
            'clouds_checked': ['AWS']
        }
        
        # Send the email
        success = send_ses_notification(SES_SENDER_EMAIL, SES_RECEIVER_EMAIL, drift_summary)
        
        if success:
            return {'success': True, 'message': 'S3 versioning test email sent successfully!'}
        else:
            return {'success': False, 'message': 'Failed to send S3 versioning test email'}, 500
            
    except Exception as e:
        logger.error(f"Error sending S3 versioning test email: {str(e)}")
        return {'success': False, 'message': f'Error sending test email: {str(e)}'}, 500

@app.route('/save-notification-email', methods=['POST'])
def save_notification_email():
    """Save notification email and trigger baseline collection"""
    if 'user_email' not in session:
        return {'success': False, 'message': 'Please log in to save notification email'}, 401
        
    try:
        user_email = session['user_email']
        notification_email = request.form.get('notification_email', '').strip()
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, notification_email):
            return {'success': False, 'message': 'Invalid email format'}, 400
        
        # Update user record with notification email
        table.update_item(
            Key={'email': user_email},
            UpdateExpression='SET notification_email = :ne, updated_at = :ua',
            ExpressionAttributeValues={
                ':ne': notification_email,
                ':ua': str(int(time.time()))
            }
        )
        
        logger.info(f"Saved notification email for user {user_email}: {notification_email}")
        
        # Trigger baseline collection
        baseline_result = run_baseline_collection(user_email)
        
        if baseline_result['success']:
            return {
                'success': True, 
                'message': 'Notification email saved and baseline collection completed!',
                'baseline_counts': baseline_result['counts'],
                'clouds_processed': baseline_result['clouds_processed'],
                'errors': baseline_result.get('errors', [])
            }
        else:
            return {
                'success': False,
                'message': 'Notification email saved but baseline collection failed',
                'errors': baseline_result.get('errors', [])
            }
        
    except Exception as e:
        logger.error(f"Error saving notification email: {str(e)}")
        return {'success': False, 'message': f'Error saving notification email: {str(e)}'}, 500

if __name__ == '__main__':
    # Create table if it doesn't exist
    if dynamodb and table:
        try:
            create_table_if_not_exists()
        except Exception as e:
            logger.error(f"Failed to create/verify table: {str(e)}")
            print(f"\nError: {str(e)}")
            print("Please check your AWS credentials and permissions.")
            print("Run 'aws sts get-caller-identity' to verify your AWS setup.")
            exit(1)
    else:
        logger.error("DynamoDB connection failed. Please check your AWS configuration.")
        print("\nError: DynamoDB connection failed.")
        print("Please ensure AWS CLI is configured with proper credentials.")
        print("Run 'aws configure' to set up your AWS credentials.")
        exit(1)
    
    print("\n" + "="*60)
    print("ConfigSync Dashboard Server Starting...")
    print("="*60)
    print(f"DynamoDB Region: {AWS_REGION}")
    print(f"DynamoDB Table: {DYNAMODB_TABLE_NAME}")
    print("="*60)
    print("To access the dashboard:")
    print("1. Open your browser")
    print("2. Navigate to: http://localhost:5000")
    print("3. Create an account or login")
    print("="*60)
    print("Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
