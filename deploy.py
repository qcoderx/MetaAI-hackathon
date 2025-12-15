#!/usr/bin/env python3
"""
Naira Sniper Deployment Script
Starts all system components
"""
import subprocess
import sys
import time
import os
import docker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_dependencies():
    """Check if all required dependencies are installed - FIX BUG 16"""
    try:
        import requests
        import redis  # Safe import
        # Don't import celery here - it might try to connect immediately
        print("✅ Core dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
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
        print("Edit .env file and add your API keys")
        return False
    
    print("✅ Environment variables configured")
    print("✅ Evolution API v2 configured (using hardcoded key)")
    
    return True

def start_redis():
    """Check Redis connection (local or cloud)"""
    try:
        import redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        if redis_url.startswith('redis://localhost'):
            # Local Redis
            r = redis.Redis(host='localhost', port=6379, db=0)
        else:
            # Cloud Redis (parse URL)
            r = redis.from_url(redis_url)
        
        r.ping()
        print("✅ Redis is connected")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        if 'localhost' in os.getenv('REDIS_URL', ''):
            print("Please start local Redis server")
        else:
            print("Check your REDIS_URL in .env file")
        return False

def start_evolution_api():
    """Start Evolution API container"""
    try:
        if not os.path.exists("docker-compose.evolution.yml"):
            print("❌ docker-compose.evolution.yml not found")
            return False
        
        print("🐳 Starting Evolution API v2 container...")
        result = subprocess.run([
            "docker-compose", "-f", "docker-compose.evolution.yml", 
            "up", "-d"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Evolution API v2 container started")
            print("📱 WhatsApp Manager: http://localhost:8081/manager")
            print("🔗 Webhook configured: /webhook/evolution")
            time.sleep(5)  # Wait for container to be ready
            return True
        else:
            print(f"❌ Failed to start Evolution API: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Docker or docker-compose not found")
        print("Please install Docker Desktop")
        return False
    except Exception as e:
        print(f"❌ Error starting Evolution API: {e}")
        return False

def start_api_server():
    """Start FastAPI server"""
    print("🚀 Starting API server...")
    return subprocess.Popen([
        sys.executable, "main.py"
    ])

def start_celery_worker():
    """Start Celery worker - FIX BUG 16: Safe import after Redis is ready"""
    print("🔧 Starting Celery worker...")
    # Now safe to import since Redis is confirmed running
    try:
        from engine.workers import celery_app
        print("✅ Celery imports successful")
    except Exception as e:
        print(f"⚠️ Celery import warning: {e}")
    
    return subprocess.Popen([
        "celery", "-A", "engine.workers", "worker", "--loglevel=info"
    ])

def start_celery_beat():
    """Start Celery beat scheduler - FIX BUG 16: Safe import after Redis is ready"""
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
    
    if not start_evolution_api():
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
        print("- Evolution API v2: http://localhost:8081")
        print("- WhatsApp Manager: http://localhost:8081/manager")
        print("- Webhook Endpoint: http://localhost:8000/webhook/evolution")
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