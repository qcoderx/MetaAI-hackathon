"""
Evolution API v2 Test Script
Tests WhatsApp integration with Evolution API v2 including webhooks
"""
import time
import requests
from engine.whatsapp_evolution import EvolutionClient

def test_evolution_api():
    """Test Evolution API v2 integration"""
    print("🧪 Testing Evolution API v2 Integration")
    print("=" * 50)
    
    # Test 1: Check Evolution API is running
    print("\n1️⃣ Checking Evolution API status...")
    try:
        response = requests.get("http://localhost:8081", timeout=5)
        print("✅ Evolution API is running")
    except requests.exceptions.RequestException:
        print("❌ Evolution API not running!")
        print("Start with: docker-compose -f docker-compose.evolution.yml up -d")
        return False
    
    # Test 2: Initialize client
    print("\n2️⃣ Initializing Evolution client...")
    try:
        client = EvolutionClient()
        print("✅ Evolution client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False
    
    # Test 3: Check instance status
    print("\n3️⃣ Checking instance status...")
    try:
        status = client.get_instance_status()
        if "error" not in status:
            state = status.get("instance", {}).get("state", "unknown")
            print(f"✅ Instance status: {state}")
            
            if state != "open":
                print("⚠️  WhatsApp not connected. Get QR code:")
                qr = client.get_qr_code()
                if qr:
                    print("📱 QR Code available at: http://localhost:8081/manager")
                    print("   Scan with WhatsApp mobile app")
                else:
                    print("❌ Failed to get QR code")
        else:
            print(f"❌ Failed to get status: {status['error']}")
    except Exception as e:
        print(f"❌ Error checking status: {e}")
    
    # Test 4: Check webhook configuration
    print("\n4️⃣ Checking webhook configuration...")
    try:
        webhook_result = client.set_webhook()
        if "error" not in webhook_result:
            print("✅ Webhook configured successfully")
            print("   URL: http://host.docker.internal:8000/webhook/evolution")
        else:
            print(f"❌ Webhook configuration failed: {webhook_result['error']}")
    except Exception as e:
        print(f"❌ Error configuring webhook: {e}")
    
    # Test 5: Test message sending (only if connected)
    print("\n5️⃣ Testing message sending...")
    try:
        # Use a test number (replace with your own)
        test_phone = "2348012345678"  # Replace with your number
        test_message = "🎯 Test message from Naira Sniper Evolution API!"
        
        print(f"Sending test message to {test_phone}...")
        result = client.send_message(test_phone, test_message)
        
        if "error" not in result:
            print("✅ Message sent successfully!")
            print(f"   Message ID: {result.get('key', {}).get('id', 'N/A')}")
        else:
            print(f"❌ Failed to send message: {result['error']}")
            if "not connected" in str(result['error']).lower():
                print("   WhatsApp not connected. Scan QR code first.")
    except Exception as e:
        print(f"❌ Error sending message: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Evolution API Test Complete!")
    
    return True

def show_connection_guide():
    """Show WhatsApp connection guide"""
    print("\n📱 WhatsApp Connection Guide:")
    print("1. Open: http://localhost:8081/manager")
    print("2. Find instance: naira_sniper_v1")
    print("3. Click 'Connect' to get QR code")
    print("4. Scan QR with WhatsApp mobile app")
    print("5. Wait for 'Connected' status")
    print("6. Test messaging (both sending and receiving)")
    print("7. Send a message TO your WhatsApp to test webhook")
    print("8. Check API logs for incoming webhook calls")

if __name__ == "__main__":
    success = test_evolution_api()
    
    if success:
        show_connection_guide()
        
        print("\n🔄 Next Steps:")
        print("1. Connect WhatsApp via QR code")
        print("2. Update test_phone number in this script")
        print("3. Run test again to verify messaging")
        print("4. Start full system: python deploy.py")
    else:
        print("\n❌ Fix the issues above and try again")