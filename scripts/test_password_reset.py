#!/usr/bin/env python
"""
Test script for InfraCore Password Reset OTP System
Tests all endpoints with various scenarios
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# ANSI Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_header(text):
    print(f"\n{BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{YELLOW}ℹ {text}{RESET}")

def test_send_otp(email):
    """Test sending OTP"""
    print_header("Test 1: Send OTP")
    
    payload = {"email": email}
    print(f"Sending POST /forgot-password/send-otp")
    print(f"Payload: {json.dumps(payload)}")
    
    response = requests.post(
        f"{BASE_URL}/forgot-password/send-otp",
        json=payload,
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print_success(f"OTP sent successfully for {email}")
        return True, data
    else:
        print_error(f"Failed to send OTP: {data.get('error', 'Unknown error')}")
        return False, data

def test_invalid_email():
    """Test with non-existent email"""
    print_header("Test 2: Invalid Email (Security Test)")
    
    payload = {"email": "nonexistent@example.com"}
    print(f"Sending POST /forgot-password/send-otp with invalid email")
    
    response = requests.post(
        f"{BASE_URL}/forgot-password/send-otp",
        json=payload,
        timeout=10
    )
    
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print_success("Security check passed: Does not reveal if user exists")
        return True
    else:
        print_error(f"Unexpected response: {data}")
        return False

def test_rate_limiting(email):
    """Test rate limiting (3 per hour)"""
    print_header("Test 3: Rate Limiting")
    
    payload = {"email": email}
    
    # First request should succeed
    print_info("Attempt 1 (should succeed)...")
    r1 = requests.post(f"{BASE_URL}/forgot-password/send-otp", json=payload, timeout=10)
    print(f"Response 1: {r1.status_code}")
    
    if r1.status_code == 200:
        print_success("First request succeeded")
    else:
        print_error(f"First request failed: {r1.json()}")
        return False
    
    time.sleep(1)
    
    # Second request should succeed
    print_info("Attempt 2 (should succeed)...")
    r2 = requests.post(f"{BASE_URL}/forgot-password/send-otp", json=payload, timeout=10)
    print(f"Response 2: {r2.status_code}")
    
    if r2.status_code == 200:
        print_success("Second request succeeded")
    else:
        print_error(f"Second request failed: {r2.json()}")
        return False
    
    time.sleep(1)
    
    # Third request should succeed
    print_info("Attempt 3 (should succeed)...")
    r3 = requests.post(f"{BASE_URL}/forgot-password/send-otp", json=payload, timeout=10)
    print(f"Response 3: {r3.status_code}")
    
    if r3.status_code == 200:
        print_success("Third request succeeded")
    else:
        print_error(f"Third request failed: {r3.json()}")
        return False
    
    time.sleep(1)
    
    # Fourth request should be rate-limited
    print_info("Attempt 4 (should be rate-limited)...")
    r4 = requests.post(f"{BASE_URL}/forgot-password/send-otp", json=payload, timeout=10)
    print(f"Response 4: {r4.status_code}")
    data4 = r4.json()
    
    if r4.status_code == 429 and "Too many" in data4.get("error", ""):
        print_success("Rate limiting working correctly (429 error)")
        return True
    else:
        print_error(f"Rate limiting not working: {data4}")
        return False

def test_verify_otp(email, otp):
    """Test OTP verification"""
    print_header("Test 4: Verify OTP")
    
    payload = {"email": email, "otp": otp}
    print(f"Verifying OTP: {otp}")
    
    response = requests.post(
        f"{BASE_URL}/forgot-password/verify-otp",
        json=payload,
        timeout=10
    )
    
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print_success("OTP verified successfully")
        return True, data
    else:
        print_error(f"OTP verification failed: {data.get('error', 'Unknown')}")
        return False, data

def test_invalid_otp(email):
    """Test with invalid OTP"""
    print_header("Test 5: Invalid OTP")
    
    payload = {"email": email, "otp": "000000"}
    print(f"Testing with invalid OTP: 000000")
    
    response = requests.post(
        f"{BASE_URL}/forgot-password/verify-otp",
        json=payload,
        timeout=10
    )
    
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 400 and "Invalid OTP" in data.get("error", ""):
        print_success("Invalid OTP correctly rejected")
        return True
    else:
        print_error(f"Unexpected response: {data}")
        return False

def test_reset_password(email, password):
    """Test password reset"""
    print_header("Test 6: Reset Password")
    
    payload = {"email": email, "new_password": password}
    print(f"Resetting password for {email}")
    
    response = requests.post(
        f"{BASE_URL}/forgot-password/reset",
        json=payload,
        timeout=10
    )
    
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print_success("Password reset successfully")
        return True, data
    else:
        print_error(f"Password reset failed: {data.get('error', 'Unknown')}")
        return False, data

def test_weak_password(email):
    """Test weak password rejection"""
    print_header("Test 7: Weak Password Validation")
    
    payload = {"email": email, "new_password": "weak"}
    print(f"Testing with weak password: 'weak' (4 chars)")
    
    response = requests.post(
        f"{BASE_URL}/forgot-password/reset",
        json=payload,
        timeout=10
    )
    
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 400 and "8 characters" in data.get("error", ""):
        print_success("Weak password correctly rejected")
        return True
    else:
        print_error(f"Unexpected response: {data}")
        return False

def main():
    """Run all tests"""
    print(f"\n{BLUE}{'*'*60}")
    print("  InfraCore Password Reset OTP System - Test Suite")
    print(f"{'*'*60}{RESET}\n")
    
    print(f"Testing URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}\n")
    
    # Test email - use an existing user
    test_email = "admin@example.com"  # Change to existing user email
    test_password = "NewSecurePassword123!"
    
    results = []
    
    try:
        # Test 1: Send OTP
        success, data = test_send_otp(test_email)
        results.append(("Send OTP", success))
        
        if not success:
            print_error("Cannot continue - OTP sending failed")
            return
        
        # Extract OTP from console (manual for now)
        otp = input(f"\n{YELLOW}Enter the OTP received in email: {RESET}").strip()
        
        if not otp or len(otp) != 6:
            print_error("Invalid OTP format")
            return
        
        # Test 2: Verify OTP
        success, data = test_verify_otp(test_email, otp)
        results.append(("Verify OTP", success))
        
        if success:
            # Test 3: Reset Password
            success, data = test_reset_password(test_email, test_password)
            results.append(("Reset Password", success))
        
        # Test 4: Invalid Email (non-destructive tests below)
        success = test_invalid_email()
        results.append(("Invalid Email Security", success))
        
        # Test 5: Rate Limiting
        success = test_rate_limiting(test_email)
        results.append(("Rate Limiting", success))
        
        # Test 6: Weak Password
        success = test_weak_password(test_email)
        results.append(("Weak Password Validation", success))
        
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to server at {BASE_URL}")
        print_info("Make sure the server is running: python main.py")
        return
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{RESET}")
        return
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = f"{GREEN}PASS{RESET}" if success else f"{RED}FAIL{RESET}"
        print(f"  {status}  {test_name}")
    
    print(f"\n  {BLUE}Total: {passed}/{total} tests passed{RESET}\n")
    
    if passed == total:
        print_success("All tests passed!")
    else:
        print_error(f"{total - passed} test(s) failed")

if __name__ == "__main__":
    main()
