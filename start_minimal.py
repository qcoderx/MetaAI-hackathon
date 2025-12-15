#!/usr/bin/env python3
"""
Minimal startup script for Naira Sniper without Celery tasks
Use this to test the core WhatsApp functionality first
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("🎯 Starting Naira Sniper - Minimal Mode")
    print("📱 WhatsApp AI Sales Assistant (Core Only)")
    print("🔗 API Docs: http://localhost:8000/docs")
    print("📱 WhatsApp Manager: http://localhost:8081/manager")
    print()
    print("⚠️  Celery tasks disabled for testing")
    print("✅ Core features available:")
    print("   - Dynamic owner registration")
    print("   - Self-chat admin console") 
    print("   - Customer AI responses")
    print("   - Order management")
    print("   - Ntfy.sh notifications")
    print()
    
    # Start FastAPI server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()