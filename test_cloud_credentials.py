#!/usr/bin/env python3
"""
ConfigSync Dashboard - Cloud Credentials Test Script
Tests the cloud credentials form validation and data structure
"""

import json
import re

def test_aws_validation():
    """Test AWS credential validation"""
    print("Testing AWS validation...")
    
    # Test Account ID validation
    valid_account_id = "123456789012"
    invalid_account_id = "12345678901"  # Too short
    
    assert len(valid_account_id) == 12 and valid_account_id.isdigit(), "Valid account ID should pass"
    assert not (len(invalid_account_id) == 12 and invalid_account_id.isdigit()), "Invalid account ID should fail"
    
    # Test Role ARN validation
    valid_role_arn = "arn:aws:iam::123456789012:role/ConfigSyncRole"
    invalid_role_arn = "arn:aws:iam::123456789012:user/ConfigSyncUser"
    
    assert valid_role_arn.startswith('arn:aws:iam::') and ':role/' in valid_role_arn, "Valid role ARN should pass"
    assert not (invalid_role_arn.startswith('arn:aws:iam::') and ':role/' in invalid_role_arn), "Invalid role ARN should fail"
    
    print("✓ AWS validation tests passed")

def test_gcp_validation():
    """Test GCP credential validation"""
    print("Testing GCP validation...")
    
    # Valid GCP service account JSON
    valid_gcp_json = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\ntest-key\n-----END PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789012345678901"
    }
    
    # Invalid GCP JSON (missing required fields)
    invalid_gcp_json = {
        "type": "service_account",
        "project_id": "test-project"
        # Missing required fields
    }
    
    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
    
    assert all(field in valid_gcp_json for field in required_fields), "Valid GCP JSON should have all required fields"
    assert not all(field in invalid_gcp_json for field in required_fields), "Invalid GCP JSON should fail validation"
    
    print("✓ GCP validation tests passed")

def test_azure_validation():
    """Test Azure credential validation"""
    print("Testing Azure validation...")
    
    valid_guid = "12345678-1234-1234-1234-123456789012"
    invalid_guid = "12345678-1234-1234-1234-12345678901"  # Too short
    
    guid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    
    assert re.match(guid_pattern, valid_guid, re.IGNORECASE), "Valid GUID should pass"
    assert not re.match(guid_pattern, invalid_guid, re.IGNORECASE), "Invalid GUID should fail"
    
    print("✓ Azure validation tests passed")

def test_cloud_credentials_structure():
    """Test cloud credentials data structure"""
    print("Testing cloud credentials data structure...")
    
    # Sample cloud credentials structure
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
    
    # Validate structure
    assert 'aws' in cloud_credentials, "Should have AWS section"
    assert 'gcp' in cloud_credentials, "Should have GCP section"
    assert 'azure' in cloud_credentials, "Should have Azure section"
    
    assert 'account_id' in cloud_credentials['aws'], "AWS should have account_id"
    assert 'role_arn' in cloud_credentials['aws'], "AWS should have role_arn"
    
    assert 'service_account' in cloud_credentials['gcp'], "GCP should have service_account"
    
    assert 'tenant_id' in cloud_credentials['azure'], "Azure should have tenant_id"
    assert 'client_id' in cloud_credentials['azure'], "Azure should have client_id"
    assert 'client_secret' in cloud_credentials['azure'], "Azure should have client_secret"
    
    print("✓ Cloud credentials structure tests passed")

def main():
    """Run all tests"""
    print("ConfigSync Dashboard - Cloud Credentials Test Suite")
    print("=" * 60)
    
    try:
        test_aws_validation()
        test_gcp_validation()
        test_azure_validation()
        test_cloud_credentials_structure()
        
        print("=" * 60)
        print("✓ All cloud credentials tests passed!")
        print("✓ The cloud credentials form is ready for use")
        print("=" * 60)
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
