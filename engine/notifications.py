import requests
from engine.whatsapp_evolution import EvolutionClient
from app.models import Order, OrderItem, Product, Customer, BusinessConfig
from sqlmodel import Session, select
from typing import Dict, Optional
import os
from datetime import datetime

class NtfyClient:
    """Ntfy.sh client for free push notifications"""
    
    def __init__(self):
        self.base_url = "https://ntfy.sh"
    
    def send_notification(self, topic: str, message: str, title: str = "Naira Sniper Alert") -> bool:
        """Send push notification via Ntfy.sh"""
        if not topic:
            print("Ntfy topic not configured")
            return False
        
        headers = {
            "Title": title,
            "Priority": "high",
            "Tags": "money,alert"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/{topic}",
                data=message.encode('utf-8'),
                headers=headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Ntfy notification failed: {e}")
            return False

class NotificationManager:
    """Manages all business notifications - WhatsApp and Push"""
    
    def __init__(self):
        self.whatsapp = EvolutionClient()
        self.ntfy_client = NtfyClient()
    
    def send_order_alert(self, session: Session, order_id: int) -> Dict:
        """Send order alert to business owner via WhatsApp and Push"""
        
        # Get order details
        order = session.exec(select(Order).where(Order.id == order_id)).first()
        if not order:
            return {"success": False, "error": "Order not found"}
        
        # Get customer and order items
        customer = session.exec(select(Customer).where(Customer.id == order.customer_id)).first()
        order_items = session.exec(select(OrderItem).where(OrderItem.order_id == order_id)).all()
        
        # Get business config
        business_config = session.exec(select(BusinessConfig)).first()
        if not business_config or not business_config.owner_phone:
            return {"success": False, "error": "Owner not registered yet"}
        
        # Build order summary
        items_text = []
        for item in order_items:
            product = session.exec(select(Product).where(Product.id == item.product_id)).first()
            if product:
                items_text.append(f"{product.name} x{item.quantity} - ₦{item.total_price:,.0f}")
        
        # WhatsApp message to owner
        whatsapp_message = f"""🔔 NEW ORDER ALERT!

Order #{order.id}
Customer: {customer.name or customer.phone}
Phone: {customer.phone}

Items:
{chr(10).join(items_text)}

Total: ₦{order.total_amount:,.0f}
Address: {order.delivery_address or 'Not provided'}

Reply 'CONFIRM {order.id}' to process order
Reply 'CANCEL {order.id}' to cancel order"""

        # Send WhatsApp alert
        whatsapp_sent = False
        try:
            whatsapp_result = self.whatsapp.send_message(
                business_config.owner_phone,
                whatsapp_message
            )
            whatsapp_sent = whatsapp_result.get("success", False)
        except Exception as e:
            print(f"WhatsApp alert failed: {e}")
        
        # Send push notification
        push_sent = False
        if business_config.ntfy_topic:
            push_message = f"💰 New Order: ₦{order.total_amount:,.0f} from {customer.name or customer.phone}. Check WhatsApp to confirm."
            push_sent = self.ntfy_client.send_notification(
                business_config.ntfy_topic,
                push_message,
                "New Order Alert"
            )
        
        return {
            "success": whatsapp_sent or push_sent,
            "whatsapp_sent": whatsapp_sent,
            "push_sent": push_sent,
            "order_id": order.id
        }
    
    def send_market_intelligence_alert(self, session: Session, alert_data: Dict) -> Dict:
        """Send market intelligence alerts in Sniper Mode"""
        
        business_config = session.exec(select(BusinessConfig)).first()
        if not business_config or not business_config.bot_active or not business_config.owner_phone:
            return {"success": False, "error": "Bot not active or owner not registered"}
        
        # Only send if significant market shift detected
        if not alert_data.get("significant_shift", False):
            return {"success": False, "error": "No significant market shift"}
        
        message = f"""📊 MARKET INTELLIGENCE ALERT

Product: {alert_data['product_name']}
Event: {alert_data['event_type']}

{alert_data['details']}

Recommended Action: {alert_data['recommendation']}

Time: {datetime.now().strftime('%H:%M')}"""
        
        # Send WhatsApp alert
        try:
            result = self.whatsapp.send_message(
                business_config.owner_phone,
                message
            )
            return {"success": result.get("success", False)}
        except Exception as e:
            print(f"Market alert failed: {e}")
            return {"success": False, "error": str(e)}
    
    def send_low_stock_alert(self, session: Session, product_id: int) -> Dict:
        """Send low stock alert to owner"""
        
        product = session.exec(select(Product).where(Product.id == product_id)).first()
        business_config = session.exec(select(BusinessConfig)).first()
        
        if not product or not business_config or not business_config.owner_phone:
            return {"success": False, "error": "Product, config not found, or owner not registered"}
        
        if product.inventory_count > 2:  # Only alert when stock is critically low
            return {"success": False, "error": "Stock not critically low"}
        
        message = f"""⚠️ LOW STOCK ALERT

{product.name}
Current Stock: {product.inventory_count} units
Price: ₦{product.current_price:,.0f}

Restock recommended to avoid lost sales.

Time: {datetime.now().strftime('%H:%M')}"""
        
        try:
            result = self.whatsapp.send_message(
                business_config.owner_phone,
                message
            )
            
            # Also send push notification if configured
            if business_config.ntfy_topic:
                self.ntfy_client.send_notification(
                    business_config.ntfy_topic,
                    f"Low Stock: {product.name} ({product.inventory_count} left)",
                    "Stock Alert"
                )
            
            return {"success": result.get("success", False)}
        except Exception as e:
            print(f"Low stock alert failed: {e}")
            return {"success": False, "error": str(e)}
    
    def send_customer_retarget_message(self, session: Session, customer_phone: str, product_id: int) -> Dict:
        """Send retargeting message to ghosted customers"""
        
        product = session.exec(select(Product).where(Product.id == product_id)).first()
        if not product:
            return {"success": False, "error": "Product not found"}
        
        # Personalized retarget message
        message = f"""Hello! 👋

You showed interest in our {product.name} last week.

Good news - price dropped to ₦{product.current_price:,.0f}!

Still available with warranty. Interested?"""
        
        try:
            result = self.whatsapp.send_message(customer_phone, message)
            return {"success": result.get("success", False)}
        except Exception as e:
            print(f"Retarget message failed: {e}")
            return {"success": False, "error": str(e)}
    
    def process_owner_command(self, session: Session, owner_phone: str, command_text: str) -> Dict:
        """Process commands from business owner"""
        
        # Verify this is the owner
        business_config = session.exec(select(BusinessConfig)).first()
        if not business_config or not business_config.owner_phone or business_config.owner_phone != owner_phone:
            return {"success": False, "error": "Unauthorized or owner not registered"}
        
        command_lower = command_text.lower().strip()
        
        # CONFIRM order command
        if command_lower.startswith("confirm "):
            try:
                order_id = int(command_lower.split(" ")[1])
                return self._confirm_order(session, order_id)
            except (ValueError, IndexError):
                return {"success": False, "error": "Invalid confirm command format"}
        
        # CANCEL order command
        elif command_lower.startswith("cancel "):
            try:
                order_id = int(command_lower.split(" ")[1])
                return self._cancel_order(session, order_id)
            except (ValueError, IndexError):
                return {"success": False, "error": "Invalid cancel command format"}
        
        # BOT ON/OFF commands
        elif command_lower == "bot off":
            business_config.bot_active = False
            session.commit()
            return {"success": True, "message": "Bot deactivated"}
        
        elif command_lower == "bot on":
            business_config.bot_active = True
            session.commit()
            return {"success": True, "message": "Bot activated"}
        
        else:
            return {"success": False, "error": "Unknown command"}
    
    def _confirm_order(self, session: Session, order_id: int) -> Dict:
        """Confirm order and notify customer"""
        
        order = session.exec(select(Order).where(Order.id == order_id)).first()
        if not order:
            return {"success": False, "error": "Order not found"}
        
        # Update order status
        order.status = "confirmed"
        session.commit()
        
        # Notify customer
        customer = session.exec(select(Customer).where(Customer.id == order.customer_id)).first()
        if customer:
            message = f"""✅ Order Confirmed!

Order #{order.id} has been confirmed by our team.

We'll prepare your items and contact you for delivery within 24 hours.

Thank you for your business! 🙏"""
            
            try:
                self.whatsapp.send_message(customer.phone, message)
            except Exception as e:
                print(f"Customer notification failed: {e}")
        
        return {"success": True, "message": f"Order {order_id} confirmed"}
    
    def _cancel_order(self, session: Session, order_id: int) -> Dict:
        """Cancel order and notify customer"""
        
        order = session.exec(select(Order).where(Order.id == order_id)).first()
        if not order:
            return {"success": False, "error": "Order not found"}
        
        # Restore inventory
        order_items = session.exec(select(OrderItem).where(OrderItem.order_id == order_id)).all()
        for item in order_items:
            product = session.exec(select(Product).where(Product.id == item.product_id)).first()
            if product:
                product.inventory_count += item.quantity
        
        # Update order status
        order.status = "cancelled"
        session.commit()
        
        # Notify customer
        customer = session.exec(select(Customer).where(Customer.id == order.customer_id)).first()
        if customer:
            message = f"""❌ Order Update

Order #{order.id} has been cancelled.

If you have any questions, please contact us.

We apologize for any inconvenience."""
            
            try:
                self.whatsapp.send_message(customer.phone, message)
            except Exception as e:
                print(f"Customer notification failed: {e}")
        
        return {"success": True, "message": f"Order {order_id} cancelled"}