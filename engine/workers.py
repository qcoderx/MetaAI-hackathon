from celery import Celery
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database import get_session
from app.models import SalesLog, Customer, Product, CompetitorPrice
from brain.core_logic import PricingAgent
from engine.whatsapp_evolution import EvolutionClient
from engine.scraper_v2 import ScraperManager
from engine.instagram import monitor_instagram_competitors
import os

# Initialize Celery
celery_app = Celery(
    'naira_sniper',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    include=['engine.workers']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Lagos',
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

@celery_app.task
def scrape_market_task():
    """Scrape all competitor prices every 30 minutes"""
    try:
        print("Starting market scraping task...")
        
        # Initialize scraper manager
        scraper = ScraperManager()
        
        # Get all products to scrape
        with next(get_session()) as session:
            products = session.exec(select(Product)).all()
            
            total_scraped = 0
            for product in products:
                try:
                    # Scrape Jiji and Jumia
                    count = scraper.scrape_all(product.name, product.id)
                    total_scraped += count
                    print(f"Scraped {count} prices for {product.name}")
                except Exception as e:
                    print(f"Error scraping {product.name}: {e}")
        
        print(f"Market scraping completed. Total prices: {total_scraped}")
        return {"status": "success", "prices_scraped": total_scraped}
        
    except Exception as e:
        print(f"Market scraping task failed: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task
def scrape_instagram_task():
    """Scrape Instagram competitors every hour"""
    try:
        print("Starting Instagram scraping task...")
        
        # Define competitor Instagram accounts
        # Format: (username, product_id)
        competitors = [
            ("techstore_ng", 1),
            ("gadgetworld_lagos", 1),
            ("phoneaccessories_ng", 1),
        ]
        
        total_prices = monitor_instagram_competitors(competitors)
        
        print(f"Instagram scraping completed. Total prices: {total_prices}")
        return {"status": "success", "prices_scraped": total_prices}
        
    except Exception as e:
        print(f"Instagram scraping task failed: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task
def retarget_ghosts_task():
    """Smart Nudge for abandoned conversations"""
    try:
        print("Starting smart ghost retargeting...")
        
        # Find sessions that haven't updated in 30 mins but are recent (within 2 hours)
        cutoff = datetime.utcnow() - timedelta(minutes=30)
        recent_cutoff = datetime.utcnow() - timedelta(hours=2)
        
        with next(get_session()) as session:
            # Find recent inquiries with no purchase
            ghosts = session.exec(
                select(SalesLog)
                .where(SalesLog.inquiry_date < cutoff)
                .where(SalesLog.purchased == False)
                .where(SalesLog.inquiry_date > recent_cutoff)
            ).all()
            
            messages_sent = 0
            
            for ghost in ghosts:
                try:
                    customer = session.get(Customer, ghost.customer_id)
                    product = session.get(Product, ghost.product_id)
                    
                    if not customer or not product or not customer.phone:
                        continue
                    
                    # Get Chat History from Redis to see what we last said
                    import redis
                    import os
                    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
                    history_key = f"history:{customer.phone}"
                    
                    try:
                        last_msg = redis_client.lindex(history_key, 0)
                        has_history = last_msg is not None
                    except:
                        has_history = False
                    
                    if has_history:
                        # Context-aware nudge
                        msg = f"Still interested in the {product.name}? ₦{product.current_price:,.0f}. Available now."
                    else:
                        # Generic nudge  
                        msg = f"Hello! The {product.name} is available. ₦{product.current_price:,.0f}. Let me know if interested."
                    
                    # Send via WhatsApp
                    from engine.whatsapp_evolution import EvolutionClient
                    client = EvolutionClient()
                    result = client.send_message(customer.phone, msg)
                    
                    if "error" not in result:
                        messages_sent += 1
                        print(f"👻 Nudged {customer.phone}")
                    
                except Exception as e:
                    print(f"Error nudging customer {ghost.customer_id}: {e}")
        
        print(f"Smart ghost retargeting completed. Messages sent: {messages_sent}")
        return {"status": "success", "messages_sent": messages_sent}
        
    except Exception as e:
        print(f"Smart ghost retargeting failed: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task
def cleanup_old_prices_task():
    """Aggressive cleanup for free tier limits - FIXED: Bulk delete"""
    try:
        # Keep prices only for 3 days
        cutoff_date = datetime.utcnow() - timedelta(days=3)
        with next(get_session()) as session:
            # Bulk delete - no memory loading
            from sqlmodel import delete
            stmt = delete(CompetitorPrice).where(CompetitorPrice.scraped_at < cutoff_date)
            result = session.exec(stmt)
            session.commit()
            count = result.rowcount
        
        return {"status": "success", "message": f"Deleted {count} old prices"}
    except Exception as e:
        print(f"Cleanup failed: {e}")
        return {"status": "error", "message": str(e)}

# Schedule tasks
celery_app.conf.beat_schedule = {
    'scrape-market-every-30-minutes': {
        'task': 'engine.workers.scrape_market_task',
        'schedule': 1800.0,  # 30 minutes
    },
    'scrape-instagram-every-hour': {
        'task': 'engine.workers.scrape_instagram_task',
        'schedule': 3600.0,  # 1 hour
    },
    'retarget-ghosts-every-2-hours': {
        'task': 'engine.workers.retarget_ghosts_task',
        'schedule': 7200.0,  # 2 hours
    },
    'cleanup-old-prices-daily': {
        'task': 'engine.workers.cleanup_old_prices_task',
        'schedule': 86400.0,  # 24 hours
    },
}

celery_app.conf.timezone = 'Africa/Lagos'

# Manual task triggers for testing
def trigger_market_scrape():
    """Manually trigger market scraping"""
    return scrape_market_task.delay()

def trigger_ghost_retargeting():
    """Manually trigger ghost retargeting"""
    return retarget_ghosts_task.delay()

def trigger_instagram_scrape():
    """Manually trigger Instagram scraping"""
    return scrape_instagram_task.delay()

if __name__ == "__main__":
    print("Celery worker ready. Available tasks:")
    print("- scrape_market_task")
    print("- scrape_instagram_task") 
    print("- retarget_ghosts_task")
    print("- cleanup_old_prices_task")
    print("\nTo start worker: celery -A engine.workers worker --loglevel=info")
    print("To start scheduler: celery -A engine.workers beat --loglevel=info")