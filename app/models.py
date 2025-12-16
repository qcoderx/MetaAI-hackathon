from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class CustomerType(str, Enum):
    PRICE_SENSITIVE = "price_sensitive"
    QUALITY_SENSITIVE = "quality_sensitive"
    UNKNOWN = "unknown"

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    DELIVERED = "delivered"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"

class BusinessRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(index=True)  # e.g., "Wig", "Sneaker", "Real Estate", "Food"
    visual_keywords: str  # Comma-separated visual tags for Llama Vision
    min_price: float  # The floor price
    negotiation_instruction: str  # e.g., "Price is firm. Delivery 2k. Payment validates order."
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class StatusReply(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    status_image_url: str  # URL of the image they replied to
    detected_category: str  # What Vision AI saw
    user_message: str  # What they asked
    ai_response: str  # What we replied
    confidence_score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = Field(unique=True, index=True)
    name: Optional[str] = None
    customer_type: CustomerType = Field(default=CustomerType.UNKNOWN)
    tags: str = Field(default="")  # Comma separated, e.g., "Interested in Wigs, Student, Price Sensitive"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction: datetime = Field(default_factory=datetime.utcnow)

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    total_amount: float
    delivery_address: Optional[str] = None
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    rule_id: int = Field(foreign_key="businessrule.id")
    item_description: str  # What the customer is buying
    quantity: int = Field(default=1)
    unit_price: float
    total_price: float

class BusinessConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_phone: Optional[str] = Field(default=None, unique=True)
    ntfy_topic: Optional[str] = None
    bot_active: bool = Field(default=True)
    business_name: str = Field(default="Auto-Closer Store")
    is_setup_complete: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)