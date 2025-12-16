from sqlmodel import Session, select
from app.database import engine
from app.models import Customer, BusinessRule, StatusReply
from brain.llama_client import LlamaClient
from datetime import datetime
import redis
import os

class SalesAgent:
    def __init__(self):
        self.llama_client = LlamaClient()
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
        except:
            self.redis_client = None
    
    def process_status_reply(self, customer_phone: str, image_url: str, user_message: str) -> str:
        """Process customer reply to WhatsApp status"""
        
        with Session(engine) as session:
            # Get or create customer
            customer = session.exec(select(Customer).where(Customer.phone == customer_phone)).first()
            if not customer:
                customer = Customer(phone=customer_phone)
                session.add(customer)
                session.commit()
                session.refresh(customer)
            
            # Get active business rules
            rules = session.exec(select(BusinessRule).where(BusinessRule.is_active == True)).all()
            
            # Format rules context
            rules_context = ""
            for rule in rules:
                rules_context += f"Category: {rule.category}, Keywords: {rule.visual_keywords}, Min Price: ₦{rule.min_price:,.0f}, Instructions: {rule.negotiation_instruction}\\n"
            
            if not rules_context:
                rules_context = "No specific rules configured. Respond helpfully to customer inquiries."
            
            # Analyze image with Vision AI
            analysis = self.llama_client.analyze_image_context(image_url, user_message, rules_context)
            
            # Save status reply
            status_reply = StatusReply(
                customer_id=customer.id,
                status_image_url=image_url,
                detected_category=analysis.get("detected_category", "unknown"),
                user_message=user_message,
                ai_response=analysis.get("reply", "Thanks for your interest!"),
                confidence_score=analysis.get("confidence", 0.0)
            )
            session.add(status_reply)
            
            # Update customer tags if sales lead
            if analysis.get("is_sales_lead", False):
                category = analysis.get("detected_category", "")
                if category and category != "unknown":
                    current_tags = customer.tags.split(",") if customer.tags else []
                    interest_tag = f"Interested in {category}"
                    if interest_tag not in current_tags:
                        current_tags.append(interest_tag)
                        customer.tags = ",".join([tag.strip() for tag in current_tags if tag.strip()])
            
            customer.updated_at = datetime.utcnow()
            session.commit()
            
            return analysis.get("reply", "Thanks for your interest! Please send me a message to discuss.")
    
    def get_customer_profile(self, phone: str) -> dict:
        """Get customer profile and interaction history"""
        with Session(engine) as session:
            customer = session.exec(select(Customer).where(Customer.phone == phone)).first()
            if not customer:
                return {"phone": phone, "tags": "", "interactions": 0}
            
            interactions = len(customer.status_replies)
            return {
                "phone": phone,
                "name": customer.name,
                "tags": customer.tags,
                "interactions": interactions,
                "last_seen": customer.updated_at
            }