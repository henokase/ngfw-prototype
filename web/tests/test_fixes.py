#!/usr/bin/env python3
"""
Quick Test Script to Verify Fixes
Tests the fixed endpoints to ensure they work properly
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8081"

def test_path_traversal_fix():
    """Test that path traversal no longer returns 500 errors"""
    print("\n=== Testing Path Traversal Fix ===")
    
    test_payloads = [
        "README.md",  # Should work (file exists)
        "nonexistent.txt",  # Should return 'file not found' error
        "../../../../etc/passwd",  # Should return error or file content
    ]
    
    for payload in test_payloads:
        try:
            data = {"filename": payload}
            response = requests.post(
                f"{BASE_URL}/file",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"Payload: {payload}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"Response: {result.get('status', 'unknown')} - {result.get('message', 'no message')}")
                    if result.get('status') == 'success':
                        print(f"File size: {result.get('size', 0)} bytes")
                except:
                    print("Response: Could not parse JSON")
            else:
                print(f"Response: HTTP {response.status_code}")
            
            print("-" * 50)
            
        except Exception as e:
            print(f"Error testing {payload}: {e}")
            print("-" * 50)

def test_command_injection_fix():
    """Test that command injection endpoint works with correct parameter"""
    print("\n=== Testing Command Injection Fix ===")
    
    test_payloads = [
        "8.8.8.8",  # Normal ping
        "127.0.0.1",  # Local ping
        "8.8.8.8; whoami",  # Command injection attempt
    ]
    
    for payload in test_payloads:
        try:
            data = {"host": payload}
            response = requests.post(
                f"{BASE_URL}/cmd",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            print(f"Payload: {payload}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"Response: {result.get('status', 'unknown')}")
                    if result.get('status') == 'success':
                        output = result.get('output', '')
                        print(f"Command output: {output[:100]}..." if len(output) > 100 else f"Command output: {output}")
                except:
                    print("Response: Could not parse JSON")
            else:
                print(f"Response: HTTP {response.status_code}")
            
            print("-" * 50)
            
        except Exception as e:
            print(f"Error testing {payload}: {e}")
            print("-" * 50)

def main():
    """Run all tests"""
    print("Testing Fixed Endpoints")
    print("=" * 60)
    
    try:
        # Test if server is running
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print(f"Warning: Server returned {response.status_code}")
    except Exception as e:
        print(f"Error: Cannot connect to server at {BASE_URL}")
        print(f"Make sure Flask app is running: flask run --host=127.0.0.1 --port=5000")
        return
    
    test_path_traversal_fix()
    test_command_injection_fix()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("If you see JSON responses instead of 500 errors, the fixes worked!")

if __name__ == "__main__":
    main()
