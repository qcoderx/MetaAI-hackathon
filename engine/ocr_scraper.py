# engine/ocr_scraper.py
"""
OCR Engine for scraping prices from Instagram screenshots
"""
import os
import cv2
import numpy as np
from PIL import Image
import pytesseract
import easyocr
import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import io
import requests
from urllib.parse import urlparse
import tempfile

# Configure Tesseract path (for macOS)
# pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'  # Uncomment if needed

logger = logging.getLogger(__name__)

class InstagramOCRScraper:
    """OCR scraper for Instagram competitor screenshots"""
    
    def __init__(self, use_easyocr: bool = True):
        """
        Initialize OCR scraper
        
        Args:
            use_easyocr: Use EasyOCR (better accuracy) if True, else use Tesseract
        """
        self.use_easyocr = use_easyocr
        
        if use_easyocr:
            # Initialize EasyOCR reader (English + numbers + currency symbols)
            logger.info("🔄 Initializing EasyOCR...")
            self.reader = easyocr.Reader(['en'], gpu=False)  # GPU=False for CPU mode
            logger.info("✅ EasyOCR initialized")
        else:
            logger.info("✅ Tesseract OCR ready")
    
    def extract_prices_from_image(self, image_path: str, product_keywords: List[str] = None) -> List[Dict]:
        """
        Extract prices and product info from an image
        
        Args:
            image_path: Path to image file or URL
            product_keywords: Keywords to look for (e.g., ['power bank', 'iphone'])
            
        Returns:
            List of price data dictionaries
        """
        try:
            # Load image
            if image_path.startswith(('http://', 'https://')):
                img = self._download_image(image_path)
            else:
                img = cv2.imread(image_path)
            
            if img is None:
                logger.error(f"❌ Could not load image: {image_path}")
                return []
            
            logger.info(f"📷 Processing image: {image_path}")
            
            # Preprocess image for better OCR
            processed_img = self._preprocess_image(img)
            
            # Extract text using OCR
            extracted_text = self._extract_text(processed_img)
            
            if not extracted_text:
                logger.warning("No text extracted from image")
                return []
            
            logger.info(f"📝 Extracted text: {extracted_text[:200]}...")
            
            # Extract prices from text
            price_data = self._extract_price_data(extracted_text, product_keywords)
            
            # If no prices found with OCR, try computer vision approach
            if not price_data:
                price_data = self._find_prices_with_cv(img, product_keywords)
            
            # Add metadata
            for item in price_data:
                item.update({
                    'source': 'instagram_ocr',
                    'image_source': image_path,
                    'extracted_at': datetime.now().isoformat(),
                    'confidence': 'ocr_high' if len(item.get('price_text', '')) > 0 else 'ocr_low'
                })
            
            logger.info(f"💰 Found {len(price_data)} price(s) in image")
            return price_data
            
        except Exception as e:
            logger.error(f"❌ OCR processing failed: {e}")
            return []
    
    def _download_image(self, url: str):
        """Download image from URL"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Convert to numpy array
            img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return img
            
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None
    
    def _preprocess_image(self, img):
        """Preprocess image for better OCR results"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply thresholding
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Morphological operations to remove noise
            kernel = np.ones((2, 2), np.uint8)
            morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # Resize if too small
            height, width = morph.shape
            if height < 100 or width < 100:
                morph = cv2.resize(morph, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
            
            return morph
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return img
    
    def _extract_text(self, img):
        """Extract text from image using OCR"""
        try:
            if self.use_easyocr:
                # Use EasyOCR
                results = self.reader.readtext(img, detail=0, paragraph=True)
                text = ' '.join(results)
            else:
                # Use Tesseract
                text = pytesseract.image_to_string(img, config='--psm 6')
            
            # Clean text
            text = ' '.join(text.split())  # Remove extra whitespace
            return text.lower()
            
        except Exception as e:
            logger.error(f"OCR text extraction failed: {e}")
            return ""
    
    def _extract_price_data(self, text: str, product_keywords: List[str] = None) -> List[Dict]:
        """
        Extract price data from OCR text
        
        Args:
            text: OCR extracted text
            product_keywords: Keywords to filter products
            
        Returns:
            List of price data dictionaries
        """
        price_data = []
        
        # Nigerian price patterns
        price_patterns = [
            r'(?:₦|ngn|naira|n)\s*([\d,]+\.?\d*)',  # ₦15,000 or N15000
            r'([\d,]+\.?\d*)\s*(?:₦|ngn|naira|n)',  # 15,000₦
            r'price\s*:?\s*(?:₦|ngn|naira|n)?\s*([\d,]+\.?\d*)',  # Price: ₦15,000
            r'([\d,]+\.?\d*)\s*(?:k|thousand)',  # 15k or 15 thousand
        ]
        
        # Find all price matches
        all_prices = []
        for pattern in price_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                price_str = match.group(1).replace(',', '')
                try:
                    price = float(price_str)
                    # Convert 'k' to thousands
                    if 'k' in match.group(0).lower() or 'thousand' in match.group(0).lower():
                        price *= 1000
                    
                    all_prices.append({
                        'price': price,
                        'price_text': match.group(0),
                        'position': match.start()
                    })
                except:
                    continue
        
        # Extract product names near prices
        for price_info in all_prices:
            # Extract context around price (50 characters before and after)
            start = max(0, price_info['position'] - 50)
            end = min(len(text), price_info['position'] + 50)
            context = text[start:end]
            
            # Try to extract product name from context
            product_name = self._extract_product_name(context, product_keywords)
            
            price_data.append({
                'price': price_info['price'],
                'price_text': price_info['price_text'],
                'product_name': product_name,
                'context': context,
                'source_text': text
            })
        
        # Filter by product keywords if provided
        if product_keywords and price_data:
            filtered_data = []
            for item in price_data:
                item_text = f"{item.get('product_name', '')} {item.get('context', '')}".lower()
                if any(keyword.lower() in item_text for keyword in product_keywords):
                    filtered_data.append(item)
            
            if filtered_data:
                return filtered_data
        
        return price_data
    
    def _extract_product_name(self, context: str, product_keywords: List[str] = None) -> str:
        """Extract product name from context"""
        # Common product patterns
        product_patterns = [
            r'(iphone\s+\d+\s*(?:pro|max|mini)?\s*\d*[a-z]*)',
            r'(samsung\s+galaxy\s+\w+\s*\d*)',
            r'(power\s+bank\s*\d*\s*[a-z]*)',
            r'(laptop\s+\w+\s*\d*)',
            r'(airpods\s*(?:pro|max)?)',
            r'(tv\s+\d+\s*inch)',
        ]
        
        # Try to match known product patterns
        for pattern in product_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # If keywords provided, look for them
        if product_keywords:
            for keyword in product_keywords:
                if keyword.lower() in context:
                    return keyword
        
        # Extract first few meaningful words
        words = context.split()
        if len(words) > 3:
            return ' '.join(words[:3]).strip()
        
        return "Unknown Product"
    
    def _find_prices_with_cv(self, img, product_keywords: List[str] = None) -> List[Dict]:
        """
        Find prices using computer vision techniques (template matching, etc.)
        """
        price_data = []
        
        try:
            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # Look for red text (common for prices/sales)
            # Red color range
            lower_red1 = np.array([0, 100, 100])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([160, 100, 100])
            upper_red2 = np.array([180, 255, 255])
            
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            red_mask = cv2.bitwise_or(mask1, mask2)
            
            # Look for green text (common for prices)
            lower_green = np.array([40, 40, 40])
            upper_green = np.array([80, 255, 255])
            green_mask = cv2.inRange(hsv, lower_green, upper_green)
            
            # Combine masks
            price_mask = cv2.bitwise_or(red_mask, green_mask)
            
            # Find contours (potential price regions)
            contours, _ = cv2.findContours(price_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours[:10]:  # Check first 10 contours
                area = cv2.contourArea(contour)
                if area < 100 or area > 5000:  # Filter by size
                    continue
                
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                
                # Extract region
                region = img[y:y+h, x:x+w]
                
                # Try OCR on this region
                region_text = self._extract_text(region)
                if region_text:
                    region_prices = self._extract_price_data(region_text, product_keywords)
                    price_data.extend(region_prices)
            
            # Remove duplicates
            unique_prices = []
            seen = set()
            for item in price_data:
                key = (item.get('price'), item.get('product_name', ''))
                if key not in seen:
                    seen.add(key)
                    unique_prices.append(item)
            
            return unique_prices
            
        except Exception as e:
            logger.error(f"CV price detection failed: {e}")
            return []
    
    def process_batch_images(self, image_paths: List[str], product_keywords: List[str] = None) -> Dict:
        """
        Process multiple images and aggregate results
        
        Args:
            image_paths: List of image paths/URLs
            product_keywords: Keywords to filter products
            
        Returns:
            Aggregated price analysis
        """
        all_prices = []
        
        for image_path in image_paths:
            try:
                prices = self.extract_prices_from_image(image_path, product_keywords)
                all_prices.extend(prices)
                
                logger.info(f"Processed {image_path}: {len(prices)} prices found")
                
            except Exception as e:
                logger.error(f"Failed to process {image_path}: {e}")
                continue
        
        # Aggregate results
        if not all_prices:
            return {
                'status': 'no_prices_found',
                'count': 0,
                'message': 'No prices extracted from images'
            }
        
        # Calculate statistics
        price_values = [p['price'] for p in all_prices]
        
        return {
            'status': 'success',
            'count': len(all_prices),
            'prices': all_prices,
            'statistics': {
                'min_price': min(price_values),
                'max_price': max(price_values),
                'avg_price': sum(price_values) / len(price_values),
                'median_price': sorted(price_values)[len(price_values) // 2],
                'unique_products': len(set(p.get('product_name', '') for p in all_prices))
            },
            'suggested_price_ranges': self._suggest_price_ranges(all_prices)
        }
    
    def _suggest_price_ranges(self, price_data: List[Dict]) -> Dict:
        """Suggest price ranges based on extracted prices"""
        if not price_data:
            return {}
        
        price_values = [p['price'] for p in price_data]
        
        # Group prices
        sorted_prices = sorted(price_values)
        n = len(sorted_prices)
        
        return {
            'competitive_range': {
                'min': sorted_prices[0],
                'max': sorted_prices[min(1, n-1)]
            },
            'market_average_range': {
                'min': sorted_prices[max(0, n//4)],
                'max': sorted_prices[min(3*n//4, n-1)]
            },
            'premium_range': {
                'min': sorted_prices[max(0, n-3)],
                'max': sorted_prices[-1]
            }
        }


class InstagramMonitor:
    """Monitor Instagram for competitor prices"""
    
    def __init__(self, ocr_scraper: InstagramOCRScraper = None):
        self.ocr_scraper = ocr_scraper or InstagramOCRScraper()
        self.competitors = {}  # competitor_username -> last_checked
        
    def monitor_competitor(self, username: str, product_keywords: List[str]):
        """
        Monitor a competitor's Instagram for product prices
        
        Args:
            username: Instagram username
            product_keywords: Products to monitor
            
        Returns:
            Price analysis
        """
        try:
            # In a real implementation, you would:
            # 1. Scrape Instagram profile for recent posts
            # 2. Download images from posts
            # 3. Process images with OCR
            
            # For now, simulate with mock data
            logger.info(f"👀 Monitoring @{username} for {product_keywords}")
            
            # This would be replaced with actual Instagram scraping
            # Using mock image URLs for demonstration
            mock_image_urls = [
                "https://example.com/competitor_post1.jpg",
                "https://example.com/competitor_post2.jpg"
            ]
            
            # Process images
            results = self.ocr_scraper.process_batch_images(mock_image_urls, product_keywords)
            
            # Update last checked
            self.competitors[username] = datetime.now().isoformat()
            
            return {
                'competitor': username,
                'keywords': product_keywords,
                'last_checked': self.competitors[username],
                **results
            }
            
        except Exception as e:
            logger.error(f"Failed to monitor {username}: {e}")
            return {
                'competitor': username,
                'error': str(e),
                'status': 'failed'
            }
    
    def monitor_multiple_competitors(self, competitors: Dict[str, List[str]]):
        """
        Monitor multiple competitors
        
        Args:
            competitors: Dict of {username: product_keywords}
            
        Returns:
            Aggregated monitoring results
        """
        all_results = []
        
        for username, keywords in competitors.items():
            result = self.monitor_competitor(username, keywords)
            all_results.append(result)
        
        # Aggregate across all competitors
        all_prices = []
        for result in all_results:
            if 'prices' in result:
                all_prices.extend(result['prices'])
        
        return {
            'total_competitors': len(competitors),
            'competitor_results': all_results,
            'aggregate_prices': all_prices if all_prices else None
        }


# Quick test function
def test_ocr_scraper():
    """Test the OCR scraper"""
    print("🧪 Testing Instagram OCR Scraper")
    print("=" * 50)
    
    # Initialize scraper
    scraper = InstagramOCRScraper(use_easyocr=True)
    
    # Test with a local image (you would need an actual image file)
    test_image_path = "test_instagram_screenshot.png"
    
    if os.path.exists(test_image_path):
        print(f"📷 Testing with image: {test_image_path}")
        
        # Extract prices
        prices = scraper.extract_prices_from_image(
            test_image_path,
            product_keywords=['iphone', 'power bank', 'laptop']
        )
        
        if prices:
            print(f"✅ Found {len(prices)} price(s):")
            for i, price_data in enumerate(prices, 1):
                print(f"  {i}. Product: {price_data.get('product_name', 'Unknown')}")
                print(f"     Price: ₦{price_data['price']:,.0f}")
                print(f"     Text: {price_data.get('price_text', 'N/A')}")
                print(f"     Context: {price_data.get('context', '')[:60]}...")
                print()
        else:
            print("❌ No prices found in image")
    else:
        print(f"⚠️ Test image not found: {test_image_path}")
        print("💡 Create a screenshot with prices to test")
    
    # Test batch processing
    print("\n📊 Testing batch processing...")
    
    # Mock image URLs (replace with actual test images)
    mock_images = [
        "https://via.placeholder.com/600x400/FF5733/FFFFFF?text=iPhone+13+%E2%82%A6250,000",
        "https://via.placeholder.com/600x400/33FF57/000000?text=Power+Bank+15k",
    ]
    
    batch_results = scraper.process_batch_images(
        mock_images,
        product_keywords=['iphone', 'power bank']
    )
    
    print(f"Status: {batch_results.get('status')}")
    print(f"Total prices found: {batch_results.get('count', 0)}")
    
    if 'statistics' in batch_results:
        stats = batch_results['statistics']
        print(f"\n📈 Price Statistics:")
        print(f"  Min: ₦{stats.get('min_price', 0):,.0f}")
        print(f"  Max: ₦{stats.get('max_price', 0):,.0f}")
        print(f"  Avg: ₦{stats.get('avg_price', 0):,.0f}")
    
    print("\n✅ OCR Test Complete")


if __name__ == "__main__":
    test_ocr_scraper()