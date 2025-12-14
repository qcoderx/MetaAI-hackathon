import requests
import os
import time
from dotenv import load_dotenv
from typing import Dict, Any, Optional

load_dotenv()

class EvolutionClient:
    """Evolution API v2 client for WhatsApp messaging"""
    
    def __init__(self, instance_name: str = "naira_sniper_v1"):
        self.base_url = "http://localhost:8081"
        self.api_key = "naira-sniper-secret-key"
        self.instance_name = instance_name
        
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Auto-initialize instance and webhook
        self._ensure_instance_exists()
        self.set_webhook()
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make authenticated request to Evolution API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code not in [200, 201]:
                print(f"Evolution API Error: {response.status_code} - {response.text}")
                return {"error": response.text}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Evolution API Connection Error: {e}")
            return {"error": str(e)}
    
    def _ensure_instance_exists(self):
        """Check if instance exists, create if not"""
        # Check existing instances
        result = self._make_request("GET", "/instance/fetchInstances")
        
        if "error" in result:
            print(f"Failed to fetch instances: {result['error']}")
            return
        
        # Check if our instance exists
        instances = result.get("data", [])
        instance_exists = any(
            instance.get("instance", {}).get("instanceName") == self.instance_name 
            for instance in instances
        )
        
        if not instance_exists:
            print(f"Creating Evolution API instance: {self.instance_name}")
            self._create_instance()
        else:
            print(f"Evolution API instance exists: {self.instance_name}")
    
    def _create_instance(self):
        """Create new WhatsApp instance"""
        data = {
            "instanceName": self.instance_name,
            "integration": "WHATSAPP-BAILEYS"
        }
        
        result = self._make_request("POST", "/instance/create", data)
        
        if "error" not in result:
            print(f"Instance created successfully: {self.instance_name}")
            time.sleep(2)  # Wait for instance to initialize
        else:
            print(f"Failed to create instance: {result['error']}")
    
    def get_qr_code(self) -> Optional[str]:
        """Get QR code for WhatsApp connection"""
        result = self._make_request("GET", f"/instance/connect/{self.instance_name}")
        
        if "error" in result:
            print(f"Failed to get QR code: {result['error']}")
            return None
        
        # Extract base64 QR code
        qr_data = result.get("base64", "")
        if qr_data:
            print("QR Code available. Scan with WhatsApp to connect.")
            return qr_data
        
        return None
    
    def send_message(self, phone: str, text: str) -> Dict[str, Any]:
        """Send text message via Evolution API v2"""
        # Clean phone number
        phone = phone.lstrip('+').replace(' ', '').replace('-', '')
        
        # Ensure phone has country code (Nigeria +234)
        if not phone.startswith('234') and phone.startswith('0'):
            phone = '234' + phone[1:]
        elif not phone.startswith('234'):
            phone = '234' + phone
        
        # Add @s.whatsapp.net suffix for v2
        if not phone.endswith('@s.whatsapp.net'):
            phone = phone + '@s.whatsapp.net'
        
        data = {
            "number": phone,
            "text": text
        }
        
        result = self._make_request("POST", f"/message/sendText/{self.instance_name}", data)
        
        if "error" not in result:
            print(f"Message sent to {phone}: {text[:50]}...")
            return result
        else:
            print(f"Failed to send message to {phone}: {result['error']}")
            return result
    
    def send_template(self, phone: str, template_name: str, components: list) -> Dict[str, Any]:
        """
        Polyfill for template messages - Evolution API doesn't use Meta templates
        Just sends the formatted text as regular message
        """
        # For now, just send as regular text message
        # In production, you'd format the template with components
        text = f"Template: {template_name}"
        return self.send_message(phone, text)
    
    def get_instance_status(self) -> Dict[str, Any]:
        """Get instance connection status"""
        result = self._make_request("GET", f"/instance/connectionState/{self.instance_name}")
        return result
    
    def set_webhook(self) -> Dict[str, Any]:
        """Configure webhook to receive incoming messages"""
        webhook_data = {
            "url": "http://host.docker.internal:8000/webhook/evolution",
            "enabled": True,
            "events": ["messages.upsert"]
        }
        
        result = self._make_request("POST", f"/webhook/set/{self.instance_name}", webhook_data)
        
        if "error" not in result:
            print(f"Webhook configured for {self.instance_name}")
        else:
            print(f"Failed to set webhook: {result['error']}")
        
        return result

def send_price_drop_message(phone: str, customer_name: str, product_name: str, 
                           old_price: float, new_price: float, hours: int = 4) -> bool:
    """Send price drop alert using Evolution API"""
    from brain.prompts import PRICE_DROP_TEMPLATE
    
    message = PRICE_DROP_TEMPLATE.format(
        customer_name=customer_name,
        product_name=product_name,
        new_price=f"{new_price:,.0f}",
        old_price=f"{old_price:,.0f}",
        hours=hours
    )
    
    client = EvolutionClient()
    result = client.send_message(phone, message)
    
    return "error" not in result

def send_value_message(phone: str, customer_name: str, product_name: str, 
                      price: float, model_year: str = "2024", 
                      warranty: str = "6-month", 
                      extra_value: str = "Free delivery within Lagos") -> bool:
    """Send value reinforcement message using Evolution API"""
    from brain.prompts import VALUE_REINFORCEMENT_TEMPLATE
    
    message = VALUE_REINFORCEMENT_TEMPLATE.format(
        customer_name=customer_name,
        product_name=product_name,
        price=f"{price:,.0f}",
        model_year=model_year,
        warranty=warranty,
        extra_value=extra_value
    )
    
    client = EvolutionClient()
    result = client.send_message(phone, message)
    
    return "error" not in result