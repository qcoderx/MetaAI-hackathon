#!/usr/bin/env python3
"""
Naira Sniper Deployment Script
Starts all system components
"""
import subprocess
import sys
import time
import os

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import requests
        import celery
        import redis
        import instaloader
        import playwright
        print("✅ All dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def check_environment():
    """Check if environment variables are set"""
    required_vars = ["GROQ_API_KEY"]
    optional_vars = ["WHATSAPP_PHONE_ID", "WHATSAPP_ACCESS_TOKEN"]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing required environment variables: {missing}")
        print("Edit .env file and add your API keys")
        return False
    
    print("✅ Environment variables configured")
    
    # Check optional WhatsApp vars
    whatsapp_configured = all(os.getenv(var) for var in optional_vars)
    if not whatsapp_configured:
        print("⚠️  WhatsApp not configured (messages won't be sent)")
    else:
        print("✅ WhatsApp configured")
    
    return True

def start_redis():
    """Start Redis server if not running"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running")
        return True
    except:
        print("❌ Redis not running. Please start Redis server:")
        print("Windows: Download from https://redis.io/download")
        print("Linux/Mac: sudo service redis-server start")
        return False

def start_api_server():
    """Start FastAPI server"""
    print("🚀 Starting API server...")
    return subprocess.Popen([
        sys.executable, "main.py"
    ])

def start_celery_worker():
    """Start Celery worker"""
    print("🔧 Starting Celery worker...")
    return subprocess.Popen([
        "celery", "-A", "engine.workers", "worker", "--loglevel=info"
    ])

def start_celery_beat():
    """Start Celery beat scheduler"""
    print("⏰ Starting Celery scheduler...")
    return subprocess.Popen([
        "celery", "-A", "engine.workers", "beat", "--loglevel=info"
    ])

def main():
    print("🎯 Naira Sniper Deployment")
    print("=" * 40)
    
    # Pre-flight checks
    if not check_dependencies():
        sys.exit(1)
    
    if not check_environment():
        sys.exit(1)
    
    if not start_redis():
        sys.exit(1)
    
    # Start services
    processes = []
    
    try:
        # Start API server
        api_process = start_api_server()
        processes.append(("API Server", api_process))
        time.sleep(3)  # Give API time to start
        
        # Start Celery worker
        worker_process = start_celery_worker()
        processes.append(("Celery Worker", worker_process))
        time.sleep(2)
        
        # Start Celery beat
        beat_process = start_celery_beat()
        processes.append(("Celery Beat", beat_process))
        
        print("\n🎉 All services started successfully!")
        print("\n📊 Service Status:")
        print("- API Server: http://localhost:8000")
        print("- API Docs: http://localhost:8000/docs")
        print("- Celery Worker: Running background tasks")
        print("- Celery Beat: Scheduling automated tasks")
        
        print("\n🔄 Automated Tasks:")
        print("- Market scraping: Every 30 minutes")
        print("- Instagram monitoring: Every hour")
        print("- Ghost retargeting: Every 2 hours")
        print("- Database cleanup: Daily")
        
        print("\n⚡ Quick Test:")
        print("Run: python test_system.py")
        
        print("\nPress Ctrl+C to stop all services...")
        
        # Wait for interrupt
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        for name, process in processes:
            print(f"Stopping {name}...")
            process.terminate()
            process.wait()
        print("✅ All services stopped")

if __name__ == "__main__":
    main()