# complete_real_system.py
#!/usr/bin/env python3
"""
COMPLETE REAL Price Comparison System - NO MOCK DATA
"""
import sys
import os
import json
import time
import concurrent.futures
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("💰 REAL PRICE COMPARISON SYSTEM - NO MOCK DATA")
print("=" * 70)

class RealPriceSystem:
    """Real system that scrapes ACTUAL data from all platforms"""
    
    def __init__(self, headless: bool = True):
        from engine.scraper_v2 import JumiaScraper, JijiSeleniumScraper, KongaSeleniumScraper
        
        print("🚀 Initializing REAL scrapers...")
        
        # Initialize all scrapers
        self.jumia = JumiaScraper()
        
        try:
            self.jiji = JijiSeleniumScraper(headless=headless)
            print("✅ Jiji Selenium scraper initialized")
        except Exception as e:
            print(f"❌ Jiji Selenium failed: {e}")
            self.jiji = None
        
        try:
            self.konga = KongaSeleniumScraper(headless=headless)
            print("✅ Konga Selenium scraper initialized")
        except Exception as e:
            print(f"❌ Konga Selenium failed: {e}")
            self.konga = None
        
        print("🎯 REAL Price System Ready!")
    
    def search_all_parallel(self, product_name: str, max_results: int = 6) -> Dict[str, List[Dict]]:
        """Search ALL marketplaces in parallel for speed"""
        print(f"\n🔍 Searching for: {product_name}")
        print("=" * 50)
        
        start_time = time.time()
        results = {}
        
        # Run scrapers in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all scraping tasks
            future_to_source = {}
            
            # Jumia
            future_to_source[executor.submit(
                self._scrape_with_timeout, 
                self.jumia.search_product, product_name, max_results
            )] = 'jumia'
            
            # Jiji (if available)
            if self.jiji:
                future_to_source[executor.submit(
                    self._scrape_with_timeout,
                    self.jiji.search_product, product_name, max_results
                )] = 'jiji'
            else:
                results['jiji'] = []
            
            # Konga (if available)
            if self.konga:
                future_to_source[executor.submit(
                    self._scrape_with_timeout,
                    self.konga.search_product, product_name, max_results
                )] = 'konga'
            else:
                results['konga'] = []
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    data = future.result(timeout=60)  # 60 second timeout per scraper
                    results[source] = data
                    print(f"✅ {source.upper()}: {len(data)} items")
                except Exception as e:
                    print(f"❌ {source.upper()} failed: {e}")
                    results[source] = []
        
        elapsed = time.time() - start_time
        
        # Summary
        total_items = sum(len(items) for items in results.values())
        print(f"\n⏱️  Completed in {elapsed:.1f} seconds")
        print(f"📊 Total items found: {total_items}")
        
        # Add metadata
        results['metadata'] = {
            'product': product_name,
            'search_time': elapsed,
            'timestamp': datetime.now().isoformat(),
            'total_items': total_items,
            'sources_used': list(results.keys())
        }
        
        return results
    
    def _scrape_with_timeout(self, scraper_func, *args, **kwargs):
        """Run scraper with timeout protection"""
        import threading
        result = []
        exception = None
        
        def target():
            nonlocal result, exception
            try:
                result = scraper_func(*args, **kwargs)
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=90)  # 90 second timeout
        
        if thread.is_alive():
            raise TimeoutError(f"Scraper timed out after 90 seconds")
        
        if exception:
            raise exception
        
        return result
    
    def search_all_sequential(self, product_name: str, max_results: int = 6) -> Dict[str, List[Dict]]:
        """Search sequentially (more reliable for debugging)"""
        print(f"\n🔍 Searching for: {product_name}")
        print("-" * 50)
        
        start_time = time.time()
        results = {}
        
        # 1. Jumia (fastest, most reliable)
        print("🛍️  Searching Jumia...")
        try:
            results['jumia'] = self.jumia.search_product(product_name, max_results)
            print(f"✅ Jumia: {len(results['jumia'])} items")
        except Exception as e:
            print(f"❌ Jumia failed: {e}")
            results['jumia'] = []
        
        # 2. Jiji
        if self.jiji:
            print("📱 Searching Jiji...")
            try:
                results['jiji'] = self.jiji.search_product(product_name, max_results)
                print(f"✅ Jiji: {len(results['jiji'])} items")
            except Exception as e:
                print(f"❌ Jiji failed: {e}")
                results['jiji'] = []
        else:
            results['jiji'] = []
            print("⚠️  Jiji scraper not available")
        
        # 3. Konga
        if self.konga:
            print("🏪 Searching Konga...")
            try:
                results['konga'] = self.konga.search_product(product_name, max_results)
                print(f"✅ Konga: {len(results['konga'])} items")
            except Exception as e:
                print(f"❌ Konga failed: {e}")
                results['konga'] = []
        else:
            results['konga'] = []
            print("⚠️  Konga scraper not available")
        
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  Total time: {elapsed:.1f} seconds")
        
        return results
    
    def display_comparison(self, results):
        """Display beautiful price comparison with REAL data"""
        print("\n" + "=" * 80)
        print("💰 REAL PRICE COMPARISON - ACTUAL DATA")
        print("=" * 80)
        
        all_items = []
        
        # Display each marketplace
        for source, items in results.items():
            if source == 'metadata':
                continue
            
            source_info = {
                'jumia': ('🛍️', 'JUMIA', 'Official Store'),
                'jiji': ('📱', 'JIJI', 'Marketplace'),
                'konga': ('🏪', 'KONGA', 'E-commerce')
            }
            
            emoji, name, desc = source_info.get(source, ('📦', source.upper(), ''))
            
            print(f"\n{emoji} {name} - {desc}")
            print("─" * 60)
            
            if not items:
                print("   ❌ No results found")
                continue
            
            # Filter out accessories for iPhone searches
            filtered_items = self._filter_accessories(items, results.get('metadata', {}).get('product', ''))
            
            if not filtered_items:
                print("   ℹ️  Only accessories found (filtered out)")
                continue
            
            for item in filtered_items[:4]:  # Show max 4 per source
                all_items.append(item)
                
                # Price indicator
                price = item['price']
                price_indicator = self._get_price_indicator(price)
                
                print(f"{price_indicator} {item['name'][:70]}...")
                print(f"   💰 ₦{price:,.0f}")
                
                if source == 'jiji' and item.get('location'):
                    print(f"   📍 {item['location']}")
                elif source == 'konga' and item.get('seller'):
                    print(f"   🏪 {item['seller']}")
                
                if item.get('rating'):
                    print(f"   ⭐ {item['rating']}")
                
                # Show if it's from Selenium
                if 'selenium' in item.get('source', ''):
                    print(f"   🤖 Live data")
                
                print()
        
        # Price analysis and best deal
        if all_items:
            self._show_best_deal(all_items, results.get('metadata', {}))
        else:
            print("\n⚠️  No real products found across all marketplaces")
    
    def _filter_accessories(self, items: List[Dict], product_name: str) -> List[Dict]:
        """Filter out accessories to show only main products"""
        if not items:
            return []
        
        product_lower = product_name.lower()
        
        # Only filter for iPhone searches
        if 'iphone' not in product_lower:
            return items
        
        filtered = []
        for item in items:
            name = item['name'].lower()
            
            # Skip obvious accessories
            accessory_keywords = [
                'case', 'cover', 'charger', 'cable', 'protector',
                'pouch', 'holder', 'stand', 'otterbox', 'spigen',
                'tempered glass', 'screen protector'
            ]
            
            is_accessory = any(keyword in name for keyword in accessory_keywords)
            
            # Also check price - real iPhones are expensive
            if 'iphone' in name and item['price'] < 50000:
                is_accessory = True
            
            if not is_accessory:
                filtered.append(item)
        
        return filtered
    
    def _get_price_indicator(self, price: float) -> str:
        """Get visual price indicator"""
        if price < 10000:
            return "💸"  # Very cheap
        elif price < 50000:
            return "💰"  # Affordable
        elif price < 150000:
            return "💎"  # Mid-range
        elif price < 300000:
            return "🏆"  # Premium
        else:
            return "👑"  # Luxury
    
    def _show_best_deal(self, all_items, metadata):
        """Show best deal and analysis"""
        if not all_items:
            return
        
        # Find best deals
        cheapest = min(all_items, key=lambda x: x['price'])
        most_expensive = max(all_items, key=lambda x: x['price'])
        
        print("\n" + "=" * 80)
        print("🏆 BEST DEAL FOUND!")
        print("=" * 80)
        
        print(f"\n🔥 CHEAPEST OPTION:")
        print(f"📦 {cheapest['name'][:80]}")
        print(f"💰 PRICE: ₦{cheapest['price']:,.0f}")
        print(f"🏪 FROM: {cheapest['source'].upper()}")
        
        if cheapest.get('location'):
            print(f"📍 {cheapest['location']}")
        
        # Show savings
        savings = most_expensive['price'] - cheapest['price']
        if savings > 0:
            savings_percent = (savings / most_expensive['price']) * 100
            print(f"💵 SAVINGS: ₦{savings:,.0f} ({savings_percent:.0f}% cheaper)")
        
        # Price statistics
        prices = [item['price'] for item in all_items]
        avg_price = sum(prices) / len(prices)
        median_price = sorted(prices)[len(prices) // 2]
        
        print(f"\n📊 PRICE ANALYSIS:")
        print(f"   Items analyzed: {len(all_items)}")
        print(f"   Average price: ₦{avg_price:,.0f}")
        print(f"   Median price: ₦{median_price:,.0f}")
        print(f"   Price range: ₦{min(prices):,.0f} - ₦{max(prices):,.0f}")
        
        # Recommendation
        print(f"\n💡 RECOMMENDATION:")
        if cheapest['source'] == 'jumia':
            print("   ✅ Buy from Jumia - Verified seller with warranty")
        elif cheapest['source'] == 'konga':
            print("   ⚠️  Buy from Konga - Good price but check seller ratings")
        elif cheapest['source'] == 'jiji':
            print("   ⚠️  Buy from Jiji - Best price but meet in safe location")
        
        # Show other good options
        print(f"\n🎯 OTHER GOOD OPTIONS:")
        
        # Sort by value (price/quality)
        sorted_by_value = sorted(all_items, key=lambda x: x['price'])
        for i, item in enumerate(sorted_by_value[1:4], 2):  # Skip cheapest, show next 3
            if item['price'] < avg_price * 1.2:  # Within 20% of average
                print(f"{i}. {item['name'][:60]}...")
                print(f"   💰 ₦{item['price']:,.0f} on {item['source'].upper()}")
    
    def save_results(self, results, product_name: str):
        """Save results to JSON file"""
        os.makedirs('engine/data', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"engine/data/REAL_{product_name.replace(' ', '_')}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 REAL data saved to: {filename}")
        return filename
    
    def close_all(self):
        """Close all Selenium drivers"""
        if hasattr(self, 'jiji') and self.jiji:
            self.jiji.close()
        if hasattr(self, 'konga') and self.konga:
            self.konga.close()
        print("✅ All scrapers closed")

# Quick test function
def quick_test():
    """Quick test of the real system"""
    print("\n🧪 QUICK TEST - REAL DATA")
    print("=" * 50)
    
    system = RealPriceSystem(headless=True)
    
    try:
        # Quick search
        results = system.search_all_sequential("iPhone 13", max_results=4)
        
        print("\n📊 QUICK RESULTS:")
        for source, items in results.items():
            if source != 'metadata':
                real_items = len([i for i in items if i.get('price', 0) > 0])
                print(f"  {source.upper()}: {real_items} items")
                if items:
                    prices = [i['price'] for i in items if i.get('price')]
                    if prices:
                        print(f"    Price range: ₦{min(prices):,.0f} - ₦{max(prices):,.0f}")
        
        system.close_all()
        print("\n✅ Quick test complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        system.close_all()

# Run the complete system
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Real Price Comparison System')
    parser.add_argument('product', nargs='?', default='iPhone 13', help='Product to search for')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--parallel', action='store_true', help='Use parallel scraping')
    parser.add_argument('--test', action='store_true', help='Run quick test')
    
    args = parser.parse_args()
    
    if args.test:
        quick_test()
        sys.exit(0)
    
    product = args.product
    headless = args.headless
    
    print(f"\n🎯 Searching for: {product}")
    print("🔄 Initializing REAL scrapers (this may take a moment)...")
    
    system = RealPriceSystem(headless=headless)
    
    try:
        # Choose scraping method
        if args.parallel:
            print("⚡ Using PARALLEL scraping for speed...")
            results = system.search_all_parallel(product, max_results=6)
        else:
            print("🔍 Using SEQUENTIAL scraping for reliability...")
            results = system.search_all_sequential(product, max_results=6)
        
        # Display results
        system.display_comparison(results)
        
        # Save results
        system.save_results(results, product)
        
        print("\n✅ REAL scraping complete! All data is ACTUAL, not mock!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        system.close_all()
        print("\n🛍️  Happy shopping with REAL data! 🎯")