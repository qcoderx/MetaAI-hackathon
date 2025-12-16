from brain.llama_client import LlamaClient
from app.models import BusinessRule, Customer, StatusReply, CustomerType
from sqlmodel import Session, select
from typing import Dict, Optional, List
from datetime import datetime

class SalesAgent:
    """Auto-Closer AI Agent for WhatsApp Status Replies"""
    
    def __init__(self):
        self.llama = LlamaClient()
    
    def process_status_reply(
        self,
        session: Session,
        customer_phone: str,
        image_url: str,
        user_text: str,
        customer_name: str = "Customer"
    ) -> Dict:
        """Process WhatsApp status reply with Vision AI"""
        
        # Step 1: Get or create customer
        customer = self._get_or_create_customer(session, customer_phone, customer_name)
        
        # Step 2: Retrieve all active business rules
        active_rules = session.exec(
            select(BusinessRule).where(BusinessRule.is_active == True)
        ).all()
        
        if not active_rules:
            return {
                "detected_category": "no_rules",
                "confidence": 0.0,
                "reply": "Thanks for your interest! Please contact us directly.",
                "is_sales_lead": False
            }
        
        # Step 3: Format rules for AI context
        rules_context = self._format_rules_context(active_rules)
        
        # Step 4: Call Vision AI
        ai_result = self.llama.analyze_image_context(image_url, user_text, rules_context)
        
        # Step 5: Save to StatusReply table
        status_reply = StatusReply(
            customer_id=customer.id,
            status_image_url=image_url,
            detected_category=ai_result.get("detected_category", "unknown"),
            user_message=user_text,
            ai_response=ai_result.get("reply", ""),
            confidence_score=ai_result.get("confidence", 0.0)
        )
        session.add(status_reply)
        
        # Step 6: Update customer tags if it's a sales lead
        if ai_result.get("is_sales_lead", False):
            self._update_customer_tags(session, customer, ai_result.get("detected_category"))
        
        session.commit()
        
        return ai_result
    
    def process_message(
        self,
        session: Session,
        customer_phone: str,
        message_text: str,
        conversation_history: List[Dict] = None
    ) -> Dict:
        """Process regular customer message (fallback for non-status messages)"""
        
        customer = self._get_or_create_customer(session, customer_phone)
        
        # Simple fallback response for now
        return {
            "response": "Hello! I see you're interested. Please reply to one of our status updates to get specific product information.",
            "intent": "general_inquiry"
        }
    
    def _get_or_create_customer(self, session: Session, phone: str, name: str = None) -> Customer:
        """Get existing customer or create new one"""
        customer = session.exec(
            select(Customer).where(Customer.phone == phone)
        ).first()
        
        if not customer:
            customer = Customer(
                phone=phone,
                name=name or "Customer"
            )
            session.add(customer)
            session.commit()
            session.refresh(customer)
        else:
            # Update last interaction
            customer.last_interaction = datetime.utcnow()
            if name and not customer.name:
                customer.name = name
            session.commit()
        
        return customer
    
    def _format_rules_context(self, rules: List[BusinessRule]) -> str:
        """Format business rules for AI context"""
        rules_text = []
        
        for rule in rules:
            rule_text = f"Category: {rule.category}, Keywords: {rule.visual_keywords}, Min Price: ₦{rule.min_price:,.0f}, Instructions: {rule.negotiation_instruction}"
            rules_text.append(rule_text)
        
        return " | ".join(rules_text)
    
    def _update_customer_tags(self, session: Session, customer: Customer, category: str):
        """Update customer tags when they show interest in a category"""
        if not category or category == "unknown":
            return
        
        interest_tag = f"Interested in {category}"
        
        # Add tag if not already present
        current_tags = customer.tags.split(", ") if customer.tags else []
        if interest_tag not in current_tags:
            current_tags.append(interest_tag)
            customer.tags = ", ".join(current_tags)
            session.commit()