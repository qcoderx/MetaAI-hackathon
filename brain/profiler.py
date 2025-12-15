from brain.llama_client import LlamaClient
from brain.prompts import INTENT_CLASSIFIER_PROMPT
from app.models import CustomerType, CustomerTypeSignal, Customer
from sqlmodel import Session, select
from datetime import datetime, timedelta

class CustomerProfiler:
    def __init__(self):
        self.llama = LlamaClient()
        
        # Fallback keyword matching
        self.price_keywords = [
            "last price", "how much last", "reduce", "too cost", 
            "can you drop", "cheaper", "I see am for", "too much"
        ]
        self.quality_keywords = [
            "original", "na original", "strong", "which model", 
            "warranty", "how long", "fake", "real", "durable"
        ]
    
    def classify_message(self, message: str) -> dict:
        """Classify customer message using Llama 3"""
        prompt = INTENT_CLASSIFIER_PROMPT.format(message=message)
        result = self.llama.generate_json(prompt)
        
        if result:
            return result
        
        # Fallback to keyword matching
        return self._keyword_classify(message)
    
    def _keyword_classify(self, message: str) -> dict:
        """Context-aware keyword classification - FIX BUG 14"""
        message_lower = message.lower()
        
        # Check for negative context that flips meaning
        negative_words = ['hate', 'expensive', 'too much', 'cheap', 'dont want', 'not interested']
        has_negative = any(neg in message_lower for neg in negative_words)
        
        price_score = sum(1 for kw in self.price_keywords if kw in message_lower)
        quality_score = sum(1 for kw in self.quality_keywords if kw in message_lower)
        
        # If negative context + premium brand mention = price sensitive
        premium_brands = ['iphone', 'samsung galaxy s', 'macbook']
        has_premium = any(brand in message_lower for brand in premium_brands)
        
        if has_negative and has_premium:
            return {
                "customer_type": "price_sensitive",
                "confidence": 0.8,
                "key_signals": ["negative_premium_context"]
            }
        
        if price_score > quality_score:
            return {
                "customer_type": "price_sensitive",
                "confidence": min(0.6 + (price_score * 0.1), 0.9),
                "key_signals": [kw for kw in self.price_keywords if kw in message_lower]
            }
        elif quality_score > price_score:
            return {
                "customer_type": "quality_sensitive",
                "confidence": min(0.6 + (quality_score * 0.1), 0.9),
                "key_signals": [kw for kw in self.quality_keywords if kw in message_lower]
            }
        else:
            return {
                "customer_type": "unknown",
                "confidence": 0.5,
                "key_signals": []
            }
    
    def update_customer_profile(self, session: Session, customer_id: int, message: str):
        """Analyze message and update customer profile"""
        classification = self.classify_message(message)
        
        # Store signal
        signal = CustomerTypeSignal(
            customer_id=customer_id,
            signal_text=message,
            signal_type=CustomerType(classification["customer_type"]),
            confidence=classification["confidence"]
        )
        session.add(signal)
        
        # Update customer type based on recent signals
        recent_signals = session.exec(
            select(CustomerTypeSignal)
            .where(CustomerTypeSignal.customer_id == customer_id)
            .where(CustomerTypeSignal.detected_at > datetime.utcnow() - timedelta(days=30))
        ).all()
        
        if len(recent_signals) >= 2:
            # Calculate weighted average
            price_score = sum(s.confidence for s in recent_signals if s.signal_type == CustomerType.PRICE_SENSITIVE)
            quality_score = sum(s.confidence for s in recent_signals if s.signal_type == CustomerType.QUALITY_SENSITIVE)
            
            customer = session.get(Customer, customer_id)
            if customer:
                if price_score > quality_score:
                    customer.customer_type = CustomerType.PRICE_SENSITIVE
                elif quality_score > price_score:
                    customer.customer_type = CustomerType.QUALITY_SENSITIVE
                customer.last_interaction = datetime.utcnow()
                session.add(customer)
        
        session.commit()
        return classification
