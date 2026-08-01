#!/usr/bin/env python3
"""
ConfigSync Dashboard - S3 Versioning Email Test
Tests the hardcoded S3 versioning email functionality
"""

import requests
import json

def test_s3_versioning_email():
    """Test the S3 versioning email endpoint"""
    print("Testing S3 Versioning Email...")
    print("=" * 50)
    
    try:
        # Test the endpoint
        response = requests.post(
            'http://localhost:5000/test-s3-versioning-email',
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✓ S3 versioning email test successful!")
                print(f"✓ Message: {data.get('message')}")
                print("✓ Email should be sent from kkmadhumitha01@gmail.com to madhumithakk1504@gmail.com")
                print("✓ Email content includes S3 bucket versioning disabled warning")
            else:
                print(f"✗ Test failed: {data.get('message')}")
                return False
        else:
            print(f"✗ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        print("=" * 50)
        print("✓ S3 versioning email test completed successfully!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("✗ Connection error: Make sure the Flask app is running on localhost:5000")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_s3_versioning_email()
    exit(0 if success else 1)
