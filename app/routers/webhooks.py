from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from app.database import get_session
from app.models import Customer, SalesLog, Product, BusinessConfig
from brain.sales_agent import SalesAgent
from brain.profiler import CustomerProfiler
from engine.notifications import NotificationManager
from engine.whatsapp_evolution import EvolutionClient
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import json
import redis
import os

# Redis client for message deduplication
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

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
    """Handle incoming messages from Evolution API v2 with dynamic owner discovery"""
    try:
        body = await request.body()
        payload = json.loads(body.decode('utf-8'))
        
        # DEBUG: Log all incoming webhooks
        print(f"🔍 WEBHOOK RECEIVED: {json.dumps(payload, indent=2)}")
        
        data = payload.get("data", {})
        event = payload.get("event", "")
        
        print(f"📨 Event: {event}, Data keys: {list(data.keys())}")
        
        # Phase 1: Handle CONNECTION_UPDATE for dynamic owner discovery
        if event == "CONNECTION_UPDATE":
            status = data.get("state", "")
            print(f"🔗 Connection update: {status}")
            if status == "open":
                return await _handle_connection_open(session)
            return {"status": "ignored", "reason": "Connection not open"}
        
        # Handle message events
        if "message" in data:
            print(f"💬 Processing message event")
            return await _handle_message_event(session, data)
        
        print(f"⚠️ No relevant event found in payload")
        return {"status": "ignored", "reason": "No relevant event found"}
        
    except Exception as e:
        print(f"❌ Error processing Evolution webhook: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

async def _handle_connection_open(session: Session):
    """Handle WhatsApp connection open - discover and register owner"""
    try:
        from engine.whatsapp_evolution import EvolutionClient
        import uuid
        
        whatsapp_client = EvolutionClient()
        
        # Get owner phone from Evolution API instance data
        owner_phone = whatsapp_client.get_instance_data()
        print(f"🔍 Extracted owner phone: {owner_phone}")
        
        if not owner_phone:
            print(f"❌ Could not extract owner phone from instance data")
            return {"status": "error", "reason": "Could not extract owner phone"}
        
        # Get or create business config
        business_config = session.exec(select(BusinessConfig)).first()
        if not business_config:
            print(f"🏢 Creating new business config")
            ntfy_topic = f"naira_sniper_admin_{str(uuid.uuid4())[:8]}"
            business_config = BusinessConfig(
                ntfy_topic=ntfy_topic,
                bot_active=True,
                business_name="Store",
                is_setup_complete=False
            )
            session.add(business_config)
            session.commit()
            session.refresh(business_config)
        
        # Only register if not already registered
        if not business_config.owner_phone or business_config.owner_phone != owner_phone:
            print(f"👤 Registering new owner: {owner_phone}")
            business_config.owner_phone = owner_phone
            business_config.is_setup_complete = True
            session.commit()
            
            # Send welcome message only once
            welcome_msg = f"""🚀 System Connected!

I am now active on this WhatsApp account.

Your AI sales assistant is ready to:
✅ Handle customer inquiries automatically
✅ Process orders and send alerts
✅ Send notifications to this chat

🔔 PUSH NOTIFICATIONS:
Install Ntfy app and subscribe to: {business_config.ntfy_topic}

📝 ADMIN COMMANDS (send to yourself):
• START/HELP - Show commands menu
• STATS - View business statistics
• BOT OFF/ON - Control bot activity
• CONFIRM [order_id] - Approve orders
• CANCEL [order_id] - Cancel orders

Ready to sell! 💰"""
            
            try:
                import time
                time.sleep(2)  # Anti-spam delay
                result = whatsapp_client.send_message(owner_phone, welcome_msg)
                print(f"💬 Welcome message sent: {result}")
            except Exception as e:
                print(f"❌ Failed to send welcome message: {e}")
            
            print(f"✅ Owner registered successfully: {owner_phone}")
            return {"status": "owner_registered", "phone": owner_phone}
        else:
            print(f"👤 Owner already registered: {owner_phone}")
            return {"status": "already_registered", "phone": owner_phone}
        
    except Exception as e:
        print(f"❌ Error handling connection open: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

async def _handle_message_event(session: Session, data: Dict):
    """Handle incoming message with self-chat admin console logic"""
    
    # --- SPAM FIX: MESSAGE DEDUPLICATION ---
    msg_id = data.get("key", {}).get("id")
    if msg_id:
        # Check if ID exists. If not, set it with 60s expiry. If yes, it's spam.
        try:
            is_new = redis_client.set(f"msg_dedup:{msg_id}", "1", ex=60, nx=True)
            if not is_new:
                print(f"🚫 Duplicate/Spam message ID {msg_id} ignored.")
                return {"status": "ignored", "reason": "Duplicate message"}
        except Exception as e:
            print(f"⚠️ Redis dedup failed: {e}")
            # Continue processing if Redis fails
    
    msg = data["message"]
    key = data.get("key", {})
    
    print(f"💬 Message data: {json.dumps(msg, indent=2)}")
    print(f"🔑 Key data: {json.dumps(key, indent=2)}")
    
    # Extract message details
    text = None
    if "conversation" in msg:
        text = msg["conversation"]
    elif "extendedTextMessage" in msg and "text" in msg["extendedTextMessage"]:
        text = msg["extendedTextMessage"]["text"]
    
    print(f"📝 Extracted text: '{text}'")
    
    if not text:
        return {"status": "ignored", "reason": "No text message"}
    
    # Extract phone numbers and message direction
    remote_jid = key.get("remoteJid", "")
    from_me = key.get("fromMe", False)
    push_name = data.get("pushName", "Customer")
    
    # Clean phone number
    phone = remote_jid.replace("@s.whatsapp.net", "")
    if phone.startswith("234"):
        phone = f"+{phone}"
    
    print(f"📱 Phone: {phone}, FromMe: {from_me}, Name: {push_name}")
    
    # Get business config
    business_config = session.exec(select(BusinessConfig)).first()
    if not business_config:
        print(f"❌ No business config found")
        return {"status": "error", "reason": "No business config"}
    
    print(f"🏢 Owner phone: {business_config.owner_phone}, Setup complete: {business_config.is_setup_complete}")
    
    if not business_config.owner_phone:
        print(f"❌ Owner not registered yet")
        return {"status": "error", "reason": "Owner not registered"}
    
    owner_phone_clean = business_config.owner_phone.replace("+", "")
    message_phone_clean = phone.replace("+", "")
    
    print(f"🔍 Comparing phones - Owner: {owner_phone_clean}, Message: {message_phone_clean}")
    
    # Phase 2: Self-Chat Admin Console Logic
    if from_me and message_phone_clean == owner_phone_clean:
        # Owner talking to themselves (Note to Self) - Admin Command
        print(f"👤 ADMIN COMMAND detected: '{text}'")
        return await _handle_admin_command(session, business_config, text)
    
    elif from_me:
        # Any message from owner - could be admin command
        print(f"👤 OWNER MESSAGE detected: '{text}'")
        if text.upper().startswith('ADD '):
            return await _handle_admin_command(session, business_config, text)
    
    elif from_me and message_phone_clean != owner_phone_clean:
        # Owner manually replying to customer - Bot stays silent
        print(f"💬 MANUAL TAKEOVER detected")
        return {"status": "manual_takeover", "reason": "Owner manually replying"}
    
    elif not from_me:
        # Customer message - Trigger Sales Agent
        print(f"👥 CUSTOMER MESSAGE detected: '{text}'")
        if not business_config.bot_active:
            print(f"🚫 Bot is inactive")
            return {"status": "ignored", "reason": "Bot is inactive"}
        
        # 1. FETCH HISTORY (Last 10 messages)
        history_key = f"history:{phone}"
        try:
            raw_history = redis_client.lrange(history_key, 0, 9)
            conversation_history = [json.loads(msg) for msg in raw_history][::-1] # Reverse to chronological
        except Exception as e:
            print(f"⚠️ Redis history fetch failed: {e}")
            conversation_history = []
        
        return await _handle_customer_message(session, phone, text, push_name, conversation_history)
    
    print(f"❓ Unknown message type")
    return {"status": "ignored", "reason": "Unknown message type"}



async def _handle_admin_command(session: Session, business_config: BusinessConfig, command: str):
    """Handle admin commands from owner's self-chat"""
    print(f"🔧 Processing admin command: '{command}'")
    command_lower = command.lower().strip()
    
    if command_lower == "stats":
        # Generate quick stats
        from app.models import Order, Customer
        from datetime import datetime, timedelta
        
        today = datetime.utcnow().date()
        orders_today = session.exec(
            select(Order).where(Order.created_at >= today)
        ).all()
        
        total_customers = session.exec(select(Customer)).all()
        
        stats_msg = f"""📊 BUSINESS STATS

📅 Today:
• Orders: {len(orders_today)}
• Revenue: ₦{sum(o.total_amount for o in orders_today):,.0f}

👥 Total Customers: {len(total_customers)}
🤖 Bot Status: {'Active' if business_config.bot_active else 'Inactive'}

Generated: {datetime.now().strftime('%H:%M')}"""
        
        whatsapp_client = EvolutionClient()
        import time
        time.sleep(2)  # Admin delay
        whatsapp_client.send_message(business_config.owner_phone, stats_msg)
        return {"status": "admin_command", "command": "stats"}
    
    elif command_lower == "bot off":
        business_config.bot_active = False
        session.commit()
        whatsapp_client = EvolutionClient()
        import time
        time.sleep(2)  # Admin delay
        whatsapp_client.send_message(business_config.owner_phone, "🚫 Bot deactivated. Customers will not receive automatic responses.")
        return {"status": "admin_command", "command": "bot_off"}
    
    elif command_lower == "bot on":
        business_config.bot_active = True
        session.commit()
        whatsapp_client = EvolutionClient()
        import time
        time.sleep(2)  # Admin delay
        whatsapp_client.send_message(business_config.owner_phone, "✅ Bot activated. Ready to handle customer inquiries.")
        return {"status": "admin_command", "command": "bot_on"}
    
    elif command_lower.startswith("add "):
        # Format: ADD Product Name, Current Price, Floor Price
        print(f"📎 ADD command detected: '{command}'")
        try:
            raw_data = command[4:].strip()
            parts = [p.strip() for p in raw_data.split(',')]
            print(f"📊 Parsed parts: {parts}")
            
            if len(parts) != 3:
                raise ValueError("Format: ADD Name, Price, Floor")
                
            name = parts[0]
            current_price = float(parts[1])
            floor_price = float(parts[2])
            
            if floor_price > current_price:
                raise ValueError("Floor price cannot be higher than current price")

            # Create Product
            from app.models import Product
            new_product = Product(
                name=name,
                model="Standard",
                current_price=current_price,
                min_negotiable_price=floor_price, 
                inventory_count=10
            )
            session.add(new_product)
            session.commit()
            print(f"✅ Product created in database: {name}")
            
            msg = f"✅ Product Added!\n\n📱 {name}\n💰 Price: ₦{current_price:,.0f}\n🛡️ Floor: ₦{floor_price:,.0f}"
            whatsapp_client = EvolutionClient()
            import time
            time.sleep(2)
            result = whatsapp_client.send_message(business_config.owner_phone, msg)
            print(f"📱 WhatsApp response sent: {result}")
            return {"status": "success", "message": "Product added"}

        except Exception as e:
            print(f"❌ ADD command error: {e}")
            whatsapp_client = EvolutionClient()
            error_msg = f"❌ Error adding product.\nFormat: ADD Name, Price, Floor\nError: {str(e)}"
            import time
            time.sleep(2)
            whatsapp_client.send_message(business_config.owner_phone, error_msg)
            return {"status": "error", "message": str(e)}
    
    elif command_lower.startswith("confirm ") or command_lower.startswith("cancel "):
        # Handle order commands
        notification_manager = NotificationManager()
        result = notification_manager.process_owner_command(
            session, business_config.owner_phone, command
        )
        return {"status": "admin_command", "command": "order_management", "result": result}
    
    else:
        # Unknown command - send help
        help_msg = """📝 ADMIN COMMANDS:

• STATS - View business statistics
• BOT ON/OFF - Control bot activity
• ADD Name, Price, Floor - Add product
• CONFIRM [order_id] - Approve orders
• CANCEL [order_id] - Cancel orders

Example: ADD iPhone 14, 450000, 400000

Send any command to this chat (Note to Self)."""
        
        whatsapp_client = EvolutionClient()
        import time
        time.sleep(2)  # Admin delay
        whatsapp_client.send_message(business_config.owner_phone, help_msg)
        return {"status": "admin_command", "command": "help"}

async def _handle_customer_message(session: Session, phone: str, text: str, customer_name: str, conversation_history: list = None):
    """Handle customer message with Sales Agent"""
    try:
        sales_agent = SalesAgent()
        
        # 2. PROCESS WITH HISTORY
        agent_response = sales_agent.process_message(
            session=session,
            customer_phone=phone,
            message_text=text,
            conversation_history=conversation_history or []
        )
        
        # Send response back to customer
        whatsapp_client = EvolutionClient()
        response_sent = False
        
        if agent_response.get("response"):
            try:
                import time
                import random
                time.sleep(random.uniform(30, 90))  # Customer delay 30-90 seconds
                send_result = whatsapp_client.send_message(phone, agent_response["response"])
                response_sent = "error" not in send_result
            except Exception as e:
                print(f"Failed to send WhatsApp response: {e}")
        
        # 3. SAVE NEW CONTEXT (User + Bot)
        history_key = f"history:{phone}"
        try:
            # Store User Msg
            redis_client.lpush(history_key, json.dumps({"role": "user", "content": text}))
            # Store Bot Msg (if sent)
            if agent_response.get("response"):
                redis_client.lpush(history_key, json.dumps({"role": "assistant", "content": agent_response["response"]}))
                # Trim to 10 items to save space
                redis_client.ltrim(history_key, 0, 9)
        except Exception as e:
            print(f"⚠️ Redis history save failed: {e}")
        
        # Handle session end (Smart Sleep)
        if agent_response.get("status") == "session_end":
            print(f"💤 AI decided to sleep for {phone}")
            try:
                redis_client.delete(history_key)
            except Exception as e:
                print(f"⚠️ Redis delete failed: {e}")
        
        # Handle order creation alerts
        if agent_response.get("status") == "order_created":
            try:
                notification_manager = NotificationManager()
                notification_manager.send_order_alert(session, agent_response["order_id"])
            except Exception as e:
                print(f"Failed to send order alert: {e}")
        
        return {
            "status": "customer_processed",
            "customer_phone": phone,
            "intent": agent_response.get("intent", "unknown"),
            "response_sent": response_sent,
            "agent_response": agent_response
        }
        
    except Exception as e:
        print(f"Error handling customer message: {e}")
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

@router.get("/register-owner")
def register_owner_manually(session: Session = Depends(get_session)):
    """Manually register owner from Evolution API data"""
    try:
        import asyncio
        result = asyncio.run(_handle_connection_open(session))
        return result
    except Exception as e:
        raise HTTPException(500, f"Failed to register owner: {str(e)}")
