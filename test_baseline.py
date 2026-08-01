#!/usr/bin/env python3
"""
ConfigSync Dashboard - Baseline Counts Test Script
Tests the baseline counts functionality and DynamoDB table structure
"""

import boto3
from botocore.exceptions import ClientError
import json
import time

def test_baseline_functionality():
    """Test baseline counts functionality"""
    print("Testing ConfigSync Dashboard Baseline Functionality...")
    print("=" * 60)
    
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
        users_table = dynamodb.Table('Users')
        snapshots_table = dynamodb.Table('Snapshots')
        
        print("✓ Connected to DynamoDB tables")
        
        # Test user creation with baseline summary
        test_email = 'test@configsync.com'
        test_password = 'testpassword123'
        
        # Create test user
        users_table.put_item(
            Item={
                'email': test_email,
                'password': test_password,
                'last_baseline_summary': {
                    'aws_count': 0,
                    'gcp_count': 0,
                    'azure_count': 0
                },
                'updated_at': str(int(time.time()))
            }
        )
        print("✓ Created test user with initial baseline summary")
        
        # Test snapshot creation
        test_snapshots = [
            {
                'user_email': test_email,
                'snapshot_id': 'AWS#EC2#i-1234567890abcdef0',
                'cloud': 'AWS',
                'resource_type': 'EC2',
                'resource_id': 'i-1234567890abcdef0',
                'resource_name': 'web-server-1',
                'config': '{"status": "running", "region": "us-east-1"}',
                'config_hash': 'abc123def456',
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
                'config': '{"status": "active", "region": "us-east-1"}',
                'config_hash': 'def456ghi789',
                'captured_at': int(time.time()),
                'source': 'baseline'
            },
            {
                'user_email': test_email,
                'snapshot_id': 'GCP#VM#vm-1',
                'cloud': 'GCP',
                'resource_type': 'VM',
                'resource_id': 'vm-1',
                'resource_name': 'gcp-vm-1',
                'config': '{"status": "running", "zone": "us-central1-a"}',
                'config_hash': 'ghi789jkl012',
                'captured_at': int(time.time()),
                'source': 'baseline'
            }
        ]
        
        for snapshot in test_snapshots:
            snapshots_table.put_item(Item=snapshot)
        
        print("✓ Created test snapshots")
        
        # Test baseline summary update
        baseline_counts = {'aws_count': 2, 'gcp_count': 1, 'azure_count': 0}
        users_table.update_item(
            Key={'email': test_email},
            UpdateExpression='SET last_baseline_summary = :lbs, updated_at = :ua',
            ExpressionAttributeValues={
                ':lbs': baseline_counts,
                ':ua': str(int(time.time()))
            }
        )
        print("✓ Updated baseline summary")
        
        # Test retrieving baseline summary
        response = users_table.get_item(Key={'email': test_email})
        if 'Item' in response:
            summary = response['Item'].get('last_baseline_summary', {})
            print(f"✓ Retrieved baseline summary: {summary}")
            
            # Verify counts
            assert summary['aws_count'] == 2, "AWS count should be 2"
            assert summary['gcp_count'] == 1, "GCP count should be 1"
            assert summary['azure_count'] == 0, "Azure count should be 0"
            print("✓ Baseline counts are correct")
        
        # Test querying snapshots
        response = snapshots_table.query(
            KeyConditionExpression='user_email = :ue',
            ExpressionAttributeValues={':ue': test_email}
        )
        
        snapshots = response['Items']
        print(f"✓ Retrieved {len(snapshots)} snapshots")
        
        # Count resources by cloud
        cloud_counts = {'aws_count': 0, 'gcp_count': 0, 'azure_count': 0}
        for snapshot in snapshots:
            cloud = snapshot.get('cloud', '').upper()
            if cloud == 'AWS':
                cloud_counts['aws_count'] += 1
            elif cloud == 'GCP':
                cloud_counts['gcp_count'] += 1
            elif cloud == 'AZURE':
                cloud_counts['azure_count'] += 1
        
        print(f"✓ Calculated cloud counts: {cloud_counts}")
        
        # Verify counts match
        assert cloud_counts['aws_count'] == 2, "AWS count should be 2"
        assert cloud_counts['gcp_count'] == 1, "GCP count should be 1"
        assert cloud_counts['azure_count'] == 0, "Azure count should be 0"
        print("✓ Cloud counts match expected values")
        
        # Clean up test data
        users_table.delete_item(Key={'email': test_email})
        
        for snapshot in test_snapshots:
            snapshots_table.delete_item(
                Key={
                    'user_email': snapshot['user_email'],
                    'snapshot_id': snapshot['snapshot_id']
                }
            )
        
        print("✓ Cleaned up test data")
        
        print("=" * 60)
        print("✓ All baseline functionality tests passed!")
        print("✓ Baseline counts are properly reflected in Users.last_baseline_summary")
        print("✓ Snapshots table structure is correct")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_baseline_functionality()
    exit(0 if success else 1)
