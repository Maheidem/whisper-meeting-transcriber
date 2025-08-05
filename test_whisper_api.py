#!/usr/bin/env python3
"""Test script to verify Whisper API endpoint"""

import requests
import sys

def test_whisper_api(url="http://localhost:9000"):
    print(f"Testing Whisper API at {url}")
    
    # Test 1: Check if service is running
    try:
        response = requests.get(f"{url}/docs", timeout=5)
        print(f"✓ Service is running (status: {response.status_code})")
    except Exception as e:
        print(f"✗ Service not accessible: {e}")
        return
    
    # Test 2: Check API endpoints
    try:
        response = requests.get(f"{url}/openapi.json", timeout=5)
        if response.status_code == 200:
            api_spec = response.json()
            print(f"✓ API version: {api_spec.get('info', {}).get('version', 'unknown')}")
            print(f"✓ Available endpoints:")
            for path in api_spec.get('paths', {}):
                print(f"  - {path}")
        else:
            print(f"✗ Could not get API spec: {response.status_code}")
    except Exception as e:
        print(f"✗ Error getting API spec: {e}")
    
    # Test 3: Check ASR endpoint details
    try:
        # Try to get more info about the ASR endpoint
        response = requests.options(f"{url}/asr", timeout=5)
        print(f"\nASR endpoint OPTIONS response: {response.status_code}")
        print(f"Allowed methods: {response.headers.get('Allow', 'unknown')}")
    except Exception as e:
        print(f"✗ Error checking ASR endpoint: {e}")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9000"
    test_whisper_api(url)