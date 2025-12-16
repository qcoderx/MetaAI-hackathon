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
        print(f"WPPConnect webhook received: {json.dumps(data, indent=2)}")
        
        # Filter: Only process event == "onMessage"
        if data.get("event") != "onMessage":
            return {"status": "ignored", "reason": "Not onMessage event"}
        
        # Extract session and message
        instance_name = data.get("session")
        msg = data.get("response", {})
        
        if not instance_name:
            return {"status": "ignored", "reason": "No session in payload"}
        
        # Get business by instance_name
        with Session(engine) as session:
            business = session.exec(
                select(Business).where(Business.instance_name == instance_name)
            ).first()
            
            if not business:
                print(f"Business with instance {instance_name} not found")
                return {"status": "ignored", "reason": "Business not found"}
        
        # Deduplication check
        msg_id = msg.get("id", "")
        if msg_id:
            if redis_client:
                if redis_client.get(f"msg:{msg_id}"):
                    return {"status": "ignored", "reason": "Duplicate message"}
                redis_client.setex(f"msg:{msg_id}", 3600, "1")
            else:
                if msg_id in message_history:
                    return {"status": "ignored", "reason": "Duplicate message"}
                message_history[msg_id] = datetime.now()
        
        # Detect Status Reply
        quoted = msg.get("quotedMsg", {})
        if "status@broadcast" in (quoted.get("from") or ""):
            print(f"🎯 Status Reply on {instance_name}: {msg.get('body')}")
            
            # Extract details for processing
            customer_phone = msg.get("from", "").replace("@c.us", "")
            user_message = msg.get("body", "")
            
            # Extract image from quoted status
            image_url = ""
            if quoted.get("type") == "image":
                image_url = quoted.get("body", "")  # WPPConnect provides image URL in body
            
            if image_url and user_message:
                # Process status reply with Vision AI
                response = await sales_agent.process_status_reply(
                    business.id, instance_name, customer_phone, image_url, user_message
                )
                print(f"AI Response: {response}")
            else:
                print(f"Status reply missing data - URL: {bool(image_url)}, Text: {bool(user_message)}")
        
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