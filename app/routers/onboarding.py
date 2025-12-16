from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from app.database import get_session
from app.models import Business
from pydantic import BaseModel
import httpx
import os
import secrets
import string

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

class CreateInstanceRequest(BaseModel):
    business_name: str
    phone_number: str

class CreateInstanceResponse(BaseModel):
    business_id: int
    instance_name: str
    qr_code: str
    webhook_url: str

def generate_instance_name(business_name: str) -> str:
    clean_name = "".join(c.lower() for c in business_name if c.isalnum())[:10]
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    return f"{clean_name}_{suffix}"

@router.post("/create-instance", response_model=CreateInstanceResponse)
async def create_instance(
    request: CreateInstanceRequest,
    session: Session = Depends(get_session)
):
    # Check for existing user
    existing = session.exec(select(Business).where(Business.phone_number == request.phone_number)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    instance_name = generate_instance_name(request.business_name)
    
    # WPPConnect Configuration
    wpp_url = os.getenv("WPPCONNECT_URL")
    secret_key = os.getenv("WPPCONNECT_SECRET_KEY")
    
    if not wpp_url or not secret_key:
        raise HTTPException(status_code=500, detail="Configuration Error: WPPCONNECT_URL or WPPCONNECT_SECRET_KEY missing")

    base_url = os.getenv('BASE_URL', 'http://localhost:8000')
    webhook_url = f"{base_url}/webhooks/wppconnect"

    try:
        async with httpx.AsyncClient() as client:
            # 1. Generate Token (Admin Level)
            token_url = f"{wpp_url}/api/{instance_name}/{secret_key}/generate-token"
            token_res = await client.post(token_url)
            
            if token_res.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Token generation failed: {token_res.text}")
            
            session_token = token_res.json().get('token')
            if not session_token:
                raise HTTPException(status_code=500, detail="No token received from WPPConnect")

            # 2. Start Session (User Level)
            start_url = f"{wpp_url}/api/{instance_name}/start-session"
            headers = {"Authorization": f"Bearer {session_token}"}
            payload = {
                "webhook": webhook_url,
                "waitQrCode": True
            }
            
            print(f"🚀 Starting WPPConnect session: {instance_name} at {wpp_url}")
            
            start_res = await client.post(start_url, json=payload, headers=headers)
            
            if start_res.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Session start failed: {start_res.text}")
            
            qr_code = start_res.json().get('qrcode', '')

            # Save to DB with Bearer Token
            business = Business(
                business_name=request.business_name,
                phone_number=request.phone_number,
                instance_name=instance_name,
                api_key=session_token  # Store Bearer Token
            )
            session.add(business)
            session.commit()
            
            return CreateInstanceResponse(
                business_id=business.id,
                instance_name=instance_name,
                qr_code=qr_code,
                webhook_url=webhook_url
            )

    except httpx.ConnectError:
         raise HTTPException(status_code=503, detail=f"Could not connect to WPPConnect at {wpp_url}. Is the Docker container running?")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System Error: {str(e)}")