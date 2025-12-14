#!/usr/bin/env python3
"""
Simple Naira Sniper Deployment (No Docker)
Starts core services without Evolution API container
"""
import subprocess
import sys
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import requests
        import celery
        import redis
        print("✅ Core dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def check_environment():
    """Check if environment variables are set"""
    required_vars = ["GROQ_API_KEY"]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing required environment variables: {missing}")
        return False
    
    print("✅ Environment variables configured")
    return True

def check_redis():
    """Check Redis connection"""
    try:
        import redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        print("✅ Redis is connected")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def start_api_server():
    """Start FastAPI server"""
    print("🚀 Starting API server...")
    return subprocess.Popen([sys.executable, "main.py"])

def start_celery_worker():
    """Start Celery worker"""
    print("🔧 Starting Celery worker...")
    return subprocess.Popen([
        "celery", "-A", "engine.workers", "worker", "--loglevel=info"
    ])

def main():
    print("🎯 Naira Sniper Simple Deployment")
    print("=" * 40)
    
    # Pre-flight checks
    if not check_dependencies():
        sys.exit(1)
    
    if not check_environment():
        sys.exit(1)
    
    if not check_redis():
        sys.exit(1)
    
    print("\n⚠️  Running without Evolution API (Docker not available)")
    print("   WhatsApp messaging will not work until Docker is installed")
    
    # Start services
    processes = []
    
    try:
        # Start API server
        api_process = start_api_server()
        processes.append(("API Server", api_process))
        time.sleep(3)
        
        # Start Celery worker
        worker_process = start_celery_worker()
        processes.append(("Celery Worker", worker_process))
        
        print("\n🎉 Core services started!")
        print("\n📊 Service Status:")
        print("- API Server: http://localhost:8000")
        print("- API Docs: http://localhost:8000/docs")
        print("- Celery Worker: Running background tasks")
        print("- Evolution API: ❌ Not available (install Docker)")
        
        print("\n⚡ Quick Test:")
        print("Run: python test_system.py")
        
        print("\n🐳 To enable WhatsApp:")
        print("1. Install Docker Desktop")
        print("2. Run: python deploy.py")
        
        print("\nPress Ctrl+C to stop services...")
        
        # Wait for interrupt
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        for name, process in processes:
            print(f"Stopping {name}...")
            process.terminate()
            process.wait()
        print("✅ Services stopped")

if __name__ == "__main__":
    main()