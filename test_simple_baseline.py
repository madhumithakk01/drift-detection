#!/usr/bin/env python3
"""
ConfigSync Dashboard - Simple Baseline Test
Tests basic baseline functionality
"""

import boto3
from botocore.exceptions import ClientError
import time

def test_simple_baseline():
    """Test basic baseline functionality"""
    print("Testing Simple Baseline Functionality...")
    print("=" * 50)
    
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
        users_table = dynamodb.Table('Users')
        
        print("✓ Connected to Users table")
        
        # Test user creation with baseline summary
        test_email = 'test@configsync.com'
        test_password = 'testpassword123'
        
        # Create test user
        users_table.put_item(
            Item={
                'email': test_email,
                'password': test_password,
                'last_baseline_summary': {
                    'aws_count': 5,
                    'gcp_count': 3,
                    'azure_count': 2
                },
                'updated_at': str(int(time.time()))
            }
        )
        print("✓ Created test user with baseline summary")
        
        # Test retrieving baseline summary
        response = users_table.get_item(Key={'email': test_email})
        if 'Item' in response:
            summary = response['Item'].get('last_baseline_summary', {})
            print(f"✓ Retrieved baseline summary: {summary}")
            
            # Verify counts
            assert summary['aws_count'] == 5, "AWS count should be 5"
            assert summary['gcp_count'] == 3, "GCP count should be 3"
            assert summary['azure_count'] == 2, "Azure count should be 2"
            print("✓ Baseline counts are correct")
        
        # Test updating baseline summary
        new_counts = {'aws_count': 7, 'gcp_count': 4, 'azure_count': 1}
        users_table.update_item(
            Key={'email': test_email},
            UpdateExpression='SET last_baseline_summary = :lbs, updated_at = :ua',
            ExpressionAttributeValues={
                ':lbs': new_counts,
                ':ua': str(int(time.time()))
            }
        )
        print("✓ Updated baseline summary")
        
        # Verify update
        response = users_table.get_item(Key={'email': test_email})
        if 'Item' in response:
            summary = response['Item'].get('last_baseline_summary', {})
            print(f"✓ Updated summary: {summary}")
            
            assert summary['aws_count'] == 7, "AWS count should be 7"
            assert summary['gcp_count'] == 4, "GCP count should be 4"
            assert summary['azure_count'] == 1, "Azure count should be 1"
            print("✓ Updated counts are correct")
        
        # Clean up test data
        users_table.delete_item(Key={'email': test_email})
        print("✓ Cleaned up test data")
        
        print("=" * 50)
        print("✓ All baseline functionality tests passed!")
        print("✓ Baseline counts are properly stored and retrieved")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_simple_baseline()
    exit(0 if success else 1)
