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
    """Retarget customers who inquired but didn't purchase"""
    try:
        print("Starting ghost retargeting task...")
        
        # Find customers who inquired > 24 hours ago but didn't purchase
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        with next(get_session()) as session:
            # Query for ghost customers
            ghost_inquiries = session.exec(
                select(SalesLog)
                .where(SalesLog.inquiry_date < cutoff_time)
                .where(SalesLog.purchased == False)
                .where(SalesLog.inquiry_date > datetime.utcnow() - timedelta(days=7))  # Within last 7 days
            ).all()
            
            agent = PricingAgent()
            evolution_client = EvolutionClient()
            messages_sent = 0
            
            for inquiry in ghost_inquiries:
                try:
                    # Get customer and product
                    customer = session.get(Customer, inquiry.customer_id)
                    product = session.get(Product, inquiry.product_id)
                    
                    if not customer or not product:
                        continue
                    
                    # Skip if customer has no phone
                    if not customer.phone:
                        continue
                    
                    # Get AI pricing decision
                    decision = agent.make_pricing_decision(session, product, customer)
                    
                    # Send appropriate message based on strategy
                    success = False
                    if decision["strategy"] == "price_drop":
                        from brain.prompts import PRICE_DROP_TEMPLATE
                        message = PRICE_DROP_TEMPLATE.format(
                            customer_name=customer.name or "Customer",
                            product_name=product.name,
                            new_price=f"{decision['recommended_price']:,.0f}",
                            old_price=f"{product.current_price:,.0f}",
                            hours=4
                        )
                        result = evolution_client.send_message(customer.phone, message)
                        success = "error" not in result
                    else:  # value_reinforcement
                        from brain.prompts import VALUE_REINFORCEMENT_TEMPLATE
                        message = VALUE_REINFORCEMENT_TEMPLATE.format(
                            customer_name=customer.name or "Customer",
                            product_name=product.name,
                            price=f"{product.current_price:,.0f}",
                            model_year="2024",
                            warranty="6-month",
                            extra_value="Free delivery within Lagos"
                        )
                        result = evolution_client.send_message(customer.phone, message)
                        success = "error" not in result
                    
                    if success:
                        messages_sent += 1
                        print(f"Retargeted {customer.phone} for {product.name} with {decision['strategy']}")
                    
                except Exception as e:
                    print(f"Error retargeting customer {inquiry.customer_id}: {e}")
        
        print(f"Ghost retargeting completed. Messages sent: {messages_sent}")
        return {"status": "success", "messages_sent": messages_sent}
        
    except Exception as e:
        print(f"Ghost retargeting task failed: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task
def cleanup_old_prices_task():
    """Aggressive cleanup for free tier limits"""
    try:
        # Keep prices only for 3 days
        cutoff_date = datetime.utcnow() - timedelta(days=3)
        with next(get_session()) as session:
            old_prices = session.exec(
                select(CompetitorPrice)
                .where(CompetitorPrice.scraped_at < cutoff_date)
            ).all()
            
            count = len(old_prices)
            for price in old_prices:
                session.delete(price)
            
            session.commit()
        
        return {"status": "success", "message": "Database cleaned"}
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