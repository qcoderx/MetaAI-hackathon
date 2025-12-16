import os
import json
from dotenv import load_dotenv

load_dotenv()

class LlamaClient:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("Warning: GROQ_API_KEY not found")
            self.client = None
        else:
            try:
                from groq import Groq
                self.client = Groq(api_key=api_key)
            except ImportError:
                print("Groq library not available")
                self.client = None
        self.vision_model = "llama-3.2-11b-vision-preview"
        self.text_model = "llama-3.3-70b-versatile"
    
    def analyze_image_context(self, image_url: str, user_text: str, rules_context: str) -> dict:
        """Analyze WhatsApp status image with Vision AI"""
        if not self.client:
            return {"detected_category": "unknown", "confidence": 0.0, "reply": "System unavailable", "is_sales_lead": False}
        
        prompt = f"""You are the 'Auto-Closer' AI. IMAGE: A WhatsApp Status posted by a vendor. TEXT: A customer's reply to this specific status: '{user_text}'. VENDOR RULES: {rules_context} YOUR TASK:

Identify the item in the image. Does it match any vendor rule category?

IGNORE 'Sold Out' stickers if the user asks 'Do you have more?'.

Formulate a short, friendly, Nigerian-business style reply based on the Rule's 'negotiation_instruction'.

OUTPUT JSON ONLY: {{ 'detected_category': 'string', 'confidence': float, 'reply': 'string (the actual message to send)', 'is_sales_lead': bool }}"""
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                model=self.vision_model,
                temperature=0.3,
                max_tokens=1024
            )
            
            response = chat_completion.choices[0].message.content
            
            # Parse JSON response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            return json.loads(response)
            
        except Exception as e:
            print(f"Vision AI error: {e}")
            return {
                "detected_category": "unknown",
                "confidence": 0.0,
                "reply": "I can't see the image clearly. What caught your eye?",
                "is_sales_lead": False
            }