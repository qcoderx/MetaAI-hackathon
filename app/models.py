from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List

class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = Field(unique=True, index=True)
    name: Optional[str] = None
    tags: str = Field(default="")  # Comma separated tags
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    status_replies: List["StatusReply"] = Relationship(back_populates="customer")

class BusinessRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(index=True)  # e.g., "Wig", "Sneaker", "Real Estate"
    visual_keywords: str  # Comma-separated visual tags for Llama
    min_price: float  # Floor price
    negotiation_instruction: str  # e.g., "Price is firm. Delivery 2k. Payment validates order."
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class StatusReply(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    status_image_url: str
    detected_category: str
    user_message: str
    ai_response: str
    confidence_score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    customer: Customer = Relationship(back_populates="status_replies")