import requests
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import json

load_dotenv()

class WhatsAppClient:
    """WhatsApp Business API client for Meta Cloud API v18.0"""
    
    def __init__(self):
        self.phone_id = os.getenv("WHATSAPP_PHONE_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_id}"
        
        if not self.phone_id or not self.access_token:
            raise ValueError("WHATSAPP_PHONE_ID and WHATSAPP_ACCESS_TOKEN must be set")
    
    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make authenticated request to WhatsApp API"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(f"{self.base_url}/{endpoint}", 
                               headers=headers, 
                               json=payload)
        
        if response.status_code != 200:
            print(f"WhatsApp API Error: {response.status_code} - {response.text}")
            return {"error": response.text}
        
        return response.json()
    
    def send_message(self, phone: str, text: str) -> Dict[str, Any]:
        """Send basic text message"""
        # Clean phone number (remove + if present)
        phone = phone.lstrip('+')
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text}
        }
        
        return self._make_request("messages", payload)
    
    def send_template(self, phone: str, template_name: str, components: list) -> Dict[str, Any]:
        """Send WhatsApp Business template message"""
        phone = phone.lstrip('+')
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": components
            }
        }
        
        return self._make_request("messages", payload)
    
    def update_catalog_product(self, product_id: str, price: float) -> Dict[str, Any]:
        """Update product price in WhatsApp Business Catalog"""
        # Note: This requires Commerce Manager API access
        catalog_url = f"https://graph.facebook.com/v18.0/{product_id}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "price": int(price * 100),  # Price in kobo
            "currency": "NGN"
        }
        
        response = requests.post(catalog_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Catalog Update Error: {response.status_code} - {response.text}")
            return {"error": response.text}
        
        return response.json()

def send_price_drop_message(phone: str, customer_name: str, product_name: str, 
                           old_price: float, new_price: float, hours: int = 4) -> bool:
    """Send price drop alert using template from brain/prompts.py"""
    from brain.prompts import PRICE_DROP_TEMPLATE
    
    message = PRICE_DROP_TEMPLATE.format(
        customer_name=customer_name,
        product_name=product_name,
        new_price=f"{new_price:,.0f}",
        old_price=f"{old_price:,.0f}",
        hours=hours
    )
    
    client = WhatsAppClient()
    result = client.send_message(phone, message)
    
    return "error" not in result

def send_value_message(phone: str, customer_name: str, product_name: str, 
                      price: float, model_year: str = "2024", 
                      warranty: str = "6-month", 
                      extra_value: str = "Free delivery within Lagos") -> bool:
    """Send value reinforcement message using template from brain/prompts.py"""
    from brain.prompts import VALUE_REINFORCEMENT_TEMPLATE
    
    message = VALUE_REINFORCEMENT_TEMPLATE.format(
        customer_name=customer_name,
        product_name=product_name,
        price=f"{price:,.0f}",
        model_year=model_year,
        warranty=warranty,
        extra_value=extra_value
    )
    
    client = WhatsAppClient()
    result = client.send_message(phone, message)
    
    return "error" not in result