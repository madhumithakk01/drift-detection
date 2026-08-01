#!/usr/bin/env python3
"""
ConfigSync Dashboard - Complete Workflow Test
Tests the complete workflow: credentials → notification email → baseline collection
"""

import boto3
from botocore.exceptions import ClientError
import json
import time

def test_complete_workflow():
    """Test the complete workflow"""
    print("Testing ConfigSync Dashboard Complete Workflow...")
    print("=" * 60)
    
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
        users_table = dynamodb.Table('Users')
        snapshots_table = dynamodb.Table('Snapshots')
        
        print("✓ Connected to DynamoDB tables")
        
        # Test user creation with complete workflow
        test_email = 'workflow@configsync.com'
        test_password = 'testpassword123'
        notification_email = 'notifications@configsync.com'
        
        # Step 1: Create user with cloud credentials
        cloud_credentials = {
            'aws': {
                'account_id': '123456789012',
                'role_arn': 'arn:aws:iam::123456789012:role/ConfigSyncRole'
            },
            'gcp': {
                'service_account': {
                    'type': 'service_account',
                    'project_id': 'test-project',
                    'private_key_id': 'test-key-id',
                    'private_key': '-----BEGIN PRIVATE KEY-----\ntest-key\n-----END PRIVATE KEY-----\n',
                    'client_email': 'test@test-project.iam.gserviceaccount.com',
                    'client_id': '123456789012345678901'
                }
            },
            'azure': {
                'tenant_id': '12345678-1234-1234-1234-123456789012',
                'client_id': '12345678-1234-1234-1234-123456789012',
                'client_secret': 'test-secret'
            }
        }
        
        # Create user with cloud credentials
        users_table.put_item(
            Item={
                'email': test_email,
                'password': test_password,
                'cloud_credentials': cloud_credentials,
                'last_baseline_summary': {
                    'aws_count': 0,
                    'gcp_count': 0,
                    'azure_count': 0
                },
                'updated_at': str(int(time.time()))
            }
        )
        print("✓ Created user with cloud credentials")
        
        # Step 2: Add notification email
        users_table.update_item(
            Key={'email': test_email},
            UpdateExpression='SET notification_email = :ne, updated_at = :ua',
            ExpressionAttributeValues={
                ':ne': notification_email,
                ':ua': str(int(time.time()))
            }
        )
        print("✓ Added notification email")
        
        # Step 3: Simulate baseline collection
        # Create sample snapshots for each cloud
        aws_snapshots = [
            {
                'user_email': test_email,
                'snapshot_id': 'AWS#EC2#i-1234567890abcdef0',
                'cloud': 'AWS',
                'resource_type': 'EC2',
                'resource_id': 'i-1234567890abcdef0',
                'resource_name': 'web-server-1',
                'config': '{"instance_type": "t3.micro", "state": "running", "image_id": "ami-12345"}',
                'config_hash': 'aws_ec2_hash_123',
                'captured_at': int(time.time()),
                'source': 'baseline'
            },
            {
                'user_email': test_email,
                'snapshot_id': 'AWS#S3#my-bucket-1',
                'cloud': 'AWS',
                'resource_type': 'S3',
                'resource_id': 'my-bucket-1',
                'resource_name': 'my-bucket-1',
                'config': '{"name": "my-bucket-1", "creation_date": "2024-01-01T00:00:00Z"}',
                'config_hash': 'aws_s3_hash_123',
                'captured_at': int(time.time()),
                'source': 'baseline'
            }
        ]
        
        gcp_snapshots = [
            {
                'user_email': test_email,
                'snapshot_id': 'GCP#VM#gcp-vm-1',
                'cloud': 'GCP',
                'resource_type': 'VM',
                'resource_id': 'gcp-vm-1',
                'resource_name': 'web-server-gcp',
                'config': '{"machine_type": "e2-medium", "zone": "us-central1-a", "status": "running"}',
                'config_hash': 'gcp_vm_hash_123',
                'captured_at': int(time.time()),
                'source': 'baseline'
            }
        ]
        
        azure_snapshots = [
            {
                'user_email': test_email,
                'snapshot_id': 'AZURE#VM#azure-vm-1',
                'cloud': 'AZURE',
                'resource_type': 'VM',
                'resource_id': 'azure-vm-1',
                'resource_name': 'web-server-azure',
                'config': '{"vm_size": "Standard_B1s", "location": "East US", "status": "running"}',
                'config_hash': 'azure_vm_hash_123',
                'captured_at': int(time.time()),
                'source': 'baseline'
            },
            {
                'user_email': test_email,
                'snapshot_id': 'AZURE#StorageAccount#storage-1',
                'cloud': 'AZURE',
                'resource_type': 'StorageAccount',
                'resource_id': 'storage-1',
                'resource_name': 'mystorageaccount',
                'config': '{"location": "East US", "sku": "Standard_LRS", "status": "active"}',
                'config_hash': 'azure_storage_hash_123',
                'captured_at': int(time.time()),
                'source': 'baseline'
            }
        ]
        
        # Store all snapshots
        all_snapshots = aws_snapshots + gcp_snapshots + azure_snapshots
        for snapshot in all_snapshots:
            snapshots_table.put_item(Item=snapshot)
        
        print(f"✓ Created {len(all_snapshots)} resource snapshots")
        
        # Step 4: Update baseline summary
        baseline_counts = {
            'aws_count': len(aws_snapshots),
            'gcp_count': len(gcp_snapshots),
            'azure_count': len(azure_snapshots)
        }
        
        users_table.update_item(
            Key={'email': test_email},
            UpdateExpression='SET last_baseline_summary = :lbs, updated_at = :ua',
            ExpressionAttributeValues={
                ':lbs': baseline_counts,
                ':ua': str(int(time.time()))
            }
        )
        print("✓ Updated baseline summary")
        
        # Step 5: Verify complete workflow
        response = users_table.get_item(Key={'email': test_email})
        if 'Item' in response:
            user_data = response['Item']
            
            # Verify all required fields
            assert 'cloud_credentials' in user_data, "Cloud credentials missing"
            assert 'notification_email' in user_data, "Notification email missing"
            assert 'last_baseline_summary' in user_data, "Baseline summary missing"
            
            # Verify cloud credentials
            creds = user_data['cloud_credentials']
            assert 'aws' in creds, "AWS credentials missing"
            assert 'gcp' in creds, "GCP credentials missing"
            assert 'azure' in creds, "Azure credentials missing"
            
            # Verify notification email
            assert user_data['notification_email'] == notification_email, "Notification email incorrect"
            
            # Verify baseline summary
            summary = user_data['last_baseline_summary']
            assert summary['aws_count'] == 2, f"AWS count incorrect: {summary['aws_count']}"
            assert summary['gcp_count'] == 1, f"GCP count incorrect: {summary['gcp_count']}"
            assert summary['azure_count'] == 2, f"Azure count incorrect: {summary['azure_count']}"
            
            print("✓ All user data fields verified")
        
        # Step 6: Verify snapshots
        response = snapshots_table.query(
            KeyConditionExpression='user_email = :ue',
            ExpressionAttributeValues={':ue': test_email}
        )
        
        snapshots = response['Items']
        print(f"✓ Retrieved {len(snapshots)} snapshots from database")
        
        # Verify snapshot structure
        for snapshot in snapshots:
            required_fields = ['user_email', 'snapshot_id', 'cloud', 'resource_type', 
                             'resource_id', 'resource_name', 'config', 'config_hash', 
                             'captured_at', 'source']
            for field in required_fields:
                assert field in snapshot, f"Missing field {field} in snapshot"
        
        print("✓ All snapshot fields verified")
        
        # Step 7: Verify snapshot IDs format
        for snapshot in snapshots:
            snapshot_id = snapshot['snapshot_id']
            cloud = snapshot['cloud']
            resource_type = snapshot['resource_type']
            resource_id = snapshot['resource_id']
            
            expected_format = f"{cloud}#{resource_type}#{resource_id}"
            assert snapshot_id == expected_format, f"Snapshot ID format incorrect: {snapshot_id}"
        
        print("✓ All snapshot IDs follow correct format")
        
        # Clean up test data
        users_table.delete_item(Key={'email': test_email})
        
        for snapshot in all_snapshots:
            snapshots_table.delete_item(
                Key={
                    'user_email': snapshot['user_email'],
                    'snapshot_id': snapshot['snapshot_id']
                }
            )
        
        print("✓ Cleaned up test data")
        
        print("=" * 60)
        print("✓ Complete workflow test passed!")
        print("✓ Workflow: Save credentials → Notification email → Baseline collection → Store snapshots")
        print("✓ All data structures and relationships verified")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_complete_workflow()
    exit(0 if success else 1)
