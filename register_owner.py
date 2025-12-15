#!/usr/bin/env python3
"""
Register the owner manually based on Evolution API data
"""

from app.database import get_session
from app.models import BusinessConfig
from sqlmodel import select
import uuid

def register_owner():
    """Register owner from Evolution API data"""
    
    # Owner phone from Evolution API
    owner_phone = "+2349025713730"
    
    session = next(get_session())
    
    # Get or create business config
    business_config = session.exec(select(BusinessConfig)).first()
    
    if not business_config:
        # Create new config
        ntfy_topic = f"naira_sniper_admin_{str(uuid.uuid4())[:8]}"
        business_config = BusinessConfig(
            ntfy_topic=ntfy_topic,
            bot_active=True,
            business_name="Naira Sniper Store",
            is_setup_complete=False
        )
        session.add(business_config)
    
    # Register owner
    business_config.owner_phone = owner_phone
    business_config.is_setup_complete = True
    session.commit()
    
    print(f"✅ Owner registered: {owner_phone}")
    print(f"📱 Ntfy topic: {business_config.ntfy_topic}")
    print(f"🤖 Bot active: {business_config.bot_active}")
    
    session.close()

if __name__ == "__main__":
    register_owner()