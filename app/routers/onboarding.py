from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from app.database import get_session
from app.models import Business
from pydantic import BaseModel
import httpx
import os
import secrets
import string
import base64

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
    # 1. Check DB for existing user
    existing = session.exec(select(Business).where(Business.phone_number == request.phone_number)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # 2. Setup names
    instance_name = generate_instance_name(request.business_name)
    
    # 3. WAHA Configuration
    waha_url = "http://localhost:3000" 
    waha_api_key = "auto-closer-key"
    webhook_url = f"{os.getenv('BASE_URL')}/webhooks/whatsapp/{instance_name}"

    try:
        async with httpx.AsyncClient() as client:
            # STEP A: Start the Session
            payload = {
                "name": instance_name,
                "config": {
                    "webhooks": [
                        {
                            "url": webhook_url,
                            "events": ["message", "session.status"]
                        }
                    ]
                }
            }
            
            print(f"Starting WAHA session: {instance_name}")
            response = await client.post(
                f"{waha_url}/api/sessions", 
                json=payload,
                headers={"Authorization": f"Bearer {waha_api_key}"}
            )
            
            if response.status_code not in [200, 201]:
                print(f"WAHA Error: {response.text}")
                raise HTTPException(status_code=500, detail=f"WAHA Failed: {response.text}")

            # STEP B: Get the QR Code
            qr_response = await client.get(
                f"{waha_url}/api/sessions/{instance_name}/auth/qr?format=image",
                headers={"Authorization": f"Bearer {waha_api_key}"}
            )
            
            qr_base64 = ""
            if qr_response.status_code == 200:
                qr_base64 = base64.b64encode(qr_response.content).decode('utf-8')
            else:
                print("QR not ready yet, user might need to check dashboard")

            # 4. Save to DB
            business = Business(
                business_name=request.business_name,
                phone_number=request.phone_number,
                instance_name=instance_name,
                api_key="waha-managed"
            )
            session.add(business)
            session.commit()
            
            return CreateInstanceResponse(
                business_id=business.id,
                instance_name=instance_name,
                qr_code=qr_base64,
                webhook_url=webhook_url
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection Failed: {str(e)}")

@router.get("/instances")
async def list_instances(session: Session = Depends(get_session)):
    """List all business instances"""
    businesses = session.exec(select(Business)).all()
    return [
        {
            "business_id": b.id,
            "business_name": b.business_name,
            "phone_number": b.phone_number,
            "instance_name": b.instance_name,
            "created_at": b.created_at
        }
        for b in businesses
    ]