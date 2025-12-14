import pytesseract
from PIL import Image
import re
import os
from typing import Optional, List, Dict
import requests
from io import BytesIO

class InstagramOCRScraper:
    """OCR-based price extraction from Instagram images"""
    
    def __init__(self):
        # Configure Tesseract path if needed (Windows)
        if os.name == 'nt':  # Windows
            # Try common Tesseract installation paths
            possible_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', ''))
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
    
    def extract_price_from_image(self, image_path: str) -> Optional[float]:
        """
        Extract price from image using OCR
        
        Args:
            image_path: Path to image file or URL
            
        Returns:
            Extracted price as float or None if not found
        """
        try:
            # Load image
            if image_path.startswith(('http://', 'https://')):
                # Download image from URL
                response = requests.get(image_path, timeout=10)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
            else:
                # Load from local file
                image = Image.open(image_path)
            
            # Preprocess image for better OCR
            image = self._preprocess_image(image)
            
            # Extract text using OCR
            text = pytesseract.image_to_string(image, config='--psm 6')
            
            # Extract price from text
            price = self._extract_price_from_text(text)
            
            return price
            
        except Exception as e:
            print(f"Error extracting price from image {image_path}: {e}")
            return None
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy"""
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize image if too small
            width, height = image.size
            if width < 800 or height < 600:
                # Scale up maintaining aspect ratio
                scale_factor = max(800/width, 600/height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to grayscale for better OCR
            image = image.convert('L')
            
            return image
            
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            return image
    
    def _extract_price_from_text(self, text: str) -> Optional[float]:
        """
        Extract price from OCR text using multiple patterns
        
        Args:
            text: Raw OCR text
            
        Returns:
            Extracted price as float or None
        """
        # Clean text
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        # Nigerian price patterns
        patterns = [
            # ₦15,000 or ₦15000
            r'₦\s*(\d{1,3}(?:,\d{3})*|\d+)',
            # N15,000 or N15000
            r'N\s*(\d{1,3}(?:,\d{3})*|\d+)',
            # #15,000 or #15000
            r'#\s*(\d{1,3}(?:,\d{3})*|\d+)',
            # 15,000 naira or 15000 naira
            r'(\d{1,3}(?:,\d{3})*|\d+)\s*(?:naira|NGN)',
            # Price: 15,000
            r'(?:price|cost|amount)[:=\s]*₦?\s*(\d{1,3}(?:,\d{3})*|\d+)',
            # Just numbers with commas (15,000+)
            r'(\d{1,3}(?:,\d{3})+)',
            # Large numbers without commas (10000+)
            r'(\d{5,})'
        ]
        
        extracted_prices = []
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean the match
                    price_str = str(match).replace(',', '').replace(' ', '')
                    price = float(price_str)
                    
                    # Filter reasonable prices (1000 to 10,000,000 Naira)
                    if 1000 <= price <= 10000000:
                        extracted_prices.append(price)
                        
                except (ValueError, TypeError):
                    continue
        
        if extracted_prices:
            # Return the most common price or the first valid one
            return extracted_prices[0]
        
        return None
    
    def extract_prices_from_multiple_images(self, image_paths: List[str]) -> List[float]:
        """
        Extract prices from multiple images
        
        Args:
            image_paths: List of image paths or URLs
            
        Returns:
            List of extracted prices
        """
        prices = []
        
        for image_path in image_paths:
            price = self.extract_price_from_image(image_path)
            if price:
                prices.append(price)
        
        return prices
    
    def batch_process_directory(self, directory_path: str) -> List[Dict]:
        """
        Process all images in a directory
        
        Args:
            directory_path: Path to directory containing images
            
        Returns:
            List of dictionaries with filename and extracted price
        """
        results = []
        
        if not os.path.exists(directory_path):
            print(f"Directory not found: {directory_path}")
            return results
        
        # Supported image formats
        supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
        
        for filename in os.listdir(directory_path):
            if filename.lower().endswith(supported_formats):
                image_path = os.path.join(directory_path, filename)
                price = self.extract_price_from_image(image_path)
                
                results.append({
                    'filename': filename,
                    'path': image_path,
                    'price': price
                })
        
        return results

# Utility functions for easy import
def extract_price_from_image(image_path: str) -> Optional[float]:
    """Convenience function to extract price from single image"""
    scraper = InstagramOCRScraper()
    return scraper.extract_price_from_image(image_path)

def extract_prices_from_images(image_paths: List[str]) -> List[float]:
    """Convenience function to extract prices from multiple images"""
    scraper = InstagramOCRScraper()
    return scraper.extract_prices_from_multiple_images(image_paths)