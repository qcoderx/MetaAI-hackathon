from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from app.database import get_session
from app.models import BusinessRule, Business
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/rules", tags=["Business Rules"])

class CreateRuleRequest(BaseModel):
    business_id: int
    category: str
    visual_keywords: str
    min_price: float
    negotiation_instruction: str
    is_active: bool = True

@router.post("/", response_model=BusinessRule)
def create_rule(rule_data: CreateRuleRequest, session: Session = Depends(get_session)):
    """Create a new business rule"""
    # Verify business exists
    business = session.get(Business, rule_data.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    rule = BusinessRule(**rule_data.dict())
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule

@router.get("/business/{business_id}", response_model=List[BusinessRule])
def get_rules(business_id: int, session: Session = Depends(get_session)):
    """Get business rules for specific business"""
    return session.exec(
        select(BusinessRule).where(BusinessRule.business_id == business_id)
    ).all()

@router.get("/{rule_id}", response_model=BusinessRule)
def get_rule(rule_id: int, session: Session = Depends(get_session)):
    """Get specific business rule"""
    rule = session.get(BusinessRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.put("/{rule_id}", response_model=BusinessRule)
def update_rule(rule_id: int, rule_data: BusinessRule, session: Session = Depends(get_session)):
    """Update business rule"""
    rule = session.get(BusinessRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule.category = rule_data.category
    rule.visual_keywords = rule_data.visual_keywords
    rule.min_price = rule_data.min_price
    rule.negotiation_instruction = rule_data.negotiation_instruction
    rule.is_active = rule_data.is_active
    
    session.commit()
    session.refresh(rule)
    return rule

@router.delete("/{rule_id}")
def delete_rule(rule_id: int, session: Session = Depends(get_session)):
    """Delete business rule"""
    rule = session.get(BusinessRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    session.delete(rule)
    session.commit()
    return {"message": "Rule deleted successfully"}