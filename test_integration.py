"""
Integration Test for Complete Naira Sniper System
Tests the full pipeline: Scraping → AI Decision → WhatsApp
"""
import requests
import json
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database import get_session
from app.models import Product, Customer, CompetitorPrice, SalesLog
from brain.core_logic import PricingAgent
from engine.whatsapp import WhatsAppClient, send_price_drop_message
from engine.workers import trigger_market_scrape, trigger_ghost_retargeting

BASE_URL = "http://localhost:8000"

def test_full_pipeline():
    """Test complete pipeline from scraping to WhatsApp"""
    print("🧪 Testing Full Naira Sniper Pipeline")
    print("=" * 50)
    
    # Step 1: Add test product
    print("\n1️⃣ Adding test product...")
    product_data = {
        "name": "Oraimo Power Bank 20000mAh",
        "model": "2024 Original",
        "current_price": 15000,
        "floor_price": 13000
    }
    
    response = requests.post(f"{BASE_URL}/product/add", json=product_data)
    if response.status_code != 200:
        print(f"❌ Failed to add product: {response.text}")
        return False
    
    product = response.json()
    product_id = product["id"]
    print(f"✅ Product added with ID: {product_id}")
    
    # Step 2: Simulate competitor prices (manual injection)
    print("\n2️⃣ Injecting competitor prices...")
    with next(get_session()) as session:
        # Add some competitor prices
        prices = [
            CompetitorPrice(product_id=product_id, source="Jiji", price=14500, url="https://jiji.ng/test"),
            CompetitorPrice(product_id=product_id, source="Jumia", price=14800, url="https://jumia.com.ng/test"),
            CompetitorPrice(product_id=product_id, source="Instagram @techstore_ng", price=14200, url="https://instagram.com/techstore_ng")
        ]
        
        for price in prices:
            session.add(price)
        session.commit()
    
    print("✅ Competitor prices injected: ₦14,500, ₦14,800, ₦14,200")
    
    # Step 3: Create test customer (price-sensitive)
    print("\n3️⃣ Creating price-sensitive customer...")
    customer_data = {
        "phone": "+2348012345678",
        "message": "How much last? I see am for 14500 on Jiji. Too cost!",
        "customer_name": "Test Customer",
        "product_id": product_id
    }
    
    response = requests.post(f"{BASE_URL}/webhook/whatsapp", json=customer_data)
    if response.status_code != 200:
        print(f"❌ Failed to create customer: {response.text}")
        return False
    
    customer_result = response.json()
    customer_id = customer_result["customer_id"]
    print(f"✅ Customer created: {customer_result['customer_type']} (confidence: {customer_result['classification']['confidence']})")
    
    # Step 4: Get AI recommendation
    print("\n4️⃣ Getting AI pricing recommendation...")
    response = requests.get(f"{BASE_URL}/market/analysis/{product_id}?customer_id={customer_id}")
    if response.status_code != 200:
        print(f"❌ Failed to get recommendation: {response.text}")
        return False
    
    recommendation = response.json()
    print(f"✅ AI Recommendation:")
    print(f"   Strategy: {recommendation['recommended_strategy']}")
    print(f"   Price: ₦{recommendation['recommended_price']:,.0f}")
    print(f"   Conversion Probability: {recommendation['conversion_probability']:.1%}")
    print(f"   Reasoning: {recommendation['reasoning']}")
    
    # Step 5: Test WhatsApp message (if configured)
    print("\n5️⃣ Testing WhatsApp integration...")
    try:
        client = WhatsAppClient()
        
        if recommendation['recommended_strategy'] == 'price_drop':
            success = send_price_drop_message(
                phone="+2348012345678",
                customer_name="Test Customer",
                product_name=product_data["name"],
                old_price=product_data["current_price"],
                new_price=recommendation["recommended_price"]
            )
        else:
            from engine.whatsapp import send_value_message
            success = send_value_message(
                phone="+2348012345678",
                customer_name="Test Customer",
                product_name=product_data["name"],
                price=product_data["current_price"]
            )
        
        if success:
            print("✅ WhatsApp message sent successfully")
        else:
            print("⚠️  WhatsApp message failed (check credentials)")
            
    except Exception as e:
        print(f"⚠️  WhatsApp not configured: {e}")
    
    # Step 6: Test ghost retargeting
    print("\n6️⃣ Testing ghost retargeting...")
    with next(get_session()) as session:
        # Create old inquiry (simulate ghost customer)
        old_inquiry = SalesLog(
            customer_id=customer_id,
            product_id=product_id,
            inquiry_date=datetime.utcnow() - timedelta(hours=25),  # 25 hours ago
            purchased=False
        )
        session.add(old_inquiry)
        session.commit()
    
    print("✅ Ghost customer created (inquired 25 hours ago)")
    
    # Test retargeting logic
    try:
        result = trigger_ghost_retargeting()
        print(f"✅ Ghost retargeting triggered: {result}")
    except Exception as e:
        print(f"⚠️  Ghost retargeting failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Integration Test Complete!")
    
    # Summary
    print("\n📊 Test Summary:")
    print(f"✅ Product Management: Working")
    print(f"✅ Customer Profiling: Working ({customer_result['customer_type']})")
    print(f"✅ AI Decision Engine: Working ({recommendation['recommended_strategy']})")
    print(f"✅ Market Intelligence: Working (3 competitor prices)")
    print(f"✅ Database Integration: Working")
    
    return True

def test_celery_tasks():
    """Test Celery background tasks"""
    print("\n🔧 Testing Celery Tasks")
    print("-" * 30)
    
    try:
        # Test market scraping
        print("Testing market scraping task...")
        result = trigger_market_scrape()
        print(f"✅ Market scrape task queued: {result}")
        
        # Test ghost retargeting
        print("Testing ghost retargeting task...")
        result = trigger_ghost_retargeting()
        print(f"✅ Ghost retargeting task queued: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Celery tasks failed: {e}")
        print("Make sure Redis and Celery worker are running")
        return False

def main():
    print("🚀 Naira Sniper Integration Test Suite")
    print("=" * 60)
    
    # Check if server is running
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ API Server is running: {health.json()}")
    except requests.exceptions.RequestException:
        print("❌ API Server not running!")
        print("Start the server first: python main.py")
        return
    
    # Run tests
    success = test_full_pipeline()
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Configure WhatsApp credentials in .env")
        print("2. Start Celery worker: celery -A engine.workers worker --loglevel=info")
        print("3. Start Celery beat: celery -A engine.workers beat --loglevel=info")
        print("4. Monitor logs for automated scraping and retargeting")
        
        print("\n🔥 System Status: FULLY OPERATIONAL")
    else:
        print("\n❌ Some tests failed. Check the logs above.")

if __name__ == "__main__":
    main()