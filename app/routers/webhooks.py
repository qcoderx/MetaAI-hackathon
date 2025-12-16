import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any
import redis
import base64

from fastapi import APIRouter, Request, HTTPException
from sqlmodel import Session, select

from app.database import engine
from app.models import Customer, BusinessRule
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

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Handle WhatsApp webhook events from Evolution API"""
    try:
        data = await request.json()
        print(f"Webhook received: {json.dumps(data, indent=2)}")
        
        # Handle Evolution API message format
        if "data" in data:
            await _handle_message_event(data["data"])
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _handle_message_event(message_data: Dict[str, Any]):
    """Process incoming WhatsApp messages"""
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
                response = sales_agent.process_status_reply(from_number, image_url, user_text)
                print(f"Status reply from {from_number}: {user_text}")
                print(f"AI Response: {response}")
                # TODO: Send response via Evolution API
            else:
                print(f"Status reply missing data - URL: {bool(image_url)}, Text: {bool(user_text)}")
        
        # Handle admin commands
        elif from_number == os.getenv("ADMIN_PHONE", ""):
            await _handle_admin_command(from_number, msg)
        
    except Exception as e:
        print(f"Error handling message event: {e}")

async def _handle_admin_command(phone: str, msg: Dict[str, Any]):
    """Handle admin commands for managing business rules"""
    try:
        text = msg.get("conversation", "")
        if not text:
            text = msg.get("extendedTextMessage", {}).get("text", "")
        
        if text.upper().startswith("ADD "):
            # Format: ADD Category|Keywords|MinPrice|Instructions
            parts = text[4:].split("|")
            if len(parts) == 4:
                with Session(engine) as session:
                    rule = BusinessRule(
                        category=parts[0].strip(),
                        visual_keywords=parts[1].strip(),
                        min_price=float(parts[2].strip()),
                        negotiation_instruction=parts[3].strip()
                    )
                    session.add(rule)
                    session.commit()
                    print(f"Added rule: {rule.category}")
        
    except Exception as e:
        print(f"Error handling admin command: {e}")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "auto-closer-webhook",
        "redis": "connected" if redis_client else "unavailable"
    }