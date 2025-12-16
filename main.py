from fastapi import FastAPI
from app.database import create_db_and_tables, get_session
from app.routers import webhooks, rules
from app.models import BusinessConfig
from sqlmodel import select
from contextlib import asynccontextmanager
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    create_db_and_tables()
    
    # Initialize business config if not exists
    session = next(get_session())
    business_config = session.exec(select(BusinessConfig)).first()
    if not business_config:
        # Create default business config (owner will be set dynamically)
        import uuid
        ntfy_topic = f"naira_sniper_admin_{str(uuid.uuid4())[:8]}"
        default_config = BusinessConfig(
            ntfy_topic=ntfy_topic,
            bot_active=True,
            business_name=os.getenv("BUSINESS_NAME", "Naira Sniper Store"),
            is_setup_complete=False
        )
        session.add(default_config)
        session.commit()
        print("✅ Business config initialized - waiting for owner setup")
    session.close()
    
    yield
    # Shutdown: cleanup if needed

app = FastAPI(
    title="Auto-Closer - Multimodal AI Sales Agent",
    description="Vision AI-powered sales automation for WhatsApp Status replies with Nigerian business context",
    version="3.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(webhooks.router)
app.include_router(rules.router)

@app.get("/")
def root():
    return {
        "message": "Auto-Closer - Multimodal AI Sales Agent",
        "status": "active",
        "version": "3.0.0",
        "features": [
            "Vision AI Status Reply Processing",
            "Llama 3.2 11B Vision Integration",
            "Dynamic Business Rules Engine",
            "Nigerian Business Context AI",
            "Automated Lead Qualification",
            "Customer Interest Tagging"
        ],
        "endpoints": {
            "products": "/product",
            "market_analysis": "/market",
            "webhooks": "/webhook",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health_check():
    """System health check"""
    try:
        session = next(get_session())
        business_config = session.exec(select(BusinessConfig)).first()
        session.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "bot_active": business_config.bot_active if business_config else False,
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "database": "disconnected",
            "error": "Database unavailable - running in offline mode",
            "version": "2.0.0"
        }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Naira Sniper - WhatsApp AI Sales Assistant")
    print("📱 Features: Conversational AI, Order Management, Market Intelligence")
    print("🔗 API Docs: http://localhost:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
