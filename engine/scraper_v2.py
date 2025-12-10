# engine/scraper_v2.py - ENHANCED VERSION WITH SELENIUM
import requests
from bs4 import BeautifulSoup
import logging
import time
import random
from typing import List, Dict, Optional
import json
import os
from datetime import datetime
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('engine/logs/scraper_selenium.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BaseScraper:
    """Base class with common methods"""
    
    def __init__(self):
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Setup session headers"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.session.headers.update(headers)
    
    def _random_delay(self):
        """Random delay to avoid blocking"""
        time.sleep(random.uniform(2, 4))
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Extract numeric price from text"""
        if not text:
            return None
        
        try:
            # Find all numbers with commas
            matches = re.findall(r'[\d,]+\.?\d*', text)
            if matches:
                # Get the first number and clean it
                price_str = matches[0].replace(',', '')
                return float(price_str)
        except:
            pass
        return None
# Replace the entire JumiaScraper class with this ROBUST version:

class JumiaScraper(BaseScraper):
    """ROBUST Jumia scraper that finds ACTUAL products, not accessories"""
    
    BASE_URL = "https://www.jumia.com.ng"
    
    def search_product(self, product_name: str, max_results: int = 10) -> List[Dict]:
        """Search product on Jumia - ROBUST VERSION"""
        logger.info(f"🔍 Searching Jumia ROBUSTLY for: {product_name}")
        
        # Get clean search query
        clean_query = self._clean_search_query(product_name)
        
        # Try MULTIPLE strategies to find actual products
        strategies = [
            self._search_smart_category,  # Smart category search
            self._search_with_price_filter,  # Price filtering
            self._search_alternate_queries,  # Alternate queries
            self._search_direct_category,  # Direct category
        ]
        
        all_results = []
        for strategy in strategies:
            if len(all_results) >= max_results:
                break
                
            try:
                results = strategy(clean_query, product_name, max_results)
                if results:
                    logger.info(f"✅ Strategy found {len(results)} items")
                    all_results.extend(results)
                    
                    # Remove duplicates
                    seen = set()
                    unique_results = []
                    for item in all_results:
                        key = (item['name'][:50], item['price'])
                        if key not in seen:
                            seen.add(key)
                            unique_results.append(item)
                    all_results = unique_results
                    
            except Exception as e:
                logger.debug(f"Strategy failed: {e}")
                continue
        
        # If we still have no results, fall back to basic search
        if not all_results:
            logger.info("Falling back to basic search")
            all_results = self._search_basic(clean_query, max_results)
        
        # Final filtering
        filtered_results = self._filter_final_results(all_results, product_name, max_results)
        
        logger.info(f"🎯 Jumia ROBUST: Found {len(filtered_results)} relevant products")
        return filtered_results
    
    def _clean_search_query(self, product_name: str) -> str:
        """Clean search query for better results"""
        # Remove common words that cause accessory results
        words = product_name.lower().split()
        
        # Words that often lead to accessories
        accessory_words = ['case', 'cover', 'charger', 'cable', 'protector']
        filtered_words = [w for w in words if w not in accessory_words]
        
        # Add "official" or "original" for better results
        if 'iphone' in product_name.lower():
            filtered_words.append('apple')
        
        return ' '.join(filtered_words) if filtered_words else product_name
    
    def _search_smart_category(self, query: str, original_query: str, max_results: int) -> List[Dict]:
        """Search in specific categories based on product type"""
        category_map = {
            'iphone': '/mobile-phones/apple/',
            'samsung': '/mobile-phones/samsung/',
            'tecno': '/mobile-phones/tecno/',
            'infinix': '/mobile-phones/infinix/',
            'laptop': '/computing/laptops/',
            'power bank': '/mobile-phones/power-banks/',
            'watch': '/watches/',
            'tv': '/electronics/tvs/',
        }
        
        original_lower = original_query.lower()
        for keyword, category in category_map.items():
            if keyword in original_lower:
                try:
                    url = f"{self.BASE_URL}{category}"
                    logger.info(f"📁 Searching in category: {category}")
                    
                    response = self.session.get(url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    products = soup.select('article.prd')[:max_results * 2]
                    if products:
                        parsed = self._parse_products(products)
                        # Filter for our specific query
                        filtered = self._filter_by_query(parsed, original_query)
                        if filtered:
                            return filtered[:max_results]
                except:
                    continue
        
        return []
    
    def _search_with_price_filter(self, query: str, original_query: str, max_results: int) -> List[Dict]:
        """Search with price filtering to exclude cheap accessories"""
        try:
            search_url = f"{self.BASE_URL}/catalog/?q={query.replace(' ', '-')}"
            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            all_products = soup.select('article.prd')[:max_results * 3]
            if not all_products:
                return []
            
            # Parse all
            all_parsed = self._parse_products(all_products)
            
            # Filter by price thresholds based on product type
            original_lower = original_query.lower()
            
            if 'iphone' in original_lower:
                # Real iPhones are rarely under ₦100,000
                filtered = [p for p in all_parsed if p['price'] > 100000]
                if filtered:
                    logger.info(f"💰 Price filter: {len(filtered)} items over ₦100,000")
                    return filtered[:max_results]
            
            elif 'samsung' in original_lower and 'galaxy' in original_lower:
                # Samsung Galaxy phones are usually > ₦50,000
                filtered = [p for p in all_parsed if p['price'] > 50000]
                if filtered:
                    return filtered[:max_results]
            
            elif 'laptop' in original_lower:
                # Laptops are usually > ₦80,000
                filtered = [p for p in all_parsed if p['price'] > 80000]
                if filtered:
                    return filtered[:max_results]
            
            # Return all if no price filter applies
            return all_parsed[:max_results]
            
        except Exception as e:
            logger.error(f"Price filter search failed: {e}")
            return []
    
    def _search_alternate_queries(self, query: str, original_query: str, max_results: int) -> List[Dict]:
        """Try alternate search queries"""
        original_lower = original_query.lower()
        alternate_queries = []
        
        if 'iphone' in original_lower:
            # Try different iPhone search variations
            import re
            model_match = re.search(r'iphone\s+(\d+)', original_lower)
            if model_match:
                model = model_match.group(1)
                alternate_queries = [
                    f"apple iphone {model}",
                    f"iphone {model} apple",
                    f"iphone {model} original",
                    f"iphone {model} brand new"
                ]
            else:
                alternate_queries = ["apple iphone", "iphone original", "iphone brand new"]
        
        elif 'samsung' in original_lower:
            alternate_queries = ["samsung galaxy", "samsung phone"]
        
        results = []
        for alt_query in alternate_queries[:2]:  # Try first 2 alternates
            try:
                alt_results = self._search_basic(alt_query, max_results)
                if alt_results:
                    # Filter to match original query
                    filtered = self._filter_by_query(alt_results, original_query)
                    if filtered:
                        results.extend(filtered)
            except:
                continue
        
        return results[:max_results]
    
    def _search_direct_category(self, query: str, original_query: str, max_results: int) -> List[Dict]:
        """Search directly in mobile phones category"""
        try:
            # Go directly to mobile phones and search
            search_term = query.replace(' ', '%20')
            url = f"{self.BASE_URL}/mobile-phones/?q={search_term}"
            
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            products = soup.select('article.prd')[:max_results * 2]
            if products:
                parsed = self._parse_products(products)
                filtered = self._filter_by_query(parsed, original_query)
                if filtered:
                    logger.info(f"📱 Mobile category search: {len(filtered)} items")
                    return filtered[:max_results]
        except:
            pass
        
        return []
    
    def _search_basic(self, query: str, max_results: int) -> List[Dict]:
        """Basic search as fallback"""
        try:
            search_url = f"{self.BASE_URL}/catalog/?q={query.replace(' ', '-')}"
            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            products = soup.select('article.prd')[:max_results]
            return self._parse_products(products)
        except:
            return []
    
    def _parse_products(self, products) -> List[Dict]:
        """Parse list of product elements"""
        results = []
        for product in products:
            try:
                data = self._parse_single_product(product)
                if data and data.get('price'):
                    results.append(data)
            except Exception as e:
                logger.debug(f"Parse error: {e}")
                continue
        
        return results
    
    def _parse_single_product(self, product) -> Optional[Dict]:
        """Parse single Jumia product"""
        try:
            # Name
            name_elem = product.select_one('.name')
            if not name_elem:
                return None
            name = name_elem.get_text(strip=True)
            
            # Price
            price_elem = product.select_one('.prc')
            if not price_elem:
                return None
            price_text = price_elem.get_text(strip=True)
            price = self._extract_price(price_text)
            
            if not price:
                return None
            
            # URL
            url = ""
            link = product.select_one('a[href]')
            if link:
                url = link['href']
                if url and not url.startswith('http'):
                    url = f"{self.BASE_URL}{url}"
            
            # Image
            image_url = ""
            img = product.select_one('img')
            if img:
                image_url = img.get('data-src') or img.get('src', '')
                if image_url.startswith('//'):
                    image_url = f"https:{image_url}"
            
            # Rating
            rating = ""
            rating_elem = product.select_one('.stars')
            if rating_elem:
                rating = rating_elem.get_text(strip=True)
            
            # Determine if it's likely an accessory
            is_accessory = self._is_accessory(name, price)
            
            return {
                'name': name[:150],
                'price': price,
                'price_text': price_text,
                'url': url,
                'image_url': image_url,
                'rating': rating,
                'is_accessory': is_accessory,
                'source': 'jumia',
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Single product parse error: {e}")
            return None
    
    def _is_accessory(self, name: str, price: float) -> bool:
        """Determine if product is likely an accessory"""
        name_lower = name.lower()
        
        # Common accessory keywords
        accessory_keywords = [
            'case', 'cover', 'charger', 'cable', 'adapter',
            'protector', 'pouch', 'holder', 'stand', 'skin',
            'tempered glass', 'screen protector', 'battery',
            'casing', 'jack', 'dock', 'mount', 'otterbox',
            'spigen', 'ring', 'grip', 'strap', 'glass'
        ]
        
        # Check keywords
        for keyword in accessory_keywords:
            if keyword in name_lower:
                return True
        
        # Check for "for iPhone/Samsung" pattern
        if re.search(r'for\s+(iphone|samsung|android)', name_lower):
            return True
        
        # Price-based heuristics
        if 'iphone' in name_lower and price < 50000:
            return True  # Too cheap for real iPhone
        
        if 'samsung' in name_lower and 'galaxy' in name_lower and price < 30000:
            return True  # Too cheap for real Samsung
        
        return False
    
    def _filter_by_query(self, products: List[Dict], original_query: str) -> List[Dict]:
        """Filter products to match original query"""
        if not products:
            return []
        
        original_lower = original_query.lower()
        query_words = original_lower.split()
        
        filtered = []
        for product in products:
            name_lower = product['name'].lower()
            
            # Check how many query words match
            matches = sum(1 for word in query_words if word in name_lower)
            
            # If searching for iPhone, be stricter
            if 'iphone' in original_lower:
                if 'iphone' not in name_lower:
                    continue
                # Exclude obvious accessories
                if product.get('is_accessory', False):
                    continue
            
            # If at least one word matches (or all for short queries)
            if matches >= max(1, len(query_words) // 2):
                filtered.append(product)
        
        return filtered
    
    def _filter_final_results(self, all_results: List[Dict], product_name: str, max_results: int) -> List[Dict]:
        """Final filtering and sorting"""
        if not all_results:
            return []
        
        product_lower = product_name.lower()
        
        # Score each result
        scored_results = []
        for result in all_results:
            score = self._score_result(result, product_lower)
            scored_results.append((score, result))
        
        # Sort by score (descending)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Take top results
        final_results = [result for _, result in scored_results[:max_results]]
        
        # Log what we found
        if final_results:
            logger.info(f"🏆 Top result: {final_results[0]['name'][:60]}...")
            logger.info(f"💰 Price range: ₦{min(r['price'] for r in final_results):,.0f} - ₦{max(r['price'] for r in final_results):,.0f}")
        
        return final_results
    
    def _score_result(self, result: Dict, query: str) -> float:
        """Score a result based on relevance"""
        score = 0.0
        name = result['name'].lower()
        price = result['price']
        
        # Query matching
        query_words = query.split()
        matches = sum(1 for word in query_words if word in name)
        score += matches * 10
        
        # Exact phrase match bonus
        if all(word in name for word in query_words):
            score += 50
        
        # Price-based scoring
        if 'iphone' in query:
            if price > 100000:
                score += 30  # Real iPhone price
            elif price > 50000:
                score += 10
            else:
                score -= 20  # Too cheap
        
        # Brand matching
        if 'apple' in name and 'iphone' in query:
            score += 20
        
        # Penalize accessories
        if result.get('is_accessory', False):
            score -= 40
        
        # Rating bonus
        if result.get('rating'):
            try:
                rating_val = float(result['rating'][:3])
                score += rating_val * 5
            except:
                pass
        
        return score

class SeleniumBaseScraper(BaseScraper):
    """Base class for Selenium scrapers"""
    
    def __init__(self, headless: bool = True):
        super().__init__()
        self.headless = headless
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver"""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless")
        
        # Anti-detection settings
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Stealth mode
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Catalina-compatible options
        options.add_argument("--disable-software-rasterizer")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Execute stealth script
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            logger.info("✅ Selenium driver initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Selenium: {e}")
            raise
    
    def _scroll_page(self, scroll_pause_time: float = 2):
        """Scroll page to load dynamic content"""
        try:
            # Get scroll height
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Scroll slowly
            for i in range(3):  # Scroll 3 times
                # Scroll to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Scroll back up a bit
            self.driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(1)
            
        except Exception as e:
            logger.warning(f"Scrolling failed: {e}")
    
    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()
            logger.info("✅ Selenium driver closed")
    
    def __del__(self):
        """Destructor to ensure driver is closed"""
        try:
            self.close()
        except:
            pass

class KongaSeleniumScraper(SeleniumBaseScraper):
    """Konga scraper using Selenium"""
    
    BASE_URL = "https://www.konga.com"
    
    def search_product(self, product_name: str, max_results: int = 10) -> List[Dict]:
        """Search product on Konga using Selenium"""
        logger.info(f"🔍 Searching Konga (Selenium) for: {product_name}")
        results = []
        
        try:
            search_query = product_name.replace(' ', '%20')
            url = f"{self.BASE_URL}/search?search={search_query}"
            
            logger.info(f"🌐 Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(random.uniform(3, 5))
            
            # Check for blocking/CAPTCHA
            page_source = self.driver.page_source.lower()
            if 'captcha' in page_source:
                logger.warning("🛡️ CAPTCHA detected on Konga")
                self._handle_captcha()
                time.sleep(5)
            
            # Scroll to load products
            self._scroll_page()
            
            # Wait for products to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div._7e3920c, article.product, [data-testid*='product']"))
                )
            except TimeoutException:
                logger.warning("Products not found with standard selectors")
            
            # Get page source and parse
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Try multiple selectors for Konga products
            selectors = [
                'div._7e3920c',  # Konga's main product div
                'article.product',
                'div[data-testid*="product"]',
                'div.product-card',
                'div._5f872f9'   # Another Konga class
            ]
            
            products = []
            for selector in selectors:
                found = soup.select(selector)
                if found:
                    logger.info(f"✅ Konga Selenium: Found {len(found)} products with selector: {selector}")
                    products = found[:max_results]
                    break
            
            if not products:
                # Try to find product links as fallback
                product_links = soup.find_all('a', href=lambda x: x and '/product/' in str(x))
                if product_links:
                    products = product_links[:max_results]
                    logger.info(f"✅ Konga Selenium: Found {len(products)} product links")
                else:
                    logger.warning("❌ Konga Selenium: No products found")
                    return []
            
            logger.info(f"📦 Konga Selenium: Parsing {len(products)} products")
            
            # Parse products
            for i, product in enumerate(products):
                try:
                    product_data = self._parse_product(product)
                    if product_data and product_data.get('price'):
                        results.append(product_data)
                        logger.debug(f"✅ Parsed Konga product {i+1}/{len(products)}")
                        
                        # Take screenshot of first product (debug)
                        if i == 0 and not self.headless:
                            self.driver.save_screenshot('konga_first_product.png')
                        
                except Exception as e:
                    logger.error(f"❌ Error parsing Konga product {i+1}: {e}")
                    continue
                
                # Small delay between parsing
                time.sleep(random.uniform(0.5, 1.0))
            
            logger.info(f"✅ Konga Selenium: Successfully parsed {len(results)} products")
            
        except Exception as e:
            logger.error(f"❌ Konga Selenium search failed: {e}", exc_info=True)
        
        return results
    
    def _handle_captcha(self):
        """Handle CAPTCHA if detected"""
        try:
            if not self.headless:
                logger.info("🔄 Please solve CAPTCHA manually in the browser window...")
                input("Press Enter after solving CAPTCHA...")
            else:
                logger.warning("🤖 Running in headless mode, refreshing page...")
                self.driver.refresh()
                time.sleep(5)
        except Exception as e:
            logger.error(f"CAPTCHA handling failed: {e}")
    
        # Update the _parse_product method in KongaSeleniumScraper:

    # Update the KongaSeleniumScraper._parse_product method in scraper_v2.py:

    def _parse_product(self, product_element) -> Optional[Dict]:
        """Parse Konga product element - FIXED VERSION"""
        try:
            # If it's just an <a> tag (link), handle it differently
            if hasattr(product_element, 'name') and product_element.name == 'a':
                # Extract from link
                name = product_element.get_text(strip=True)
                url = product_element.get('href', '')
                
                if not name or not url:
                    return None
                
                # Clean name
                name = name.replace('...', '').strip()
                if len(name) < 5:
                    return None
                
                # For links, we might need to follow them to get price
                # But for now, let's return a basic item
                # Real price would need to be extracted by following the link
                return {
                    'name': name[:150],
                    'price': 0,  # Placeholder - would need to scrape product page
                    'price_text': 'Price not available',
                    'url': f"{self.BASE_URL}{url}" if url.startswith('/') else url,
                    'source': 'konga_selenium',
                    'scraped_at': datetime.now().isoformat()
                }
            
            # Original parsing for div elements
            if hasattr(product_element, 'prettify'):
                product_html = product_element.prettify()
            else:
                product_html = str(product_element)
            
            soup = BeautifulSoup(product_html, 'html.parser')
            
            # Try to find product card
            product_card = soup.select_one('div._7e3920c, article.product, div.product-card')
            if product_card:
                soup = BeautifulSoup(str(product_card), 'html.parser')
            
            # Extract name
            name = "N/A"
            name_selectors = [
                'h3[title]',
                'h3._2574f5d',
                'h3.name',
                'div[data-testid="productName"]',
                'h4',
                'a[title]'
            ]
            
            for selector in name_selectors:
                elem = soup.select_one(selector)
                if elem:
                    name = elem.get('title', elem.get_text(strip=True))
                    if name and name != "N/A":
                        break
            
            # Extract price
            price = None
            price_selectors = [
                'div._5c5c1a5',
                'div.price',
                'div[data-testid="productPrice"]',
                'span[class*="price"]',
                'div._678e4f6'
            ]
            
            for selector in price_selectors:
                elem = soup.select_one(selector)
                if elem:
                    price_text = elem.get_text(strip=True)
                    price = self._extract_price(price_text)
                    if price:
                        break
            
            # If still no price, check all text
            if not price:
                all_text = soup.get_text()
                price_match = re.search(r'₦\s*([\d,]+\.?\d*)', all_text)
                if price_match:
                    price_str = price_match.group(1).replace(',', '')
                    try:
                        price = float(price_str)
                    except:
                        pass
            
            if not price:
                logger.debug(f"Konga: No price found for: {name[:50]}")
                return None
            
            # Extract URL
            url = ""
            link_elem = soup.find('a', href=True)
            if link_elem:
                url = link_elem['href']
                if url and not url.startswith('http'):
                    url = f"{self.BASE_URL}{url}" if url.startswith('/') else f"{self.BASE_URL}/{url}"
            
            return {
                'name': name[:200],
                'price': price,
                'price_text': f"₦{price:,}",
                'url': url,
                'source': 'konga_selenium',
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Konga parse error: {e}")
            return None

class JijiSeleniumScraper(SeleniumBaseScraper):
    """Jiji scraper using Selenium (your working code)"""
    
    BASE_URL = "https://jiji.ng"
    
    def search_product(self, product_name: str, max_results: int = 10) -> List[Dict]:
        """Search product on Jiji using Selenium"""
        logger.info(f"🔍 Searching Jiji (Selenium) for: {product_name}")
        results = []
        
        try:
            search_query = product_name.replace(' ', '+')
            url = f"{self.BASE_URL}/search?query={search_query}"
            
            logger.info(f"🌐 Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(random.uniform(3, 5))
            
            # Check for CAPTCHA
            page_source = self.driver.page_source.lower()
            if 'captcha' in page_source or 'cloudflare' in page_source:
                logger.warning("🛡️ CAPTCHA detected on Jiji")
                self._handle_captcha()
                time.sleep(5)
            
            # Wait for listings to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".b-list-advert-base, [data-testid='product-card']"))
                )
            except:
                logger.warning("Listings not found with standard selector")
            
            # Scroll to load more content
            self._scroll_page()
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find listings
            listings = soup.select('.b-list-advert-base, [data-testid="product-card"], .listing-item')
            
            if not listings:
                # Try to find by href pattern
                all_links = soup.find_all('a', href=lambda x: x and '/item/' in str(x))
                listings = all_links[:max_results]
                logger.info(f"Found {len(listings)} listings via href pattern")
            
            logger.info(f"Found {len(listings)} total listings")
            
            # Parse listings
            for i, listing in enumerate(listings[:max_results]):
                try:
                    listing_data = self._parse_listing(listing)
                    if listing_data and listing_data.get('price'):
                        results.append(listing_data)
                        logger.debug(f"✅ Parsed Jiji listing {i+1}/{len(listings)}")
                        
                        # Take screenshot of first listing
                        if i == 0 and not self.headless:
                            self.driver.save_screenshot('jiji_first_listing.png')
                        
                except Exception as e:
                    logger.error(f"❌ Error parsing Jiji listing {i+1}: {e}")
                    continue
                
                # Random delay between parsing
                time.sleep(random.uniform(0.5, 1.5))
            
            logger.info(f"🎉 Jiji Selenium: Successfully parsed {len(results)} listings")
            
        except Exception as e:
            logger.error(f"❌ Jiji Selenium scraping failed: {e}", exc_info=True)
        
        return results
    
    def _handle_captcha(self):
        """Handle CAPTCHA if detected"""
        try:
            if not self.headless:
                logger.info("🔄 Please solve CAPTCHA manually in the browser window...")
                input("Press Enter after solving CAPTCHA...")
            else:
                logger.warning("🤖 Running in headless mode, refreshing page...")
                self.driver.refresh()
                time.sleep(5)
        except Exception as e:
            logger.error(f"CAPTCHA handling failed: {e}")
    
    # Update JijiSeleniumScraper's _parse_listing method:

    def _parse_listing(self, listing_element) -> Optional[Dict]:
        """Parse Jiji listing element - WITH FILTERING"""
        try:
            if hasattr(listing_element, 'prettify'):
                listing_html = listing_element.prettify()
            else:
                listing_html = str(listing_element)
            
            soup = BeautifulSoup(listing_html, 'html.parser')
            
            # Extract title
            title_elem = soup.select_one('.b-advert-title-inner, .title, h3, [class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else "N/A"
            
            # Extract price
            price_elem = soup.select_one('.qa-advert-price, .price, [class*="price"]')
            price_text = price_elem.get_text(strip=True) if price_elem else ""
            
            # Extract price using regex
            price_match = re.search(r'₦\s*([\d,]+)', price_text)
            if not price_match:
                # Look in all text
                all_text = soup.get_text()
                price_match = re.search(r'₦\s*([\d,]+)', all_text)
            
            price = None
            if price_match:
                price_str = price_match.group(1).replace(',', '')
                try:
                    price = float(price_str)
                except:
                    price = None
            
            if not price:
                return None
            
            # Filter out accessories if searching for iPhone
            # (This should be called from search_product with context)
            
            # Extract URL
            url = ""
            link_elem = soup.find('a', href=True)
            if link_elem:
                url = link_elem['href']
                if url and not url.startswith('http'):
                    url = f"{self.BASE_URL}{url}" if url.startswith('/') else f"{self.BASE_URL}/{url}"
            
            # Extract location
            location_elem = soup.select_one('.b-list-advert__region, .location, [class*="location"]')
            location = location_elem.get_text(strip=True) if location_elem else "N/A"
            
            return {
                'name': title[:200],
                'price': price,
                'price_text': price_text,
                'url': url,
                'location': location,
                'source': 'jiji_selenium',
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in _parse_listing: {e}")
            return None

class EnhancedScraperManager:
    """Manager for Selenium-enhanced scrapers"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.jumia = JumiaScraper()
        self.jiji = None
        self.konga = None
        self._init_selenium_scrapers()
        logger.info("🚀 Enhanced ScraperManager initialized")
    
    def _init_selenium_scrapers(self):
        """Initialize Selenium scrapers with error handling"""
        try:
            self.jiji = JijiSeleniumScraper(headless=self.headless)
            logger.info("✅ Jiji Selenium scraper initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Jiji Selenium: {e}")
            self.jiji = None
        
        try:
            self.konga = KongaSeleniumScraper(headless=self.headless)
            logger.info("✅ Konga Selenium scraper initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Konga Selenium: {e}")
            self.konga = None
    
    def scrape_all(self, product_name: str, max_results: int = 10) -> Dict[str, List[Dict]]:
        """Scrape from all marketplaces"""
        logger.info(f"🎯 Starting ENHANCED scrape for: {product_name}")
        
        results = {}
        
        # Jumia (always try - it works with requests)
        try:
            results['jumia'] = self.jumia.search_product(product_name, max_results)
        except Exception as e:
            logger.error(f"❌ Jumia failed: {e}")
            results['jumia'] = []
        
        # Jiji (Selenium)
        if self.jiji:
            try:
                results['jiji'] = self.jiji.search_product(product_name, max_results)
            except Exception as e:
                logger.error(f"❌ Jiji Selenium failed: {e}")
                results['jiji'] = []
        else:
            results['jiji'] = []
            logger.warning("⚠️ Jiji scraper not available")
        
        # Konga (Selenium)
        if self.konga:
            try:
                results['konga'] = self.konga.search_product(product_name, max_results)
            except Exception as e:
                logger.error(f"❌ Konga Selenium failed: {e}")
                results['konga'] = []
        else:
            results['konga'] = []
            logger.warning("⚠️ Konga scraper not available")
        
        # Log summary
        total_items = sum(len(items) for items in results.values())
        logger.info(f"📈 Total items scraped: {total_items}")
        
        for source, items in results.items():
            source_type = " (Selenium)" if source in ['jiji', 'konga'] and items else ""
            logger.info(f"✅ {source.upper()}{source_type}: {len(items)} items")
        
        return results
    
    def save_results(self, results: Dict[str, List[Dict]], product_name: str):
        """Save results to JSON file"""
        os.makedirs('engine/data', exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"engine/data/{product_name.replace(' ', '_')}_SELENIUM_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Saved results to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return None
    
    def close_all(self):
        """Close all Selenium drivers"""
        if self.jiji:
            self.jiji.close()
        if self.konga:
            self.konga.close()
        logger.info("✅ All Selenium drivers closed")
        
        

        
# Add this class at the end of engine/scraper_v2.py
class ProductionScraperManager(EnhancedScraperManager):
    """Production-ready scraper manager with fallbacks"""
    
    def __init__(self, use_selenium: bool = True):
        self.use_selenium = use_selenium
        super().__init__(headless=True)  # Always headless in production
    
    def _init_selenium_scrapers(self):
        """Initialize Selenium with fallback"""
        try:
            # Jiji Selenium
            self.jiji = JijiSeleniumScraper(headless=True)  # HEADLESS for production
            logger.info("✅ Jiji Selenium initialized (headless)")
        except Exception as e:
            logger.error(f"Jiji Selenium failed: {e}, falling back to requests")
            # Create a dummy requests scraper for Jiji
            from engine.scraper import JijiScraper
            self.jiji = JijiScraper()  # Fallback to requests version
            
        try:
            # Konga Selenium
            self.konga = KongaSeleniumScraper(headless=True)  # HEADLESS for production
            logger.info("✅ Konga Selenium initialized (headless)")
        except Exception as e:
            logger.error(f"Konga Selenium failed: {e}, falling back to requests")
            # Create a dummy requests scraper for Konga
            from engine.scraper import KongaScraper
            self.konga = KongaScraper()  # Fallback to requests version