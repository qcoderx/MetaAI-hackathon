import instaloader
import os
import tempfile
from datetime import datetime, timedelta
from typing import List, Optional
from sqlmodel import Session
from app.database import get_session
from app.models import CompetitorPrice
from engine.ocr_scraper import InstagramOCRScraper

class InstagramCompetitorMonitor:
    """Monitor competitor Instagram accounts for price posts"""
    
    def __init__(self):
        self.loader = instaloader.Instaloader()
        self.ocr_scraper = InstagramOCRScraper()
        
        # Try to load session if exists
        try:
            self.loader.load_session_from_file("naira_sniper")
        except FileNotFoundError:
            print("No Instagram session found, using anonymous access")
    
    def fetch_recent_posts(self, username: str, max_posts: int = 3) -> List[str]:
        """
        Fetch recent post images from Instagram profile
        Returns list of downloaded image paths
        """
        image_paths = []
        
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            
            # Get posts from last 7 days
            cutoff_date = datetime.now() - timedelta(days=7)
            
            for post in profile.get_posts():
                if len(image_paths) >= max_posts:
                    break
                
                if post.date < cutoff_date:
                    break
                
                # Download post image to temp directory with unique name
                import uuid
                temp_filename = f"temp_ig_{uuid.uuid4().hex[:8]}.jpg"
                try:
                    self.loader.download_pic(temp_filename, post.url, post.date)
                    image_paths.append(temp_filename)
                except Exception as e:
                    print(f"Error downloading image: {e}")
                    continue
        
        except Exception as e:
            print(f"Error fetching Instagram posts for {username}: {e}")
        
        return image_paths
    
    def extract_prices_from_images(self, image_paths: List[str]) -> List[float]:
        """Extract prices from downloaded images using OCR"""
        prices = []
        
        for image_path in image_paths:
            try:
                price = self.ocr_scraper.extract_price_from_image(image_path)
                if price and price > 0:
                    prices.append(price)
            except Exception as e:
                print(f"Error extracting price from {image_path}: {e}")
            finally:
                # Clean up temp file
                try:
                    os.unlink(image_path)
                except:
                    pass
        
        return prices
    
    def monitor_competitor(self, username: str, product_id: int) -> int:
        """
        Monitor competitor Instagram and save prices to database
        Returns number of prices found
        """
        print(f"Monitoring Instagram @{username} for product {product_id}")
        
        # Fetch recent posts
        image_paths = self.fetch_recent_posts(username)
        
        if not image_paths:
            print(f"No recent images found for @{username}")
            return 0
        
        # Extract prices
        prices = self.extract_prices_from_images(image_paths)
        
        if not prices:
            print(f"No prices extracted from @{username} images")
            return 0
        
        # Save to database
        with next(get_session()) as session:
            for price in prices:
                competitor_price = CompetitorPrice(
                    product_id=product_id,
                    source=f"Instagram @{username}",
                    price=price,
                    url=f"https://instagram.com/{username}",
                    scraped_at=datetime.utcnow()
                )
                session.add(competitor_price)
            
            session.commit()
        
        print(f"Saved {len(prices)} prices from @{username}: {prices}")
        return len(prices)

def monitor_instagram_competitors(competitors: List[tuple]) -> int:
    """
    Monitor multiple Instagram competitors
    
    Args:
        competitors: List of (username, product_id) tuples
    
    Returns:
        Total number of prices found
    """
    monitor = InstagramCompetitorMonitor()
    total_prices = 0
    
    for username, product_id in competitors:
        try:
            count = monitor.monitor_competitor(username, product_id)
            total_prices += count
        except Exception as e:
            print(f"Error monitoring @{username}: {e}")
    
    return total_prices

# Example usage
if __name__ == "__main__":
    # Example competitor list: (instagram_username, product_id)
    competitors = [
        ("techstore_ng", 1),  # Oraimo Power Bank
        ("gadgetworld_lagos", 1),
        ("phoneaccessories_ng", 1)
    ]
    
    total = monitor_instagram_competitors(competitors)
    print(f"Total prices extracted: {total}")