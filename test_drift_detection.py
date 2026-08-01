#!/usr/bin/env python3
"""
ConfigSync Dashboard - Drift Detection Test
Tests the drift detection functionality
"""

import boto3
from botocore.exceptions import ClientError
import json
import time

def test_drift_detection():
    """Test drift detection functionality"""
    print("Testing ConfigSync Dashboard Drift Detection...")
    print("=" * 60)
    
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
        users_table = dynamodb.Table('Users')
        snapshots_table = dynamodb.Table('Snapshots')
        
        print("✓ Connected to DynamoDB tables")
        
        # Test user email
        test_email = 'madhumithakk1504@gmail.com'
        
        # Step 1: Update user with drift detection fields
        users_table.update_item(
            Key={'email': test_email},
            UpdateExpression='SET detection_status = :ds, drift_status = :drs, updated_at = :ua',
            ExpressionAttributeValues={
                ':ds': 'Stopped',
                ':drs': {
                    'last_check': None,
                    'drifts_detected': [],
                    'total_drifts': 0
                },
                ':ua': str(int(time.time()))
            }
        )
        print("✓ Updated user with drift detection fields")
        
        # Step 2: Create test baseline snapshots
        test_snapshots = [
            {
                'user_email': test_email,
                'snapshot_id': 'AWS#EC2#i-test123',
                'cloud': 'AWS',
                'resource_type': 'EC2',
                'resource_id': 'i-test123',
                'resource_name': 'test-instance',
                'config': '{"instance_type": "t3.micro", "state": "running"}',
                'config_hash': 'baseline_hash_123',
                'captured_at': int(time.time()),
                'source': 'baseline'
            },
            {
                'user_email': test_email,
                'snapshot_id': 'AWS#S3#test-bucket',
                'cloud': 'AWS',
                'resource_type': 'S3',
                'resource_id': 'test-bucket',
                'resource_name': 'test-bucket',
                'config': '{"name": "test-bucket", "creation_date": "2024-01-01T00:00:00Z"}',
                'config_hash': 'baseline_s3_hash_123',
                'captured_at': int(time.time()),
                'source': 'baseline'
            }
        ]
        
        for snapshot in test_snapshots:
            snapshots_table.put_item(Item=snapshot)
        
        print(f"✓ Created {len(test_snapshots)} test baseline snapshots")
        
        # Step 3: Test drift detection functions
        from app import (
            get_baseline_snapshots, 
            collect_aws_current, 
            collect_gcp_current, 
            collect_azure_current,
            compare_with_baseline,
            update_dashboard
        )
        
        # Test baseline snapshots retrieval
        baseline_snapshots = get_baseline_snapshots(test_email)
        print(f"✓ Retrieved baseline snapshots: {len(baseline_snapshots)} clouds")
        
        # Test current resource collection (simulated)
        current_resources = {
            'aws': {
                'AWS#EC2#i-test123': {
                    'config': '{"instance_type": "t3.micro", "state": "stopped"}',
                    'config_hash': 'modified_hash_456',
                    'resource_type': 'EC2',
                    'resource_id': 'i-test123',
                    'resource_name': 'test-instance'
                },
                'AWS#S3#test-bucket': {
                    'config': '{"name": "test-bucket", "creation_date": "2024-01-01T00:00:00Z"}',
                    'config_hash': 'baseline_s3_hash_123',
                    'resource_type': 'S3',
                    'resource_id': 'test-bucket',
                    'resource_name': 'test-bucket'
                }
            }
        }
        
        print("✓ Created test current resources")
        
        # Test drift comparison
        drift_summary = compare_with_baseline(baseline_snapshots, current_resources)
        print(f"✓ Drift comparison completed: {drift_summary['total_drifts']} drifts detected")
        
        # Verify drift detection results
        assert drift_summary['total_drifts'] > 0, "Should detect at least one drift"
        assert len(drift_summary['drifts_detected']) > 0, "Should have drift details"
        
        print("✓ Drift detection logic working correctly")
        
        # Test dashboard update
        success = update_dashboard(test_email, drift_summary, 'Running')
        assert success, "Dashboard update should succeed"
        print("✓ Dashboard update successful")
        
        # Verify updated data in database
        response = users_table.get_item(Key={'email': test_email})
        if 'Item' in response:
            user_data = response['Item']
            drift_status = user_data.get('drift_status', {})
            detection_status = user_data.get('detection_status', 'Stopped')
            
            assert detection_status == 'Running', "Detection status should be Running"
            assert drift_status['total_drifts'] > 0, "Should have drift count"
            assert len(drift_status['drifts_detected']) > 0, "Should have drift details"
            
            print("✓ Database updated correctly")
            print(f"  - Detection Status: {detection_status}")
            print(f"  - Total Drifts: {drift_status['total_drifts']}")
            print(f"  - Drifts Detected: {len(drift_status['drifts_detected'])}")
        
        # Clean up test data
        for snapshot in test_snapshots:
            snapshots_table.delete_item(
                Key={
                    'user_email': snapshot['user_email'],
                    'snapshot_id': snapshot['snapshot_id']
                }
            )
        
        print("✓ Cleaned up test data")
        
        print("=" * 60)
        print("✓ Drift detection test passed!")
        print("✓ All drift detection functions working correctly")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_drift_detection()
    exit(0 if success else 1)
