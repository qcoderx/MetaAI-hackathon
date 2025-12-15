from celery import Celery
import os

# Simple Celery app for task execution
app = Celery(
    'naira_sniper',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Basic configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Lagos',
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Import tasks
from engine.workers import scrape_market_task, scrape_instagram_task, retarget_ghosts_task, cleanup_old_prices_task

# Schedule (optional - can be disabled for now)
app.conf.beat_schedule = {
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

if __name__ == '__main__':
    app.start()