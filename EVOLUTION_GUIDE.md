# 📱 Evolution API v2 Integration Guide

## Overview
Naira Sniper now uses **Evolution API v2.1.1** instead of Meta WhatsApp Cloud API. This allows using any phone number without business verification and includes webhook support for incoming messages.

## 🚀 Quick Start

### Step 1: Install Docker
Download and install Docker Desktop:
- **Windows/Mac**: https://www.docker.com/products/docker-desktop
- **Linux**: `sudo apt install docker.io docker-compose`

### Step 2: Configure Environment
Evolution API v2 uses a hardcoded API key for simplicity:
```bash
# API key is hardcoded as: naira-sniper-secret-key
# No .env configuration needed for Evolution API
```

### Step 3: Start Evolution API
```bash
# Start the Evolution API container
docker-compose -f docker-compose.evolution.yml up -d

# Or use the deployment script
python deploy.py
```

### Step 4: Connect WhatsApp
1. Open WhatsApp Manager: http://localhost:8081/manager
2. Your instance will be auto-created as `naira_sniper_v1`
3. Webhook will be auto-configured to `/webhook/evolution`
4. Click "Connect" to get QR code
5. Scan QR code with your WhatsApp mobile app
6. Wait for "Connected" status
7. Test by sending a message to your WhatsApp number

## 📋 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Evolution API v2 | http://localhost:8081 | Main API endpoint |
| WhatsApp Manager | http://localhost:8081/manager | Web interface |
| Naira Sniper API | http://localhost:8000 | Main application |
| Webhook Endpoint | http://localhost:8000/webhook/evolution | Incoming messages |
| API Documentation | http://localhost:8000/docs | FastAPI docs |

## 🔧 Configuration

### Environment Variables
```bash
# Required
GROQ_API_KEY=gsk_your_groq_key_here
EVOLUTION_API_KEY=naira-sniper-secret

# Optional (for database)
DATABASE_URL=sqlite:///./naira_sniper.db
REDIS_URL=redis://localhost:6379/0
```

### Docker Compose Configuration
The `docker-compose.evolution.yml` file configures:
- **Port**: 8081 (host) → 8080 (container)
- **Authentication**: API key protection
- **Storage**: Persistent volumes for instances and data
- **Database**: Disabled (uses local file storage)

## 📱 WhatsApp Connection Process

### 1. Automatic Instance Creation
When you start the system, it automatically:
- Creates instance named `naira_sniper_v1`
- Uses `WHATSAPP-BAILEYS` integration
- Generates connection QR code

### 2. Manual Connection (if needed)
```bash
# Check instance status
curl -H "apikey: naira-sniper-secret" \
  http://localhost:8081/instance/connectionState/naira_sniper_v1

# Get QR code
curl -H "apikey: naira-sniper-secret" \
  http://localhost:8081/instance/connect/naira_sniper_v1
```

### 3. Connection States
- **close**: Not connected
- **connecting**: Generating QR code
- **open**: Connected and ready

## 🧪 Testing

### Test Message Sending
```python
from engine.whatsapp_evolution import EvolutionClient

client = EvolutionClient()
result = client.send_message("2348012345678", "Test message from Naira Sniper!")
print(result)
```

### Test via API
```bash
# Send test message
curl -X POST http://localhost:8081/message/sendText/naira_sniper_v1 \
  -H "apikey: naira-sniper-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "2348012345678",
    "text": "Hello from Evolution API!"
  }'
```

## 🔍 Monitoring

### Check Container Status
```bash
# View running containers
docker ps

# View Evolution API logs
docker logs naira_sniper_evolution

# Follow logs in real-time
docker logs -f naira_sniper_evolution
```

### Check Instance Health
```bash
# List all instances
curl -H "apikey: naira-sniper-secret" \
  http://localhost:8081/instance/fetchInstances

# Check specific instance
curl -H "apikey: naira-sniper-secret" \
  http://localhost:8081/instance/connectionState/naira_sniper_v1
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Container Won't Start
```bash
# Check Docker is running
docker --version

# Check port availability
netstat -an | grep 8081

# Restart container
docker-compose -f docker-compose.evolution.yml restart
```

#### 2. QR Code Not Appearing
```bash
# Restart instance
curl -X DELETE -H "apikey: naira-sniper-secret" \
  http://localhost:8081/instance/logout/naira_sniper_v1

# Reconnect
curl -H "apikey: naira-sniper-secret" \
  http://localhost:8081/instance/connect/naira_sniper_v1
```

#### 3. Messages Not Sending
- Check WhatsApp connection status
- Verify phone number format (234xxxxxxxxx)
- Check Evolution API logs
- Ensure WhatsApp Web is not open elsewhere

### Phone Number Format
Evolution API expects numbers in international format:
- ✅ Correct: `2348012345678`
- ❌ Wrong: `+2348012345678`, `08012345678`

The client automatically formats Nigerian numbers.

## 🔄 Migration from Meta API

### What Changed
- **Before**: Meta WhatsApp Cloud API (business verification required)
- **After**: Evolution API v1 (any phone number)

### Code Changes
- `engine/whatsapp.py` → `engine/whatsapp_evolution.py`
- Meta templates → Plain text messages
- Business catalog → Not supported (Evolution limitation)

### Environment Variables
- **Removed**: `WHATSAPP_PHONE_ID`, `WHATSAPP_ACCESS_TOKEN`
- **Added**: `EVOLUTION_API_KEY`

## 📊 Performance

### Limits
- **Rate Limit**: ~20 messages/minute (WhatsApp limitation)
- **Concurrent**: Single phone number per instance
- **Storage**: Local file system (no external database)

### Scaling
For production scaling:
- Use multiple instances with different phone numbers
- Enable PostgreSQL database in Evolution API
- Use Redis for session management

## 🔐 Security

### API Key Protection
- Change default `EVOLUTION_API_KEY` in production
- Use strong, random API keys
- Restrict network access to Evolution API port

### WhatsApp Security
- Keep phone number secure
- Monitor for unauthorized access
- Use 2FA on WhatsApp account

## 📚 API Reference

### Key Endpoints (Evolution API v1)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/instance/fetchInstances` | List instances |
| POST | `/instance/create` | Create instance |
| GET | `/instance/connect/{instance}` | Get QR code |
| GET | `/instance/connectionState/{instance}` | Check status |
| POST | `/message/sendText/{instance}` | Send message |
| DELETE | `/instance/logout/{instance}` | Disconnect |

### Message Format
```json
{
  "number": "2348012345678",
  "text": "Your message here"
}
```

---

## 🎯 Next Steps

1. **Start Services**: `python deploy.py`
2. **Connect WhatsApp**: Scan QR at http://localhost:8081/manager
3. **Test Messaging**: `python test_integration.py`
4. **Monitor Logs**: `docker logs -f naira_sniper_evolution`

**Evolution API is now your WhatsApp gateway! 📱✨**