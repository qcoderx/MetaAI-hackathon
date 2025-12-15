from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class CustomerType(str, Enum):
    PRICE_SENSITIVE = "price_sensitive"
    QUALITY_SENSITIVE = "quality_sensitive"
    UNKNOWN = "unknown"

class Strategy(str, Enum):
    PRICE_DROP = "price_drop"
    VALUE_REINFORCEMENT = "value_reinforcement"
    MATCH_OFFER = "match_offer"
    EDUCATE_AND_COUNTER = "educate_and_counter"

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    DELIVERED = "delivered"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"

class DataTier(str, Enum):
    TIER_1_TRUTH = "tier_1_truth"  # Jumia/Konga/Slot
    TIER_2_MARKET = "tier_2_market"  # Verified Jiji/IG
    TIER_3_NOISE = "tier_3_noise"  # Unverified/New Sellers

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    model: str
    current_price: float
    min_negotiable_price: float  # Renamed from floor_price for clarity
    inventory_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CompetitorPrice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    source: str  # "Jiji", "Jumia", "Konga", "Instagram"
    price: float
    url: Optional[str] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    tier: DataTier = Field(default=DataTier.TIER_3_NOISE)
    is_out_of_stock: bool = Field(default=False)
    seller_is_verified: bool = Field(default=False)
    seller_joined_date: Optional[datetime] = None

class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = Field(unique=True, index=True)
    name: Optional[str] = None
    customer_type: CustomerType = Field(default=CustomerType.UNKNOWN)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction: datetime = Field(default_factory=datetime.utcnow)

class CustomerTypeSignal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    signal_text: str
    signal_type: CustomerType
    confidence: float  # 0.0 to 1.0
    detected_at: datetime = Field(default_factory=datetime.utcnow)

class SalesLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    product_id: int = Field(foreign_key="product.id")
    inquiry_date: datetime = Field(default_factory=datetime.utcnow)
    purchased: bool = Field(default=False)
    final_price: Optional[float] = None
    purchase_date: Optional[datetime] = None

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
    product_id: int = Field(foreign_key="product.id")
    quantity: int = Field(default=1)
    unit_price: float
    total_price: float

class BusinessConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_phone: Optional[str] = Field(default=None, unique=True)
    ntfy_topic: Optional[str] = None
    bot_active: bool = Field(default=True)
    business_name: str = Field(default="Naira Sniper")
    is_setup_complete: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PricingDecision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    customer_id: Optional[int] = Field(default=None, foreign_key="customer.id")
    old_price: float
    new_price: float
    strategy: Strategy
    reasoning: str  # Why this decision was made
    market_avg_price: float
    lowest_competitor_price: float
    conversion_probability: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
