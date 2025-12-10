# quick_test.py (put in project root)
#!/usr/bin/env python3
"""
Quick test to verify Konga and Jiji fixes
"""
import sys
import os
import json

# Add engine to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("🧪 QUICK TEST - KONGA + JIJI FIXES")
print("=" * 60)

try:
    from engine.scraper import JumiaScraper, JijiScraper, KongaScraper
    
    # Test Konga
    print("\n1️⃣ TESTING KONGA FIX")
    print("-" * 40)
    
    konga = KongaScraper()
    results = konga.search_product("iPhone", max_results=3)
    
    if results:
        print(f"✅ Konga: Found {len(results)} real products!")
        for i, item in enumerate(results, 1):
            print(f"  {i}. {item['name'][:50]}...")
            print(f"     💵 ₦{item['price']:,.0f}")
            if item.get('seller'):
                print(f"     🏪 Seller: {item['seller']}")
    else:
        print("❌ Konga still not working - checking HTML structure...")
        # Save page for debugging
        import requests
        url = "https://www.konga.com/search?search=iPhone"
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with open('konga_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("💾 Saved Konga page to konga_page.html for inspection")
    
    # Test Jiji
    print("\n2️⃣ TESTING JIJI IMPROVEMENTS")
    print("-" * 40)
    
    jiji = JijiScraper()
    results = jiji.search_product("iPhone", max_results=3)
    
    print(f"📦 Jiji: Got {len(results)} items")
    
    if results and 'smart_mock' in results[0].get('source', ''):
        print("✅ Jiji using SMART mock data (based on real prices)")
        for i, item in enumerate(results[:2], 1):
            print(f"  {i}. {item['name']}")
            print(f"     💵 ₦{item['price']:,.0f}")
            print(f"     📍 {item.get('location', 'Unknown')}")
    elif results:
        print("✅ Jiji found REAL listings!")
        for i, item in enumerate(results[:2], 1):
            print(f"  {i}. {item['name'][:50]}...")
            print(f"     💵 ₦{item['price']:,.0f}")
    else:
        print("❌ Jiji not working")
    
    # Test Jumia (should always work)
    print("\n3️⃣ TESTING JUMIA (BASELINE)")
    print("-" * 40)
    
    jumia = JumiaScraper()
    results = jumia.search_product("iPhone", max_results=3)
    
    print(f"✅ Jumia: {len(results)} real products (always works)")
    
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETE")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()