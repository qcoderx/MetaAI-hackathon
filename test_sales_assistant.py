#!/usr/bin/env python3
"""
Test script for the WhatsApp AI Sales Assistant
Demonstrates the full lifecycle: catalog search, negotiation, order creation
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_PHONE = "+2348123456789"

def test_api_endpoint(endpoint, method="GET", data=None):
    """Test API endpoint with error handling"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            response = requests.get(url, timeout=10)
        
        print(f"\n🔗 {method} {endpoint}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {json.dumps(result, indent=2)}")
            return result
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")
        return None

def simulate_customer_conversation():
    """Simulate a complete customer conversation flow"""
    
    print("🎯 NAIRA SNIPER - WHATSAPP AI SALES ASSISTANT TEST")
    print("=" * 60)
    
    # Test 1: Health Check
    print("\n1️⃣ SYSTEM HEALTH CHECK")
    health = test_api_endpoint("/health")
    
    if not health or health.get("status") != "healthy":
        print("❌ System not healthy. Please start the server first.")
        return
    
    # Test 2: Catalog Search
    print("\n2️⃣ CUSTOMER CATALOG SEARCH")
    catalog_message = {
        "phone": TEST_PHONE,
        "message": "Do you have iPhone 13?"
    }
    
    catalog_response = test_api_endpoint("/webhook/test/message", "POST", catalog_message)
    
    # Test 3: Price Negotiation
    print("\n3️⃣ PRICE NEGOTIATION")
    time.sleep(1)  # Simulate conversation delay
    
    negotiation_message = {
        "phone": TEST_PHONE,
        "message": "Too expensive. I saw it for 180,000 on Jiji. Can you reduce?"
    }
    
    negotiation_response = test_api_endpoint("/webhook/test/message", "POST", negotiation_message)
    
    # Test 4: Order Creation
    print("\n4️⃣ ORDER CREATION")
    time.sleep(1)
    
    order_message = {
        "phone": TEST_PHONE,
        "message": "I want to buy it. My name is John Doe, address is 123 Victoria Island Lagos"
    }
    
    order_response = test_api_endpoint("/webhook/test/message", "POST", order_message)
    
    # Test 5: Check System Status
    print("\n5️⃣ FINAL SYSTEM STATUS")
    final_health = test_api_endpoint("/health")
    
    print("\n🎉 CONVERSATION SIMULATION COMPLETE!")
    print("=" * 60)
    
    # Summary
    print("\n📊 TEST SUMMARY:")
    print(f"✅ Health Check: {'PASS' if health else 'FAIL'}")
    print(f"✅ Catalog Search: {'PASS' if catalog_response else 'FAIL'}")
    print(f"✅ Negotiation: {'PASS' if negotiation_response else 'FAIL'}")
    print(f"✅ Order Creation: {'PASS' if order_response else 'FAIL'}")
    
    if order_response and order_response.get("agent_response", {}).get("status") == "order_created":
        order_id = order_response["agent_response"]["order_id"]
        print(f"\n🛒 Order Created: #{order_id}")
        print("📱 Owner should receive WhatsApp + Push notification")

def test_owner_commands():
    """Test owner command processing"""
    
    print("\n👨‍💼 TESTING OWNER COMMANDS")
    print("=" * 40)
    
    # Note: Owner commands will work after first user registers as owner
    print("Owner commands available after first user scans QR code and registers")
    return
    


def test_analytics_endpoints():
    """Test analytics and reporting features"""
    
    print("\n📊 TESTING ANALYTICS FEATURES")
    print("=" * 40)
    
    # Test webhook health
    webhook_health = test_api_endpoint("/webhook/health")
    
    if webhook_health:
        print("✅ Analytics system ready")
    else:
        print("❌ Analytics system not available")

if __name__ == "__main__":
    print("🚀 Starting Naira Sniper Sales Assistant Tests...")
    print(f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Main conversation simulation
        simulate_customer_conversation()
        
        # Owner commands test
        test_owner_commands()
        
        # Analytics test
        test_analytics_endpoints()
        
        print("\n🎯 ALL TESTS COMPLETED!")
        print("\n💡 NEXT STEPS:")
        print("1. Check WhatsApp for owner notifications")
        print("2. Verify order in database")
        print("3. Test Evolution API webhook integration")
        print("4. Set up Celery for background tasks")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")