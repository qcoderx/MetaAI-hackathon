import json
import os
from datetime import datetime
from typing import Dict, Any
import redis

from fastapi import APIRouter, Request, HTTPException
from sqlmodel import Session, select

from app.database import engine
from app.models import Business
from brain.sales_agent import SalesAgent

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Initialize sales agent
sales_agent = SalesAgent()

# Redis for message deduplication
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    redis_client = redis.from_url(redis_url, decode_responses=True)
except:
    redis_client = None
    print("Redis not available - using memory deduplication")
    message_history = {}

@router.post("/wppconnect")
async def wppconnect_webhook(request: Request):
    """Handle WPPConnect webhook events"""
    try:
        data = await request.json()
        
        # Check if event == "onMessage"
        if data.get("event") != "onMessage":
            return {"status": "ignored"}
        
        # Extract message
        msg = data.get("response", {})
        
        # Status Detection: Check if response.quotedMsg.from contains "status@broadcast"
        quoted = msg.get("quotedMsg", {})
        if "status@broadcast" in (quoted.get("from") or ""):
            print("Status Reply Detected")
            print(f"Body: {msg.get('body')}")
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "auto-closer-webhook",
        "redis": "connected" if redis_client else "unavailable"
    }