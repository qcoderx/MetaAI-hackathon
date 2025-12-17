import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from app.database import engine
from app.models import Business

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

class BusinessSetup(BaseModel):
    business_name: str
    phone: str

@router.post("/setup")
async def setup_business(data: BusinessSetup):
    """Setup business and get WhatsApp QR code"""
    
    # 1. Database Logic: Check if exists OR Create new
    with Session(engine) as session:
        # Check if this phone already exists
        statement = select(Business).where(Business.phone_number == data.phone)
        business = session.exec(statement).first()
        
        if business:
            print(f"ℹ️ Business found: {business.business_name} (ID: {business.id})")
            # Optional: Update instance name if you want to force a refresh
            # business.instance_name = ... 
        else:
            print(f"🆕 Creating new business: {data.business_name}")
            business = Business(
                business_name=data.business_name,
                phone_number=data.phone,
                # Clean the name for URL usage (e.g. "Tola's Wigs" -> "tolas_wigs")
                instance_name=data.business_name.lower().replace(" ", "_").replace("'", "")
            )
            session.add(business)
            session.commit()
            session.refresh(business)
    
    # 2. WPPConnect API Setup
    wppconnect_url = os.getenv("WPPCONNECT_URL", "http://localhost:21465")
    secret_key = os.getenv("WPPCONNECT_SECRET_KEY", "mysecretkey123")
    instance_name = business.instance_name
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step A: Generate token (This creates the session on WPPConnect)
            token_url = f"{wppconnect_url}/api/{instance_name}/{secret_key}/generate-token"
            print(f"🔄 Connecting to WPPConnect: {token_url}")
            
            token_response = await client.post(token_url)
            
            # WPPConnect might return 201 (Created) or 200 (OK)
            if token_response.status_code not in [200, 201]:
                print(f"❌ Token Error: {token_response.text}")
                raise HTTPException(status_code=500, detail="Failed to generate WPP token")
            
            token_data = token_response.json()
            session_token = token_data.get("token")
            
            # Step B: Start session to get QR code
            start_url = f"{wppconnect_url}/api/{instance_name}/start-session"
            headers = {"Authorization": f"Bearer {session_token}"}
            
            # We point the webhook back to YOUR machine
            webhook_url = f"{os.getenv('BASE_URL', 'http://localhost:8000')}/webhooks/wppconnect"
            
            payload = {
                "webhook": webhook_url,
                "waitQrCode": True
            }
            
            print(f"🚀 Starting Session for {instance_name}...")
            try:
                session_response = await client.post(start_url, headers=headers, json=payload)
                session_data = session_response.json()
                qr_code = session_data.get("qrcode") or session_data.get("urlCode", "")
                status = session_data.get("status", "unknown")
            except httpx.ReadTimeout:
                print("⏰ Session start timed out, but webhooks are working")
                qr_code = ""
                status = "connecting"
            
            return {
                "business_id": business.id,
                "instance_name": instance_name,
                "status": status,
                "qr_code": qr_code, # This is the base64 image string
                "message": "Scan this QR code in WhatsApp > Linked Devices" if qr_code else "Session already connected or starting..."
            }
            
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Could not connect to WPPConnect Server. Is Docker running?")