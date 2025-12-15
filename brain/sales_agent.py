from brain.llama_client import LlamaClient
from brain.prompts import SALES_REP_SYSTEM_PROMPT
from app.models import (
    Product, Customer, CustomerType, Order, OrderItem, OrderStatus, 
    PaymentStatus, BusinessConfig
)
from sqlmodel import Session, select, func
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import re

class ConversationState:
    GREETING = "greeting"
    CATALOG_SEARCH = "catalog_search"
    PRODUCT_INQUIRY = "product_inquiry"
    NEGOTIATION = "negotiation"
    ORDER_TAKING = "order_taking"
    DELIVERY_INFO = "delivery_info"
    ORDER_CONFIRMATION = "order_confirmation"

class SalesAgent:
    """WhatsApp AI Sales Assistant - Full Lifecycle Conversational Agent"""
    
    def __init__(self):
        self.llama = LlamaClient()
        self.conversation_history = []
    
    def process_message(
        self,
        session: Session,
        customer_phone: str,
        message_text: str,
        conversation_history: List[Dict] = None
    ) -> Dict:
        """Main entry point for processing customer messages"""
        
        # Get or create customer
        customer = self._get_or_create_customer(session, customer_phone)
        
        # CURE ALZHEIMER'S: Load conversation history from database
        self.conversation_history = self._load_conversation_history(session, customer.id)
        
        # Log incoming message
        self._log_message(session, customer.id, message_text, is_from_customer=True)
        
        # Analyze message intent
        intent = self._analyze_intent(message_text, self.conversation_history)
        
        # Route to appropriate handler
        if intent == "catalog_search":
            return self._handle_catalog_search(session, customer, message_text)
        elif intent == "negotiation":
            return self._handle_negotiation(session, customer, message_text)
        elif intent == "order_creation":
            return self._handle_order_creation(session, customer, message_text)
        elif intent == "objection":
            return self._handle_objection(session, customer, message_text)
        else:
            return self._handle_general_inquiry(session, customer, message_text)
    
    def _get_or_create_customer(self, session: Session, phone: str) -> Customer:
        """Get existing customer or create new one"""
        customer = session.exec(
            select(Customer).where(Customer.phone == phone)
        ).first()
        
        if not customer:
            customer = Customer(phone=phone)
            session.add(customer)
            session.commit()
            session.refresh(customer)
        
        return customer
    
    def _load_conversation_history(self, session: Session, customer_id: int) -> List[Dict]:
        """Load recent conversation history from database"""
        from app.models import ConversationLog
        from datetime import timedelta
        
        # Load last 10 messages from past 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        logs = session.exec(
            select(ConversationLog)
            .where(ConversationLog.customer_id == customer_id)
            .where(ConversationLog.created_at > cutoff)
            .order_by(ConversationLog.created_at.desc())
            .limit(10)
        ).all()
        
        history = []
        for log in reversed(logs):  # Reverse to get chronological order
            history.append({
                "message": log.message,
                "is_from_customer": log.is_from_customer,
                "timestamp": log.created_at,
                "product_id": log.product_id
            })
        
        return history
    
    def _log_message(self, session: Session, customer_id: int, message: str, is_from_customer: bool, product_id: Optional[int] = None):
        """Log message to conversation history"""
        from app.models import ConversationLog
        
        log = ConversationLog(
            customer_id=customer_id,
            message=message,
            is_from_customer=is_from_customer,
            product_id=product_id
        )
        session.add(log)
        session.commit()
    
    def _analyze_intent(self, message: str, history: List[Dict]) -> str:
        """Analyze customer message intent using keywords and context"""
        message_lower = message.lower()
        
        # Order creation signals
        if any(word in message_lower for word in ["buy", "order", "purchase", "take it", "i want"]):
            return "order_creation"
        
        # Negotiation signals
        if any(word in message_lower for word in ["price", "expensive", "cheaper", "discount", "reduce"]):
            return "negotiation"
        
        # Catalog search signals
        if any(word in message_lower for word in ["do you have", "available", "stock", "iphone", "samsung"]):
            return "catalog_search"
        
        # Objection signals
        if any(phrase in message_lower for phrase in ["later", "think about", "jumia", "konga", "let me check"]):
            return "objection"
        
        return "general_inquiry"
    
    def _handle_catalog_search(self, session: Session, customer: Customer, message: str) -> Dict:
        """Handle product catalog searches"""
        # Extract product keywords
        keywords = self._extract_product_keywords(message)
        
        # Search products
        products = self._search_products(session, keywords)
        
        if not products:
            response = "Sorry, we don't have that item in stock right now. But we get new stock weekly! What specific phone are you looking for?"
            return {"response": response, "products": []}
        
        # Format product list
        product_list = []
        response_parts = ["Here's what we have available:\n"]
        
        for product in products[:5]:  # Limit to 5 results
            if product.inventory_count > 0:
                product_list.append({
                    "id": product.id,
                    "name": product.name,
                    "price": product.current_price,
                    "stock": product.inventory_count
                })
                response_parts.append(f"📱 {product.name} - ₦{product.current_price:,.0f} ({product.inventory_count} available)")
        
        response_parts.append("\nWhich one interests you? I can give you more details!")
        
        response = "\n".join(response_parts)
        self._log_message(session, customer.id, response, is_from_customer=False)
        
        return {
            "response": response,
            "products": product_list,
            "intent": "catalog_search"
        }
    
    def _handle_negotiation(self, session: Session, customer: Customer, message: str) -> Dict:
        product = self._get_conversation_product(session, customer)
        if not product:
            return {"response": "Which product are you interested in?"}

        # Extract price from message
        offered_price = self._extract_price_from_message(message)
        
        if offered_price and offered_price > 0:
            # Use Python logic for price enforcement
            return self._negotiate_price(session, customer, product, offered_price, message)
        else:
            # General price complaint - use AI but without floor price in prompt
            prompt = f"""You are a Nigerian phone retailer. Customer says: "{message}" about {product.name} (₦{product.current_price:,.0f}). 
            Defend the value and ask for their budget. Keep it short and Nigerian style."""
            
            ai_response = self.llama.generate_text(prompt)
            response = ai_response or "What's your budget? I can work with you."
            self._log_message(session, customer.id, response, is_from_customer=False, product_id=product.id)
            return {"response": response, "intent": "negotiation"}
    
    def _negotiate_price(self, session: Session, customer: Customer, product: Product, offered_price: float, message: str) -> Dict:
        """Handle specific price negotiations with Python floor price enforcement"""
        
        if offered_price >= product.min_negotiable_price:
            # Accept offer
            response = f"Deal! ₦{offered_price:,.0f} works. Let me get your delivery details."
            self._log_message(session, customer.id, response, is_from_customer=False, product_id=product.id)
            return {"response": response, "status": "accepted", "negotiated_price": offered_price}
        
        elif offered_price >= product.min_negotiable_price * 0.9:
            # Counter-offer slightly above floor
            counter_price = product.min_negotiable_price + 500
            response = f"I hear you. My final price is ₦{counter_price:,.0f} - that's the lowest I can go for quality. Deal?"
            self._log_message(session, customer.id, response, is_from_customer=False, product_id=product.id)
            return {"response": response, "status": "counter_offer", "counter_price": counter_price}
        
        else:
            # Reject - too low
            response = f"₦{offered_price:,.0f} is too low for original quality. My best price is ₦{product.min_negotiable_price:,.0f}. Worth it for genuine product."
            self._log_message(session, customer.id, response, is_from_customer=False, product_id=product.id)
            return {"response": response, "status": "rejected", "floor_price": product.min_negotiable_price}
    
    def _handle_order_creation(self, session: Session, customer: Customer, message: str) -> Dict:
        """Handle order creation process"""
        
        # Check if customer has provided delivery details
        if self._has_delivery_info(message):
            return self._create_order(session, customer, message)
        else:
            # Ask for delivery information
            response = "Great! I'm ready to process your order. Please provide:\n\n1. Your full name\n2. Delivery address\n3. Phone number for delivery updates"
            
            return {
                "response": response,
                "status": "awaiting_delivery_info"
            }
    
    def _handle_objection(self, session: Session, customer: Customer, message: str) -> Dict:
        """Handle customer objections using AI"""
        
        product = self._get_conversation_product(session, customer)
        
        prompt = f"""
        Customer objection: "{message}"
        Product: {product.name if product else "General inquiry"}
        Price: ₦{product.current_price if product else 0}
        
        Generate a helpful, Nigerian-context response that:
        1. Acknowledges their concern
        2. Provides value reinforcement
        3. Creates urgency without being pushy
        4. Keeps the conversation moving forward
        
        Be professional but friendly. Max 2 sentences.
        """
        
        ai_response = self.llama.generate_text(prompt)
        
        if not ai_response:
            ai_response = "I understand you want to think about it. Quality phones move fast in this market - let me know if you have any questions!"
        
        return {
            "response": ai_response,
            "intent": "objection_handling"
        }
    
    def _handle_general_inquiry(self, session: Session, customer: Customer, message: str) -> Dict:
        """Handle general inquiries with AI assistance - NO FLOOR PRICE IN PROMPT"""
        
        product = self._get_conversation_product(session, customer)
        
        if product:
            # Safe prompt without floor price
            prompt = f"""You are a Nigerian phone retailer. Customer says: "{message}" 
            Product: {product.name} - ₦{product.current_price:,.0f} ({product.inventory_count} in stock)
            Respond professionally, highlight value, ask for the sale. Keep it short."""
        else:
            prompt = f"You are a Nigerian phone retailer. Customer says: '{message}'. Respond professionally and ask what they need."
        
        ai_response = self.llama.generate_text(prompt)
        
        if not ai_response:
            ai_response = "Hello! Welcome to our store. We have the best phones at great prices. What are you looking for today?"
        
        self._log_message(session, customer.id, ai_response, is_from_customer=False)
        return {"response": ai_response, "intent": "general_inquiry"}
    
    def _create_order(self, session: Session, customer: Customer, message: str) -> Dict:
        """Create confirmed order and return order details"""
        
        # Extract delivery info from message
        delivery_info = self._extract_delivery_info(message)
        
        # Get product from conversation context
        product = self._get_conversation_product(session, customer)
        
        if not product:
            return {"response": "Please specify which product you want to order."}
        
        # Create order
        order = Order(
            customer_id=customer.id,
            total_amount=product.current_price,
            delivery_address=delivery_info.get("address", ""),
            status=OrderStatus.CONFIRMED
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        
        # Create order item
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=1,
            unit_price=product.current_price,
            total_price=product.current_price
        )
        session.add(order_item)
        
        # Update inventory
        product.inventory_count -= 1
        session.commit()
        
        response = f"✅ Order confirmed!\n\nOrder #{order.id}\n{product.name} - ₦{product.current_price:,.0f}\n\nDelivery: {delivery_info.get('address', 'Address provided')}\n\nYou'll receive delivery updates on this number. Thank you for your business!"
        
        # Log bot response
        self._log_message(session, customer.id, response, is_from_customer=False, product_id=product.id)
        
        return {
            "response": response,
            "order_id": order.id,
            "status": "order_created",
            "total_amount": product.current_price
        }
    
    # Helper methods
    def _extract_product_keywords(self, message: str) -> List[str]:
        """Extract product search keywords"""
        keywords = []
        message_lower = message.lower()
        
        # Common phone brands and models
        brands = ["iphone", "samsung", "huawei", "xiaomi", "tecno", "infinix", "oppo", "vivo"]
        for brand in brands:
            if brand in message_lower:
                keywords.append(brand)
        
        # Extract model numbers
        model_pattern = r'\b\d+[a-z]*\b'
        models = re.findall(model_pattern, message_lower)
        keywords.extend(models)
        
        return keywords
    
    def _search_products(self, session: Session, keywords: List[str]) -> List[Product]:
        """Search products by keywords"""
        if not keywords:
            return []
        
        query = select(Product).where(Product.inventory_count > 0)
        
        # Add keyword filters
        for keyword in keywords:
            query = query.where(
                (Product.name.ilike(f"%{keyword}%")) | 
                (Product.model.ilike(f"%{keyword}%"))
            )
        
        return session.exec(query).all()
    
    def _extract_price_from_message(self, message: str) -> Optional[float]:
        """Extract price from customer message - FIX BUG 3: Find largest number, not first"""
        # Look for patterns like "15000", "15,000", "₦15000"
        price_pattern = r'₦?(\d{1,3}(?:,\d{3})*|\d+)'
        matches = re.findall(price_pattern, message.replace(',', ''))
        
        if matches:
            try:
                # Convert all matches to numbers and return the largest (likely the price)
                numbers = [float(match.replace(',', '')) for match in matches]
                return max(numbers)  # Return largest number, not first
            except ValueError:
                pass
        
        return None
    
    def _get_conversation_product(self, session: Session, customer: Customer) -> Optional[Product]:
        """Get the product being discussed from conversation history"""
        # Check recent conversation for product mentions
        for msg in reversed(self.conversation_history[-5:]):  # Last 5 messages
            if msg.get('product_id'):
                product = session.get(Product, msg['product_id'])
                if product and product.inventory_count > 0:
                    return product
        
        # Extract product from current conversation keywords
        keywords = []
        for msg in self.conversation_history[-3:]:
            if msg.get('is_from_customer', True):
                keywords.extend(self._extract_product_keywords(msg['message']))
        
        if keywords:
            products = self._search_products(session, keywords)
            if products:
                return products[0]
        
        # Fallback: return first available product
        return session.exec(select(Product).where(Product.inventory_count > 0)).first()
    
    def _has_delivery_info(self, message: str) -> bool:
        """Check if message contains delivery information"""
        message_lower = message.lower()
        return any(word in message_lower for word in ["address", "street", "road", "avenue", "close", "estate"])
    
    def _extract_delivery_info(self, message: str) -> Dict:
        """Extract delivery information from message"""
        # Simplified extraction - in production would use NLP
        return {
            "address": message.strip(),
            "phone": "Provided via WhatsApp"
        }