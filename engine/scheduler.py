"""
NAIRA SNIPER - TASK SCHEDULER
Background task queue for periodic scraping
"""
import schedule
import time
import threading
from datetime import datetime
import logging
from .scraper import ScraperManager
from .database import PriceDatabase

logger = logging.getLogger(__name__)

class TaskScheduler:
    """Background task scheduler"""
    
    def __init__(self):
        self.scraper = ScraperManager()
        self.database = PriceDatabase()
        self.running = False
        self.thread = None
        logger.info("⏰ TaskScheduler initialized")
    
    def scrape_products(self, product_names: list = None):
        """Scrape multiple products"""
        if not product_names:
            product_names = [
                "iPhone",
                "power bank",
                "laptop",
                "Samsung phone",
                "airpods"
            ]
        
        logger.info(f"🔄 Scraping {len(product_names)} products...")
        
        all_results = {}
        for product in product_names:
            try:
                logger.info(f"🔍 Scraping: {product}")
                
                # Scrape
                results = self.scraper.scrape_all(product, max_results=5)
                
                # Save to file
                self.scraper.save_results(results, product)
                
                # Save to database
                self.database.save_prices(product, results)
                
                # Count items
                total_items = sum(len(items) for items in results.values())
                all_results[product] = total_items
                
                logger.info(f"✅ {product}: {total_items} items")
                
                # Delay between products
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to scrape {product}: {e}")
                continue
        
        return all_results
    
    def start(self):
        """Start the scheduler in background thread"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        # Schedule tasks
        schedule.every(30).minutes.do(lambda: self.scrape_products())
        schedule.every().hour.do(lambda: logger.info("⏰ Hourly check completed"))
        schedule.every().day.at("09:00").do(lambda: self._daily_report())
        schedule.every().sunday.at("23:00").do(lambda: self.database.cleanup_old_data(7))
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
        logger.info("✅ Scheduler started")
        logger.info("📅 Scheduled tasks:")
        logger.info("  - Scrape every 30 minutes")
        logger.info("  - Daily report at 9:00 AM")
        logger.info("  - Weekly cleanup on Sunday 11 PM")
    
    def _run(self):
        """Run scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _daily_report(self):
        """Generate daily report"""
        logger.info("📊 Generating daily report...")
        # TODO: Implement detailed report
    
    def stop(self):
        """Stop scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 Scheduler stopped")
    
    def run_once(self):
        """Run scraping once (for testing)"""
        return self.scrape_products()


# Global instance
scheduler = TaskScheduler()