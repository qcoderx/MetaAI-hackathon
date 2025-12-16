# MetaAI-hackathon

# 🎯 Auto-Closer - Multimodal AI Sales Agent for WhatsApp Status

## The Problem
Nigerian vendors lose sales because they:
- Can't respond to WhatsApp status inquiries 24/7
- Miss visual context from customer screenshots
- Don't have automated lead qualification
- Lack personalized sales conversations

## The Solution
An AI agent that:
1. **Analyzes** WhatsApp status images with Vision AI
2. **Responds** intelligently to customer inquiries
3. **Qualifies** leads automatically
4. **Closes** sales with personalized messaging

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTO-CLOSER SYSTEM                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │   WHATSAPP   │─────▶│  STATUS      │                   │
│  │   WEBHOOK    │      │  REPLIES     │                   │
│  └──────────────┘      └──────┬───────┘                   │
│                               │                            │
│                               ▼                            │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │    REDIS     │◀─────│  VISION AI   │◀──── Llama 3.2   │
│  │ DEDUPLICATION│      │    AGENT     │      11B Vision   │
│  └──────────────┘      └──────┬───────┘                   │
│                               │                            │
│                               ▼                            │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │  BUSINESS    │      │   CUSTOMER   │                   │
│  │   RULES      │      │   TAGGING    │                   │
│  └──────────────┘      └──────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your GROQ_API_KEY and REDIS_URL

# Run server
python main.py
```

## 📁 Project Structure

```
auto-closer/
├── brain/              # 🧠 AI Logic
│   ├── llama_client.py # Groq/Llama 3.2 Vision wrapper
│   └── sales_agent.py  # Auto-Closer AI agent
│
├── app/                # 🏗️ Architecture
│   ├── database.py     # SQLModel setup
│   ├── models.py       # Database schema
│   └── routers/        # FastAPI endpoints
│       ├── rules.py    # Business rules CRUD
│       └── webhooks.py # WhatsApp webhook handler
│
└── main.py             # FastAPI application entry
```

## 🎯 Key Features

### ✅ Implemented
- Vision AI with Llama 3.2 11B Vision model
- WhatsApp Status reply detection
- Redis-based message deduplication
- Customer lead tagging and qualification
- Business rules management API
- Anti-spam protection
- Admin commands via WhatsApp

## 📚 Documentation

- API Docs: `http://localhost:8000/docs` (when server running)
- Business Rules: `POST /rules/` to configure categories and pricing

## 🤝 Team

**Quadri** - Systems Architect & AI Engineer  
Built: Vision AI, Sales Agent, Database, API

**Abdulrahman** - Integration Engineer  
Built: WhatsApp Integration, Redis Setup

## 📊 Example Flow

1. Customer replies to WhatsApp status with product image
2. Vision AI analyzes image context and customer message
3. System tags customer as qualified lead
4. AI generates personalized sales response
5. WhatsApp sends automated follow-up
6. Lead tracked in database for conversion

---

**Built for Meta AI Hackathon 2024** 🚀