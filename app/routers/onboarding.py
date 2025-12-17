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
    
    # Create business in database
    with Session(engine) as session:
        business = Business(
            business_name=data.business_name,
            phone_number=data.phone,
            instance_name=data.business_name.lower().replace(" ", "_")
        )
        session.add(business)
        session.commit()
        session.refresh(business)
    
    # WPPConnect API setup
    wppconnect_url = os.getenv("WPPCONNECT_URL", "http://localhost:21465")
    secret_key = os.getenv("WPPCONNECT_SECRET_KEY", "mysecretkey123")
    instance_name = business.instance_name
    
    async with httpx.AsyncClient() as client:
        # Step 1: Generate token
        token_response = await client.post(
            f"{wppconnect_url}/api/{instance_name}/{secret_key}/generate-token"
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to generate token")
        
        token = token_response.json().get("token")
        
        # Step 2: Start session with QR code
        session_response = await client.post(
            f"{wppconnect_url}/api/{instance_name}/start-session",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "webhook": f"{os.getenv('BASE_URL', 'http://localhost:8000')}/webhooks/wppconnect",
                "waitQrCode": True
            }
        )
        
        if session_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to start session")
        
        session_data = session_response.json()
        qr_code = session_data.get("qrcode", "")
        
        return {
            "business_id": business.id,
            "instance_name": instance_name,
            "qr_code": qr_code,
            "message": "Scan QR code with WhatsApp to connect"
        }