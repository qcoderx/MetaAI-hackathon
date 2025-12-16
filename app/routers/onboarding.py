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
    api_key: str
    qr_code: str
    webhook_url: str

def generate_instance_name(business_name: str) -> str:
    """Generate unique instance name from business name"""
    # Clean business name and add random suffix
    clean_name = "".join(c.lower() for c in business_name if c.isalnum())[:10]
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    return f"{clean_name}_{suffix}"

@router.post("/create-instance", response_model=CreateInstanceResponse)
async def create_instance(
    request: CreateInstanceRequest,
    session: Session = Depends(get_session)
):
    """Create new business instance with WhatsApp integration"""
    try:
        # Check if phone number already exists
        existing = session.exec(
            select(Business).where(Business.phone_number == request.phone_number)
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Phone number already registered")
        
        # Generate unique instance name
        instance_name = generate_instance_name(request.business_name)
        
        # Create business record
        business = Business(
            business_name=request.business_name,
            phone_number=request.phone_number,
            instance_name=instance_name
        )
        session.add(business)
        session.commit()
        session.refresh(business)
        
        # Create Evolution API instance
        evolution_url = f"{os.getenv('EVOLUTION_API_URL')}/instance/create"
        headers = {"apikey": os.getenv("EVOLUTION_API_KEY")}
        payload = {
            "instanceName": instance_name,
            "token": business.api_key,
            "qrcode": True,
            "webhook": f"{os.getenv('BASE_URL', 'http://localhost:8000')}/webhooks/whatsapp/{instance_name}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(evolution_url, json=payload, headers=headers)
            
            if response.status_code != 201:
                # Rollback business creation if Evolution API fails
                session.delete(business)
                session.commit()
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to create WhatsApp instance: {response.text}"
                )
            
            evolution_data = response.json()
            
            return CreateInstanceResponse(
                business_id=business.id,
                instance_name=instance_name,
                api_key=business.api_key,
                qr_code=evolution_data.get("qrcode", ""),
                webhook_url=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/webhooks/whatsapp/{instance_name}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating instance: {str(e)}")

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