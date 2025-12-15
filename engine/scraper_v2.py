import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
from typing import List, Dict, Optional
from sqlmodel import Session
from app.database import get_session
from app.models import CompetitorPrice, DataTier
from datetime import datetime, timedelta

class JijiScraper:
    """Scraper for Jiji.ng marketplace"""
    
    def __init__(self):
        self.base_url = "https://jiji.ng"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def scrape_product(self, product_name: str, max_results: int = 10) -> List[Dict]:
        """Scrape Jiji for product prices"""
        prices = []
        
        try:
            query = product_name.replace(' ', '+')
            search_url = f"{self.base_url}/search?query={query}"
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            listings = soup.find_all('div', class_='b-list-advert__gallery__item')[:max_results]
            
            for listing in listings:
                try:
                    price_elem = listing.find('div', class_='qa-advert-price')
                    if not price_elem:
                        continue
                    
                    price_text = price_elem.get_text(strip=True)
                    price = self._extract_price(price_text)
                    
                    if price:
                        link_elem = listing.find('a')
                        url = self.base_url + link_elem.get('href') if link_elem else ""
                        
                        # Extract seller verification status
                        seller_verified = bool(listing.find(['span', 'div'], class_=re.compile(r'verified|vip|badge', re.I)))
                        
                        # Extract seller join date
                        seller_joined = None
                        join_text = listing.find(text=re.compile(r'joined.*ago', re.I))
                        if join_text:
                            seller_joined = self._parse_join_date(join_text)
                        
                        # Determine tier
                        tier = DataTier.TIER_3_NOISE
                        if seller_verified or (seller_joined and seller_joined < datetime.utcnow() - timedelta(days=180)):
                            tier = DataTier.TIER_2_MARKET
                        
                        prices.append({
                            'price': price,
                            'url': url,
                            'source': 'Jiji',
                            'tier': tier,
                            'seller_is_verified': seller_verified,
                            'seller_joined_date': seller_joined
                        })
                
                except Exception as e:
                    print(f"Error parsing Jiji listing: {e}")
                    continue
        
        except Exception as e:
            print(f"Error scraping Jiji: {e}")
        
        return prices
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        price_clean = re.sub(r'[₦,\s]', '', price_text)
        numbers = re.findall(r'\d+', price_clean)
        
        if numbers:
            return float(''.join(numbers))
        
        return None
    
    def _parse_join_date(self, join_text: str) -> Optional[datetime]:
        """Parse 'Joined X months ago' text to datetime"""
        try:
            if 'month' in join_text.lower():
                months = re.search(r'(\d+)', join_text)
                if months:
                    months_ago = int(months.group(1))
                    return datetime.utcnow() - timedelta(days=months_ago * 30)
            elif 'year' in join_text.lower():
                years = re.search(r'(\d+)', join_text)
                if years:
                    years_ago = int(years.group(1))
                    return datetime.utcnow() - timedelta(days=years_ago * 365)
        except:
            pass
        return None

class JumiaScraper:
    """Scraper for Jumia.com.ng marketplace"""
    
    def __init__(self):
        self.base_url = "https://www.jumia.com.ng"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def scrape_product(self, product_name: str, max_results: int = 10) -> List[Dict]:
        """Scrape Jumia for product prices"""
        prices = []
        
        try:
            query = product_name.replace(' ', '%20')
            search_url = f"{self.base_url}/catalog/?q={query}"
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            listings = soup.find_all('article', class_='prd')[:max_results]
            
            for listing in listings:
                try:
                    price_elem = listing.find('div', class_='prc')
                    if not price_elem:
                        continue
                    
                    price_text = price_elem.get_text(strip=True)
                    price = self._extract_price(price_text)
                    
                    if price:
                        link_elem = listing.find('a', class_='core')
                        url = self.base_url + link_elem.get('href') if link_elem else ""
                        
                        # Check stock status
                        out_of_stock = bool(listing.find(['span', 'div'], text=re.compile(r'out of stock|unavailable|sold out', re.I)))
                        if not out_of_stock:
                            cart_btn = listing.find(['button', 'a'], class_=re.compile(r'add.*cart|buy', re.I))
                            if cart_btn and ('disabled' in cart_btn.get('class', []) or cart_btn.get('disabled')):
                                out_of_stock = True
                        
                        prices.append({
                            'price': price,
                            'url': url,
                            'source': 'Jumia',
                            'tier': DataTier.TIER_1_TRUTH,
                            'is_out_of_stock': out_of_stock,
                            'seller_is_verified': True
                        })
                
                except Exception as e:
                    print(f"Error parsing Jumia listing: {e}")
                    continue
        
        except Exception as e:
            print(f"Error scraping Jumia: {e}")
        
        return prices
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        price_clean = re.sub(r'[₦,\s]', '', price_text)
        numbers = re.findall(r'\d+', price_clean)
        
        if numbers:
            return float(''.join(numbers))
        
        return None

class ScraperManager:
    """Main scraper coordinator"""
    
    def __init__(self):
        self.jiji_scraper = JijiScraper()
        self.jumia_scraper = JumiaScraper()
    
    def scrape_all(self, product_name: str, product_id: int) -> int:
        """Scrape all sources and save to database"""
        total_prices = 0
        
        try:
            with next(get_session()) as session:
                print(f"Scraping Jiji for: {product_name}")
                jiji_prices = self.jiji_scraper.scrape_product(product_name)
                total_prices += self._save_prices(session, jiji_prices, product_id)
                
                print(f"Scraping Jumia for: {product_name}")
                jumia_prices = self.jumia_scraper.scrape_product(product_name)
                total_prices += self._save_prices(session, jumia_prices, product_id)
                
                session.commit()
                print(f"Saved {total_prices} prices for {product_name}")
        
        except Exception as e:
            print(f"Error in scrape_all: {e}")
        
        return total_prices
    
    def _save_prices(self, session: Session, prices: List[Dict], product_id: int) -> int:
        """Save scraped prices to database"""
        saved_count = 0
        
        for price_data in prices:
            try:
                competitor_price = CompetitorPrice(
                    product_id=product_id,
                    source=price_data['source'],
                    price=price_data['price'],
                    url=price_data.get('url', ''),
                    scraped_at=datetime.utcnow(),
                    tier=price_data.get('tier', DataTier.TIER_3_NOISE),
                    is_out_of_stock=price_data.get('is_out_of_stock', False),
                    seller_is_verified=price_data.get('seller_is_verified', False),
                    seller_joined_date=price_data.get('seller_joined_date')
                )
                
                session.add(competitor_price)
                saved_count += 1
            
            except Exception as e:
                print(f"Error saving price: {e}")
                continue
        
        return saved_count