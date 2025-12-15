from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from app.database import get_session
from app.models import Customer, SalesLog, Product, BusinessConfig
from brain.sales_agent import SalesAgent
from engine.notifications import NotificationManager
from engine.whatsapp_evolution import EvolutionClient
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import json

router = APIRouter(prefix="/webhook", tags=["webhooks"])

class WhatsAppMessage(BaseModel):
    phone: str
    message: str
    customer_name: Optional[str] = None
    product_id: Optional[int] = None

class CustomerSignalRequest(BaseModel):
    customer_id: int
    message: str

class ManualMessageRequest(BaseModel):
    phone: str
    message: str

class OrderStatusRequest(BaseModel):
    order_id: int
    status: str

@router.post("/whatsapp")
def handle_whatsapp_message(
    data: WhatsAppMessage,
    session: Session = Depends(get_session)
):
    """
    Handle incoming WhatsApp messages
    - Create/update customer
    - Classify customer type
    - Log interaction
    """
    # Get or create customer
    customer = session.exec(
        select(Customer).where(Customer.phone == data.phone)
    ).first()
    
    if not customer:
        customer = Customer(
            phone=data.phone,
            name=data.customer_name
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)
    else:
        customer.last_interaction = datetime.utcnow()
        session.add(customer)
    
    # Classify customer type from message
    profiler = CustomerProfiler()
    classification = profiler.update_customer_profile(
        session, customer.id, data.message
    )
    
    # Log sales inquiry if product mentioned
    if data.product_id:
        product = session.get(Product, data.product_id)
        if product:
            sales_log = SalesLog(
                customer_id=customer.id,
                product_id=data.product_id
            )
            session.add(sales_log)
    
    session.commit()
    
    return {
        "customer_id": customer.id,
        "customer_type": customer.customer_type.value,
        "classification": classification,
        "message": "Message processed successfully"
    }

@router.post("/customer/signal")
def store_customer_signal(
    data: CustomerSignalRequest,
    session: Session = Depends(get_session)
):
    """Store and analyze customer signals"""
    customer = session.get(Customer, data.customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    
    profiler = CustomerProfiler()
    classification = profiler.update_customer_profile(
        session, data.customer_id, data.message
    )
    
    return {
        "customer_id": data.customer_id,
        "classification": classification,
        "updated_type": customer.customer_type.value
    }

@router.get("/health")
def health_check(session: Session = Depends(get_session)):
    """Health check endpoint"""
    try:
        # Check database connection
        session.exec(select(BusinessConfig)).first()
        
        # Check if bot is active
        business_config = session.exec(select(BusinessConfig)).first()
        bot_active = business_config.bot_active if business_config else False
        
        return {
            "status": "healthy",
            "database": "connected",
            "bot_active": bot_active,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"Health check failed: {str(e)}")

@router.post("/evolution")
async def handle_evolution_webhook(
    request: Request,
    session: Session = Depends(get_session)
):
    """Handle incoming messages from Evolution API v2 with conversational AI"""
    try:
        body = await request.body()
        payload = json.loads(body.decode('utf-8'))
        
        # Extract message data from Evolution API v2 payload
        data = payload.get("data", {})
        
        # Handle different message types
        message_data = None
        if "message" in data:
            msg = data["message"]
            
            # Extract text from different message types
            text = None
            if "conversation" in msg:
                text = msg["conversation"]
            elif "extendedTextMessage" in msg and "text" in msg["extendedTextMessage"]:
                text = msg["extendedTextMessage"]["text"]
            
            if text:
                # Extract phone and name
                remote_jid = data.get("key", {}).get("remoteJid", "")
                phone = remote_jid.replace("@s.whatsapp.net", "")
                push_name = data.get("pushName", "Customer")
                
                if phone and text:
                    message_data = {
                        "phone": phone,
                        "message": text,
                        "customer_name": push_name
                    }
        
        if not message_data:
            return {"status": "ignored", "reason": "No text message found"}
        
        # Get or create business config
        business_config = session.exec(select(BusinessConfig)).first()
        if not business_config:
            return {"status": "error", "reason": "Business config not found"}
        
        # Auto-register first user as owner if not set up
        if not business_config.is_setup_complete and not business_config.owner_phone:
            business_config.owner_phone = message_data["phone"]
            business_config.is_setup_complete = True
            session.commit()
            
            # Send welcome message to new owner
            whatsapp_client = EvolutionClient()
            welcome_msg = f"🎉 Welcome to Naira Sniper!

You are now registered as the business owner.

Your AI sales assistant is active and ready to:
✅ Handle customer inquiries
✅ Process orders automatically
✅ Send you notifications

🔔 PUSH NOTIFICATIONS:
Install Ntfy app and subscribe to: {business_config.ntfy_topic}

Commands:
• BOT ON/OFF - Control bot
• CONFIRM [order_id] - Approve orders
• CANCEL [order_id] - Cancel orders

Let's start selling! 🚀"
            
            try:
                whatsapp_client.send_message(message_data["phone"], welcome_msg)
            except Exception as e:
                print(f"Failed to send welcome message: {e}")
            
            return {"status": "owner_registered", "phone": message_data["phone"]}
        
        # Check if bot is active
        if not business_config.bot_active:
            return {"status": "ignored", "reason": "Bot is inactive"}
        
        # Check if this is the business owner sending commands
        notification_manager = NotificationManager()
        if business_config.owner_phone == message_data["phone"]:
            command_result = notification_manager.process_owner_command(
                session, message_data["phone"], message_data["message"]
            )
            return {"status": "owner_command", "result": command_result}
        
        # Process customer message with Sales Agent
        sales_agent = SalesAgent()
        
        # Get conversation history (simplified - in production would store in DB)
        conversation_history = []  # TODO: Implement conversation history storage
        
        # Process message
        agent_response = sales_agent.process_message(
            session=session,
            customer_phone=message_data["phone"],
            message_text=message_data["message"],
            conversation_history=conversation_history
        )
        
        # Send response back to customer
        whatsapp_client = EvolutionClient()
        response_sent = False
        
        if agent_response.get("response"):
            try:
                send_result = whatsapp_client.send_message(
                    message_data["phone"],
                    agent_response["response"]
                )
                response_sent = send_result.get("success", False)
            except Exception as e:
                print(f"Failed to send WhatsApp response: {e}")
        
        # Handle order creation alerts
        if agent_response.get("status") == "order_created":
            try:
                notification_manager.send_order_alert(
                    session, agent_response["order_id"]
                )
            except Exception as e:
                print(f"Failed to send order alert: {e}")
        
        return {
            "status": "processed",
            "customer_phone": message_data["phone"],
            "intent": agent_response.get("intent", "unknown"),
            "response_sent": response_sent,
            "agent_response": agent_response
        }
        
    except Exception as e:
        print(f"Error processing Evolution webhook: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/test/message")
def send_test_message(
    data: ManualMessageRequest,
    session: Session = Depends(get_session)
):
    """Send manual test message to sales agent (for testing)"""
    try:
        # Check if bot is active
        business_config = session.exec(select(BusinessConfig)).first()
        if not business_config or not business_config.bot_active:
            raise HTTPException(400, "Bot is inactive")
        
        # Process with Sales Agent
        sales_agent = SalesAgent()
        agent_response = sales_agent.process_message(
            session=session,
            customer_phone=data.phone,
            message_text=data.message,
            conversation_history=[]
        )
        
        # Send response via WhatsApp
        whatsapp_client = EvolutionClient()
        response_sent = False
        
        if agent_response.get("response"):
            send_result = whatsapp_client.send_message(
                data.phone,
                agent_response["response"]
            )
            response_sent = send_result.get("success", False)
        
        return {
            "success": True,
            "agent_response": agent_response,
            "response_sent": response_sent
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error processing test message: {str(e)}")

@router.post("/order/status")
def update_order_status(
    data: OrderStatusRequest,
    session: Session = Depends(get_session)
):
    """Update order status manually"""
    from app.models import Order, OrderStatus
    
    order = session.exec(select(Order).where(Order.id == data.order_id)).first()
    if not order:
        raise HTTPException(404, "Order not found")
    
    try:
        order.status = OrderStatus(data.status)
        session.commit()
        
        # Send notification if order is confirmed or cancelled
        if data.status in ["confirmed", "cancelled"]:
            notification_manager = NotificationManager()
            if data.status == "confirmed":
                notification_manager._confirm_order(session, data.order_id)
            else:
                notification_manager._cancel_order(session, data.order_id)
        
        return {
            "success": True,
            "order_id": data.order_id,
            "new_status": data.status
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error updating order: {str(e)}")
