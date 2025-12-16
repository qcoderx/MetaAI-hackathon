from sqlmodel import Session
from app.database import engine
from app.models import Business

# Create test business directly in database
with Session(engine) as session:
    # Check if business exists
    existing = session.get(Business, 1)
    if existing:
        print(f"Business exists: {existing.business_name} - {existing.instance_name}")
    else:
        # Create new business
        business = Business(
            business_name="Test Store",
            phone_number="+2349025713730",
            instance_name="test_store"
        )
        session.add(business)
        session.commit()
        session.refresh(business)
        print(f"Created business: {business.business_name} - {business.instance_name}")