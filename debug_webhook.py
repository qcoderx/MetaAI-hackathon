#!/usr/bin/env python3
"""
Debug webhook to test if messages are being received
"""

import requests
import json

def test_webhook():
    """Test if webhook endpoint is working"""
    
    # Test webhook health
    try:
        response = requests.get("http://localhost:8000/webhook/health")
        print(f"Webhook Health: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Webhook health check failed: {e}")
    
    # Test manual message
    test_data = {
        "phone": "+2348123456789",
        "message": "START"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/webhook/test/message",
            json=test_data
        )
        print(f"\nManual Test: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Manual test failed: {e}")

def check_evolution_status():
    """Check Evolution API status"""
    
    try:
        # Check if Evolution API is running
        response = requests.get("http://localhost:8081/instance/fetchInstances", 
                              headers={"apikey": "naira-sniper-secret-key"})
        print(f"\nEvolution API Status: {response.status_code}")
        if response.status_code == 200:
            instances = response.json()
            print(f"Instances: {json.dumps(instances, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Evolution API check failed: {e}")

if __name__ == "__main__":
    print("🔍 DEBUGGING WEBHOOK ISSUES")
    print("=" * 40)
    
    test_webhook()
    check_evolution_status()
    
    print("\n💡 TROUBLESHOOTING STEPS:")
    print("1. Check if Evolution API is connected (scan QR)")
    print("2. Check webhook logs in terminal")
    print("3. Test manual message endpoint")
    print("4. Verify phone number format")