#!/usr/bin/env python3
"""
DDoS Script Test Suite
Quick tests to verify the DDoS simulation script works correctly
"""

import subprocess
import sys
import time
import requests

def test_server_connectivity():
    """Test if the Flask server is running"""
    print("🔍 Testing server connectivity...")
    try:
        response = requests.get("https://ae13353d5d1a.ngrok-free.app/", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and responsive")
            return True
        else:
            print(f"⚠️ Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("💡 Make sure Flask app is running: flask run --host=127.0.0.1 --port=5000")
        return False

def run_ddos_test(attack_type, duration=10, **kwargs):
    """Run a DDoS test and return the result"""
    print(f"\n🚀 Testing {attack_type.upper()} attack...")
    
    # Build command
    cmd = [
        "python", "tests/payloads/ddos_script.py",
        "--attack", attack_type,
        "--duration", str(duration)
    ]
    
    # Add additional arguments
    for key, value in kwargs.items():
        cmd.extend([f"--{key}", str(value)])
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Run the attack
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 30)
        end_time = time.time()
        
        print(f"⏱️ Execution time: {end_time - start_time:.2f} seconds")
        print(f"📊 Return code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ Attack completed successfully")
            
            # Extract statistics from output
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if "Total Requests Sent:" in line or "Success Rate:" in line or "Block Rate:" in line:
                    print(f"📈 {line.strip()}")
                    
        else:
            print("❌ Attack failed")
            print(f"Error: {result.stderr}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Attack timed out")
        return False
    except Exception as e:
        print(f"❌ Error running attack: {e}")
        return False

def main():
    """Run all DDoS tests"""
    print("=" * 60)
    print("DDOS SCRIPT TEST SUITE")
    print("=" * 60)
    
    # Check server connectivity first
    if not test_server_connectivity():
        print("\n❌ Cannot proceed with tests - server not available")
        sys.exit(1)
    
    print("\n🧪 Running DDoS simulation tests...")
    print("⚠️ These are low-intensity tests for verification only")
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: HTTP Flood (low intensity)
    total_tests += 1
    print(f"\n{'='*50}")
    print("TEST 1: HTTP Flood (Low Intensity)")
    print(f"{'='*50}")
    if run_ddos_test("http_flood", duration=10, rate=5, threads=2):
        tests_passed += 1
    
    # Test 2: POST Flood (low intensity)
    total_tests += 1
    print(f"\n{'='*50}")
    print("TEST 2: POST Flood (Low Intensity)")
    print(f"{'='*50}")
    if run_ddos_test("post_flood", duration=10, rate=3, threads=2):
        tests_passed += 1
    
    # Test 3: Slowloris (few connections)
    total_tests += 1
    print(f"\n{'='*50}")
    print("TEST 3: Slowloris (Few Connections)")
    print(f"{'='*50}")
    if run_ddos_test("slowloris", duration=15, connections=5):
        tests_passed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    print(f"Success Rate: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! DDoS script is working correctly.")
        print("\n📋 Next steps:")
        print("1. Test with higher intensity: --rate 100 --duration 60")
        print("2. Test through NGFW by changing --target to VM2 IP")
        print("3. Monitor server resources during attacks")
        print("4. Check NGFW logs for detection")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()
