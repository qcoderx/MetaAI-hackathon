from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import BusinessRule
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/rules", tags=["rules"])

class CreateRuleRequest(BaseModel):
    category: str
    visual_keywords: str
    min_price: float
    negotiation_instruction: str

class UpdateRuleRequest(BaseModel):
    category: Optional[str] = None
    visual_keywords: Optional[str] = None
    min_price: Optional[float] = None
    negotiation_instruction: Optional[str] = None
    is_active: Optional[bool] = None

@router.post("/add")
def create_rule(
    rule_data: CreateRuleRequest,
    session: Session = Depends(get_session)
):
    """Create a new business rule"""
    
    # Check if category already exists
    existing_rule = session.exec(
        select(BusinessRule).where(BusinessRule.category == rule_data.category)
    ).first()
    
    if existing_rule:
        raise HTTPException(400, f"Rule for category '{rule_data.category}' already exists")
    
    new_rule = BusinessRule(
        category=rule_data.category,
        visual_keywords=rule_data.visual_keywords,
        min_price=rule_data.min_price,
        negotiation_instruction=rule_data.negotiation_instruction,
        is_active=True
    )
    
    session.add(new_rule)
    session.commit()
    session.refresh(new_rule)
    
    return {
        "success": True,
        "message": f"Rule created for {rule_data.category}",
        "rule_id": new_rule.id
    }

@router.get("")
def list_rules(session: Session = Depends(get_session)):
    """List all business rules"""
    
    rules = session.exec(select(BusinessRule)).all()
    
    return {
        "rules": [
            {
                "id": rule.id,
                "category": rule.category,
                "visual_keywords": rule.visual_keywords,
                "min_price": rule.min_price,
                "negotiation_instruction": rule.negotiation_instruction,
                "is_active": rule.is_active,
                "created_at": rule.created_at.isoformat()
            }
            for rule in rules
        ],
        "total": len(rules)
    }

@router.get("/{rule_id}")
def get_rule(rule_id: int, session: Session = Depends(get_session)):
    """Get specific business rule"""
    
    rule = session.get(BusinessRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    
    return {
        "id": rule.id,
        "category": rule.category,
        "visual_keywords": rule.visual_keywords,
        "min_price": rule.min_price,
        "negotiation_instruction": rule.negotiation_instruction,
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat()
    }

@router.put("/{rule_id}")
def update_rule(
    rule_id: int,
    rule_data: UpdateRuleRequest,
    session: Session = Depends(get_session)
):
    """Update business rule"""
    
    rule = session.get(BusinessRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    
    # Update fields if provided
    if rule_data.category is not None:
        rule.category = rule_data.category
    if rule_data.visual_keywords is not None:
        rule.visual_keywords = rule_data.visual_keywords
    if rule_data.min_price is not None:
        rule.min_price = rule_data.min_price
    if rule_data.negotiation_instruction is not None:
        rule.negotiation_instruction = rule_data.negotiation_instruction
    if rule_data.is_active is not None:
        rule.is_active = rule_data.is_active
    
    rule.updated_at = datetime.utcnow()
    session.commit()
    
    return {
        "success": True,
        "message": f"Rule {rule_id} updated successfully"
    }

@router.delete("/{rule_id}")
def delete_rule(rule_id: int, session: Session = Depends(get_session)):
    """Delete business rule"""
    
    rule = session.get(BusinessRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    
    session.delete(rule)
    session.commit()
    
    return {
        "success": True,
        "message": f"Rule {rule_id} deleted successfully"
    }