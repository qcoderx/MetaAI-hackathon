from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List
import secrets

class Business(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    business_name: str
    phone_number: str = Field(unique=True, index=True)
    instance_name: str = Field(unique=True, index=True)
    api_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    customers: List["Customer"] = Relationship(back_populates="business")
    business_rules: List["BusinessRule"] = Relationship(back_populates="business")
    status_replies: List["StatusReply"] = Relationship(back_populates="business")

class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: int = Field(foreign_key="business.id")
    phone: str = Field(index=True)
    name: Optional[str] = None
    tags: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    business: Business = Relationship(back_populates="customers")
    status_replies: List["StatusReply"] = Relationship(back_populates="customer")

class BusinessRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: int = Field(foreign_key="business.id")
    category: str = Field(index=True)
    visual_keywords: str
    min_price: float
    negotiation_instruction: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    business: Business = Relationship(back_populates="business_rules")

class StatusReply(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: int = Field(foreign_key="business.id")
    customer_id: int = Field(foreign_key="customer.id")
    status_image_url: str
    detected_category: str
    user_message: str
    ai_response: str
    confidence_score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    business: Business = Relationship(back_populates="status_replies")
    customer: Customer = Relationship(back_populates="status_replies")