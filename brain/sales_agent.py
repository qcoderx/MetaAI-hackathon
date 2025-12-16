from sqlmodel import Session, select
from app.database import engine
from app.models import Customer, BusinessRule, StatusReply, Business
from brain.llama_client import LlamaClient
from datetime import datetime
import httpx
import os

class SalesAgent:
    def __init__(self):
        self.llama_client = LlamaClient()
    
    async def _send_whatsapp_message(self, phone: str, message: str, instance_name: str) -> dict:
        """Send message via Evolution API"""
        try:
            url = f"{os.getenv('EVOLUTION_API_URL')}/message/sendText/{instance_name}"
            headers = {"apikey": os.getenv("EVOLUTION_API_KEY")}
            payload = {
                "number": phone,
                "textMessage": {"text": message}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                return response.json()
        except Exception as e:
            print(f"Error sending WhatsApp message: {e}")
            return {"error": str(e)}
    
    async def process_status_reply(self, business_id: int, instance_name: str, customer_phone: str, image_url: str, user_message: str) -> str:
        """Process customer reply to WhatsApp status"""
        
        with Session(engine) as session:
            # Get or create customer for this business
            customer = session.exec(
                select(Customer).where(
                    Customer.phone == customer_phone,
                    Customer.business_id == business_id
                )
            ).first()
            
            if not customer:
                customer = Customer(
                    business_id=business_id,
                    phone=customer_phone
                )
                session.add(customer)
                session.commit()
                session.refresh(customer)
            
            # Get active business rules for this business
            rules = session.exec(
                select(BusinessRule).where(
                    BusinessRule.is_active == True,
                    BusinessRule.business_id == business_id
                )
            ).all()
            
            # Format rules context
            rules_context = ""
            for rule in rules:
                rules_context += f"Category: {rule.category}, Keywords: {rule.visual_keywords}, Min Price: ₦{rule.min_price:,.0f}, Instructions: {rule.negotiation_instruction}\\n"
            
            if not rules_context:
                rules_context = "No specific rules configured. Respond helpfully to customer inquiries."
            
            # Analyze image with Vision AI
            analysis = await self.llama_client.analyze_image_context(image_url, user_message, rules_context)
            
            # Save status reply
            status_reply = StatusReply(
                business_id=business_id,
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
            
            # Send response via WhatsApp
            reply_message = analysis.get("reply", "Thanks for your interest! Please send me a message to discuss.")
            await self._send_whatsapp_message(customer_phone, reply_message, instance_name)
            
            return reply_message