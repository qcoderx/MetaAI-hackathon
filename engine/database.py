"""
NAIRA SNIPER - DATABASE
SQLite database for storing prices
"""
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import os

class ProductPrice(SQLModel, table=True):
    __tablename__ = "product_prices"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    product_name: str = Field(index=True)
    source: str = Field(index=True)
    title: str
    price: float = Field(index=True)
    url: Optional[str] = None
    rating: Optional[str] = None
    location: Optional[str] = None
    scraped_at: datetime = Field(default_factory=datetime.now, index=True)


class PriceDatabase:
    """Database manager"""
    
    def __init__(self, db_url: str = None):
        if not db_url:
            # Store DB in engine/data folder
            os.makedirs('engine/data', exist_ok=True)
            db_url = "sqlite:///./engine/data/prices.db"
        
        self.engine = create_engine(db_url)
        
        # Create tables
        SQLModel.metadata.create_all(self.engine)
        print(f"✅ Database initialized: {db_url}")
    
    def save_prices(self, product_name: str, results: Dict[str, List[Dict]]):
        """Save scraped prices to database"""
        with Session(self.engine) as session:
            total_saved = 0
            
            for source, items in results.items():
                if not items:
                    continue
                
                for item in items:
                    if not item.get('price'):
                        continue
                    
                    # Check for duplicates
                    existing = session.exec(
                        select(ProductPrice).where(
                            ProductPrice.product_name == product_name,
                            ProductPrice.source == source,
                            ProductPrice.title == item.get('name', '')[:100],
                            ProductPrice.price == item['price']
                        ).limit(1)
                    ).first()
                    
                    if not existing:
                        price_record = ProductPrice(
                            product_name=product_name,
                            source=source,
                            title=item.get('name', 'Unknown')[:200],
                            price=item['price'],
                            url=item.get('url'),
                            rating=item.get('rating'),
                            location=item.get('location'),
                        )
                        session.add(price_record)
                        total_saved += 1
            
            session.commit()
            print(f"💾 Saved {total_saved} new prices to database")
            return total_saved
    
    def get_latest_prices(self, product_name: str = None, source: str = None, limit: int = 50):
        """Get latest prices from database"""
        with Session(self.engine) as session:
            query = select(ProductPrice)
            
            if product_name:
                query = query.where(ProductPrice.product_name == product_name)
            if source:
                query = query.where(ProductPrice.source == source)
            
            query = query.order_by(ProductPrice.scraped_at.desc()).limit(limit)
            
            results = session.exec(query).all()
            return results
    
    def get_price_stats(self, product_name: str):
        """Get price statistics for a product"""
        with Session(self.engine) as session:
            from sqlalchemy.sql import func
            
            stats = session.exec(
                select(
                    ProductPrice.source,
                    func.count(ProductPrice.id).label('count'),
                    func.avg(ProductPrice.price).label('avg_price'),
                    func.min(ProductPrice.price).label('min_price'),
                    func.max(ProductPrice.price).label('max_price')
                ).where(
                    ProductPrice.product_name == product_name
                ).group_by(
                    ProductPrice.source
                )
            ).all()
            
            return stats
    
    def cleanup_old_data(self, days: int = 7):
        """Remove data older than X days"""
        with Session(self.engine) as session:
            from sqlalchemy import delete
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            stmt = delete(ProductPrice).where(
                ProductPrice.scraped_at < cutoff
            )
            
            result = session.exec(stmt)
            session.commit()
            
            print(f"🧹 Cleaned up {result.rowcount} old records")
            return result.rowcount