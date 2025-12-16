from fastapi import FastAPI
from app.database import create_db_and_tables
from app.routers import webhooks, rules, onboarding, qr
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Auto-Closer v3.0.0...")
    create_db_and_tables()
    print("✅ Database initialized")
    print("🤖 Vision AI Agent loaded")
    print("📱 WhatsApp webhook ready")
    print("🧠 Redis memory active")
    yield
    # Shutdown
    print("👋 Auto-Closer shutting down...")

app = FastAPI(
    title="Auto-Closer",
    description="Multimodal AI Sales Agent for WhatsApp Status",
    version="3.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(webhooks.router)
app.include_router(rules.router)
app.include_router(onboarding.router)
app.include_router(qr.router)

@app.get("/")
async def root():
    return {
        "message": "Auto-Closer API v3.0.0",
        "status": "active",
        "features": [
            "Vision AI Analysis",
            "WhatsApp Status Replies",
            "Lead Qualification",
            "Business Rules Management"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "auto-closer",
        "version": "3.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )