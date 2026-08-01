#!/usr/bin/env python3
"""
ConfigSync Dashboard - Test Script
Tests DynamoDB connection and table creation
"""

import boto3
from botocore.exceptions import ClientError
import sys

def test_dynamodb_connection():
    """Test DynamoDB connection and table creation"""
    print("Testing ConfigSync Dashboard DynamoDB Connection...")
    print("=" * 50)
    
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
        table_name = 'Users'
        
        print(f"✓ Connected to DynamoDB in region: eu-north-1")
        
        # Test table creation/access
        try:
            table = dynamodb.Table(table_name)
            table.load()
            print(f"✓ Table '{table_name}' already exists and is accessible")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"ℹ Table '{table_name}' does not exist - will be created on first run")
            else:
                print(f"✗ Error accessing table: {e}")
                return False
        
        # Test basic operations
        try:
            # Test put item (will be cleaned up)
            test_email = 'test@configsync.com'
            test_password = 'testpassword123'
            
            table.put_item(
                Item={
                    'email': test_email,
                    'password': test_password
                }
            )
            print("✓ Successfully wrote test item to DynamoDB")
            
            # Test get item
            response = table.get_item(Key={'email': test_email})
            if 'Item' in response:
                print("✓ Successfully read test item from DynamoDB")
                
                # Clean up test item
                table.delete_item(Key={'email': test_email})
                print("✓ Successfully cleaned up test item")
            else:
                print("✗ Failed to read test item from DynamoDB")
                return False
                
        except Exception as e:
            print(f"✗ Error during test operations: {e}")
            return False
        
        print("=" * 50)
        print("✓ All DynamoDB tests passed!")
        print("✓ ConfigSync Dashboard is ready to run")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"✗ Failed to connect to DynamoDB: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure AWS CLI is configured: aws configure")
        print("2. Check IAM permissions for DynamoDB access")
        print("3. Verify region is set to 'eu-north-1'")
        print("4. Run: aws sts get-caller-identity")
        return False

if __name__ == '__main__':
    success = test_dynamodb_connection()
    sys.exit(0 if success else 1)
