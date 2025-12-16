import json
import os
from datetime import datetime
from typing import Dict, Any
import redis

from fastapi import APIRouter, Request, HTTPException, Path
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

@router.post("/whatsapp/{instance_name}")
async def whatsapp_webhook(request: Request, instance_name: str = Path(...)):
    """Handle WhatsApp webhook events from Evolution API for specific instance"""
    try:
        data = await request.json()
        print(f"Webhook received for {instance_name}: {json.dumps(data, indent=2)}")
        
        # Get business by instance_name
        with Session(engine) as session:
            business = session.exec(
                select(Business).where(Business.instance_name == instance_name)
            ).first()
            
            if not business:
                raise HTTPException(status_code=404, detail=f"Business with instance {instance_name} not found")
        
        # Handle Evolution API message format
        if "data" in data:
            await _handle_message_event(data["data"], business.id, business.instance_name)
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _handle_message_event(message_data: Dict[str, Any], business_id: int, instance_name: str):
    """Process incoming WhatsApp messages for specific business"""
    try:
        # Extract message details
        key = message_data.get("key", {})
        from_number = key.get("remoteJid", "").replace("@s.whatsapp.net", "")
        msg_id = key.get("id", "")
        
        # Deduplication check
        if redis_client:
            if redis_client.get(f"msg:{msg_id}"):
                return
            redis_client.setex(f"msg:{msg_id}", 3600, "1")  # 1 hour TTL
        else:
            if msg_id in message_history:
                return
            message_history[msg_id] = datetime.now()
        
        # Check if this is a status reply
        msg = message_data.get("message", {})
        context = msg.get("extendedTextMessage", {}).get("contextInfo", {})
        is_status_reply = "status@broadcast" in context.get("remoteJid", "")
        has_quoted_image = "imageMessage" in context.get("quotedMessage", {})
        
        if is_status_reply and has_quoted_image:
            # Extract user message
            user_text = msg.get("extendedTextMessage", {}).get("text", "")
            if not user_text:
                user_text = msg.get("conversation", "")
            
            # Extract image URL from quoted message
            quoted_image = context.get("quotedMessage", {}).get("imageMessage", {})
            image_url = quoted_image.get("url", "")
            
            # Fallback to thumbnail if no URL
            if not image_url and "jpegThumbnail" in quoted_image:
                thumbnail_b64 = quoted_image["jpegThumbnail"]
                image_url = f"data:image/jpeg;base64,{thumbnail_b64}"
            
            if image_url and user_text:
                # Process status reply with Vision AI
                response = await sales_agent.process_status_reply(
                    business_id, instance_name, from_number, image_url, user_text
                )
                print(f"Status reply from {from_number}: {user_text}")
                print(f"AI Response: {response}")
            else:
                print(f"Status reply missing data - URL: {bool(image_url)}, Text: {bool(user_text)}")
        
    except Exception as e:
        print(f"Error handling message event: {e}")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "auto-closer-webhook",
        "redis": "connected" if redis_client else "unavailable"
    }