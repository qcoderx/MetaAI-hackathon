from groq import Groq
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
            self.client = Groq(api_key=api_key)
        self.vision_model = "llama-3.2-11b-vision-preview"
        self.text_model = "llama-3.3-70b-versatile"
    
    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate response from Llama 3"""
        if not self.client:
            print("Groq client not initialized")
            return None
            
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that responds in valid JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.text_model,
                temperature=temperature,
                max_tokens=1024
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return None
    
    def generate_json(self, prompt: str) -> dict:
        """Generate and parse JSON response"""
        if not self.client:
            return None
            
        response = self.generate(prompt, temperature=0.3)
        if response:
            try:
                # Extract JSON from response (handle markdown code blocks)
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0].strip()
                return json.loads(response)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                print(f"Response was: {response}")
                return None
        return None
    
    def generate_text(self, prompt: str) -> str:
        """Generate simple text response"""
        if not self.client:
            return "I'm currently unable to process your request. Please try again later."
            
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.text_model,
                temperature=0.7,
                max_tokens=512
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return "I'm currently unable to process your request. Please try again later."
    
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