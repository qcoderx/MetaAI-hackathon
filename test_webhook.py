import requests
import json

# 1. Create test business first
business_data = {
    "business_name": "Test Store",
    "phone": "+2349025713730"
}

print("Creating test business...")
business_response = requests.post(
    "http://localhost:8000/onboarding/setup",
    json=business_data
)
print(f"Business creation: {business_response.status_code}")
if business_response.status_code == 200:
    business_result = business_response.json()
    instance_name = business_result.get("instance_name", "test_store")
    print(f"Instance name: {instance_name}")
else:
    instance_name = "test_store"
    print("Using default instance name")

# 2. Test status reply webhook
test_payload = {
    "event": "onMessage",
    "session": instance_name,
    "response": {
        "id": "test_msg_123",
        "from": "2349025713730@c.us",
        "body": "How much is this?",
        "quotedMsg": {
            "from": "status@broadcast",
            "type": "image",
            "body": "https://example.com/product.jpg"
        }
    }
}

print("\nTesting webhook...")
response = requests.post(
    "http://localhost:8000/webhooks/wppconnect",
    json=test_payload
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")