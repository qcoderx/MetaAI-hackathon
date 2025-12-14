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
from typing import List, Dict
from sqlmodel import Session
from app.database import get_session
from app.models import CompetitorPrice
from datetime import datetime

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
            # Format search query
            query = product_name.replace(' ', '+')
            search_url = f"{self.base_url}/search?query={query}"
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find product listings
            listings = soup.find_all('div', class_='b-list-advert__gallery__item')[:max_results]
            
            for listing in listings:
                try:
                    # Extract price
                    price_elem = listing.find('div', class_='qa-advert-price')
                    if not price_elem:
                        continue
                    
                    price_text = price_elem.get_text(strip=True)
                    price = self._extract_price(price_text)
                    
                    if price:
                        # Extract URL
                        link_elem = listing.find('a')
                        url = self.base_url + link_elem.get('href') if link_elem else ""
                        
                        prices.append({
                            'price': price,
                            'url': url,
                            'source': 'Jiji'
                        })
                
                except Exception as e:
                    print(f"Error parsing Jiji listing: {e}")
                    continue
        
        except Exception as e:
            print(f"Error scraping Jiji: {e}")
        
        return prices
    
    def _extract_price(self, price_text: str) -> float:
        """Extract numeric price from text"""
        # Remove currency symbols and commas
        price_clean = re.sub(r'[₦,\s]', '', price_text)
        
        # Extract numbers
        numbers = re.findall(r'\d+', price_clean)
        
        if numbers:
            return float(''.join(numbers))
        
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
            # Format search query
            query = product_name.replace(' ', '%20')
            search_url = f"{self.base_url}/catalog/?q={query}"
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find product listings
            listings = soup.find_all('article', class_='prd')[:max_results]
            
            for listing in listings:
                try:
                    # Extract price
                    price_elem = listing.find('div', class_='prc')
                    if not price_elem:
                        continue
                    
                    price_text = price_elem.get_text(strip=True)
                    price = self._extract_price(price_text)
                    
                    if price:
                        # Extract URL
                        link_elem = listing.find('a', class_='core')
                        url = self.base_url + link_elem.get('href') if link_elem else ""
                        
                        prices.append({
                            'price': price,
                            'url': url,
                            'source': 'Jumia'
                        })
                
                except Exception as e:
                    print(f"Error parsing Jumia listing: {e}")
                    continue
        
        except Exception as e:
            print(f"Error scraping Jumia: {e}")
        
        return prices
    
    def _extract_price(self, price_text: str) -> float:
        """Extract numeric price from text"""
        # Remove currency symbols and commas
        price_clean = re.sub(r'[₦,\s]', '', price_text)
        
        # Extract numbers
        numbers = re.findall(r'\d+', price_clean)
        
        if numbers:
            return float(''.join(numbers))
        
        return None

class SeleniumScraper:
    """Selenium-based scraper for JavaScript-heavy sites"""
    
    def __init__(self):
        self.driver = None
    
    def _setup_driver(self):
        """Setup Chrome driver with options"""
        if self.driver:
            return
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def scrape_dynamic_site(self, url: str, product_name: str) -> List[Dict]:
        """Scrape sites that require JavaScript execution"""
        prices = []
        
        try:
            self._setup_driver()
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Search for product
            search_box = self.driver.find_element(By.CSS_SELECTOR, "input[type='search'], input[name='q'], input[placeholder*='search']")
            search_box.clear()
            search_box.send_keys(product_name)
            search_box.submit()
            
            time.sleep(3)  # Wait for results
            
            # Extract prices (generic selectors)
            price_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='price'], [class*='cost'], [class*='amount']")
            
            for elem in price_elements[:10]:
                try:
                    price_text = elem.text.strip()
                    price = self._extract_price(price_text)
                    
                    if price and price > 1000:  # Filter out invalid prices
                        prices.append({
                            'price': price,
                            'url': self.driver.current_url,
                            'source': 'Dynamic Site'
                        })
                
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"Error with Selenium scraping: {e}")
        
        return prices
    
    def _extract_price(self, price_text: str) -> float:
        """Extract numeric price from text"""
        # Remove currency symbols and commas
        price_clean = re.sub(r'[₦,\s]', '', price_text)
        
        # Extract numbers
        numbers = re.findall(r'\d+', price_clean)
        
        if numbers:
            return float(''.join(numbers))
        
        return None
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None

class ScraperManager:
    """Main scraper coordinator"""
    
    def __init__(self):
        self.jiji_scraper = JijiScraper()
        self.jumia_scraper = JumiaScraper()
        self.selenium_scraper = SeleniumScraper()
    
    def scrape_all(self, product_name: str, product_id: int) -> int:
        """Scrape all sources and save to database"""
        total_prices = 0
        
        try:
            with next(get_session()) as session:
                # Scrape Jiji
                print(f"Scraping Jiji for: {product_name}")
                jiji_prices = self.jiji_scraper.scrape_product(product_name)
                total_prices += self._save_prices(session, jiji_prices, product_id)
                
                # Scrape Jumia
                print(f"Scraping Jumia for: {product_name}")
                jumia_prices = self.jumia_scraper.scrape_product(product_name)
                total_prices += self._save_prices(session, jumia_prices, product_id)
                
                session.commit()
                print(f"Saved {total_prices} prices for {product_name}")
        
        except Exception as e:
            print(f"Error in scrape_all: {e}")
        
        finally:
            # Clean up Selenium driver
            self.selenium_scraper.close()
        
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
                    scraped_at=datetime.utcnow()
                )
                
                session.add(competitor_price)
                saved_count += 1
            
            except Exception as e:
                print(f"Error saving price: {e}")
                continue
        
        return saved_count
    
    def scrape_specific_site(self, url: str, product_name: str, product_id: int) -> int:
        """Scrape a specific website using Selenium"""
        try:
            with next(get_session()) as session:
                prices = self.selenium_scraper.scrape_dynamic_site(url, product_name)
                saved_count = self._save_prices(session, prices, product_id)
                session.commit()
                return saved_count
        
        except Exception as e:
            print(f"Error scraping specific site: {e}")
            return 0
        
        finally:
            self.selenium_scraper.close()