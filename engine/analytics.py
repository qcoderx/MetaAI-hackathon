from celery import Celery
from sqlmodel import Session, select, func
from app.database import get_session
from app.models import (
    Order, OrderItem, Product, Customer, SalesLog, 
    BusinessConfig, OrderStatus, CompetitorPrice
)
from engine.notifications import NotificationManager
from datetime import datetime, timedelta
from typing import Dict, List
import os

# Celery configuration
celery_app = Celery(
    "naira_sniper_analytics",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

class AnalyticsEngine:
    """Business intelligence and reporting engine"""
    
    def __init__(self):
        self.notification_manager = NotificationManager()
    
    def generate_daily_report(self, session: Session, date: datetime = None) -> Dict:
        """Generate comprehensive daily business report"""
        
        if not date:
            date = datetime.utcnow().date()
        
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())
        
        # Sales metrics
        sales_data = self._calculate_sales_metrics(session, start_of_day, end_of_day)
        
        # Customer metrics
        customer_data = self._calculate_customer_metrics(session, start_of_day, end_of_day)
        
        # Inventory metrics
        inventory_data = self._calculate_inventory_metrics(session)
        
        # Market intelligence
        market_data = self._calculate_market_metrics(session, start_of_day, end_of_day)
        
        return {
            "date": date.isoformat(),
            "sales": sales_data,
            "customers": customer_data,
            "inventory": inventory_data,
            "market": market_data,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _calculate_sales_metrics(self, session: Session, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate sales performance metrics"""
        
        # Total sales
        confirmed_orders = session.exec(
            select(Order)\n            .where(Order.created_at >= start_date)\n            .where(Order.created_at <= end_date)\n            .where(Order.status == OrderStatus.CONFIRMED)\n        ).all()
        
        total_sales = sum(order.total_amount for order in confirmed_orders)
        order_count = len(confirmed_orders)
        
        # Average order value
        avg_order_value = total_sales / order_count if order_count > 0 else 0
        
        # Top selling products
        top_products = session.exec(\n            select(\n                Product.name,\n                func.sum(OrderItem.quantity).label(\"total_sold\"),\n                func.sum(OrderItem.total_price).label(\"total_revenue\")\n            )\n            .join(OrderItem, Product.id == OrderItem.product_id)\n            .join(Order, OrderItem.order_id == Order.id)\n            .where(Order.created_at >= start_date)\n            .where(Order.created_at <= end_date)\n            .where(Order.status == OrderStatus.CONFIRMED)\n            .group_by(Product.id, Product.name)\n            .order_by(func.sum(OrderItem.quantity).desc())\n            .limit(5)\n        ).all()
        
        return {\n            \"total_revenue\": total_sales,\n            \"order_count\": order_count,\n            \"avg_order_value\": avg_order_value,\n            \"top_products\": [\n                {\n                    \"name\": product.name,\n                    \"units_sold\": product.total_sold,\n                    \"revenue\": product.total_revenue\n                }\n                for product in top_products\n            ]\n        }
    
    def _calculate_customer_metrics(self, session: Session, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate customer engagement metrics"""
        
        # New customers
        new_customers = session.exec(\n            select(func.count(Customer.id))\n            .where(Customer.created_at >= start_date)\n            .where(Customer.created_at <= end_date)\n        ).first() or 0
        
        # Active customers (customers who interacted)
        active_customers = session.exec(\n            select(func.count(Customer.id.distinct()))\n            .where(Customer.last_interaction >= start_date)\n            .where(Customer.last_interaction <= end_date)\n        ).first() or 0
        
        # Conversion rate (customers who made orders vs total inquiries)
        total_inquiries = session.exec(\n            select(func.count(SalesLog.id))\n            .where(SalesLog.inquiry_date >= start_date)\n            .where(SalesLog.inquiry_date <= end_date)\n        ).first() or 0
        
        converted_customers = session.exec(\n            select(func.count(Customer.id.distinct()))\n            .join(Order, Customer.id == Order.customer_id)\n            .where(Order.created_at >= start_date)\n            .where(Order.created_at <= end_date)\n            .where(Order.status == OrderStatus.CONFIRMED)\n        ).first() or 0
        
        conversion_rate = (converted_customers / total_inquiries * 100) if total_inquiries > 0 else 0
        
        # Missed opportunities (inquiries without orders)
        missed_opportunities = total_inquiries - converted_customers
        
        return {\n            \"new_customers\": new_customers,\n            \"active_customers\": active_customers,\n            \"total_inquiries\": total_inquiries,\n            \"converted_customers\": converted_customers,\n            \"conversion_rate\": round(conversion_rate, 2),\n            \"missed_opportunities\": missed_opportunities\n        }
    
    def _calculate_inventory_metrics(self, session: Session) -> Dict:
        """Calculate inventory status and alerts"""
        
        # Low stock products (inventory <= 2)
        low_stock_products = session.exec(\n            select(Product)\n            .where(Product.inventory_count <= 2)\n            .where(Product.inventory_count > 0)\n        ).all()
        
        # Out of stock products
        out_of_stock_products = session.exec(\n            select(Product)\n            .where(Product.inventory_count == 0)\n        ).all()
        
        # Total inventory value
        all_products = session.exec(select(Product)).all()
        total_inventory_value = sum(\n            product.current_price * product.inventory_count \n            for product in all_products\n        )
        
        return {\n            \"low_stock_count\": len(low_stock_products),\n            \"low_stock_products\": [\n                {\n                    \"name\": product.name,\n                    \"stock\": product.inventory_count,\n                    \"price\": product.current_price\n                }\n                for product in low_stock_products\n            ],\n            \"out_of_stock_count\": len(out_of_stock_products),\n            \"out_of_stock_products\": [product.name for product in out_of_stock_products],\n            \"total_inventory_value\": total_inventory_value\n        }
    
    def _calculate_market_metrics(self, session: Session, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate market intelligence metrics"""
        
        # Recent competitor price updates
        recent_prices = session.exec(\n            select(CompetitorPrice)\n            .where(CompetitorPrice.scraped_at >= start_date)\n            .where(CompetitorPrice.scraped_at <= end_date)\n            .order_by(CompetitorPrice.scraped_at.desc())\n            .limit(10)\n        ).all()
        
        # Price advantage analysis
        price_advantages = []
        products_with_competitors = session.exec(\n            select(Product.id, Product.name, Product.current_price)\n            .join(CompetitorPrice, Product.id == CompetitorPrice.product_id)\n            .group_by(Product.id, Product.name, Product.current_price)\n        ).all()
        
        for product in products_with_competitors:\n            competitor_prices = session.exec(\n                select(CompetitorPrice.price)\n                .where(CompetitorPrice.product_id == product.id)\n                .where(CompetitorPrice.scraped_at >= start_date - timedelta(days=7))\n            ).all()
            \n            if competitor_prices:\n                avg_competitor_price = sum(competitor_prices) / len(competitor_prices)\n                price_diff = product.current_price - avg_competitor_price\n                price_advantages.append({\n                    \"product\": product.name,\n                    \"our_price\": product.current_price,\n                    \"market_avg\": avg_competitor_price,\n                    \"difference\": price_diff,\n                    \"advantage_percent\": (price_diff / avg_competitor_price * 100) if avg_competitor_price > 0 else 0\n                })
        
        return {\n            \"recent_price_updates\": len(recent_prices),\n            \"price_advantages\": price_advantages[:5],  # Top 5\n            \"market_coverage\": len(products_with_competitors)\n        }
    
    def format_whatsapp_report(self, report_data: Dict) -> str:
        """Format daily report for WhatsApp delivery"""
        
        sales = report_data[\"sales\"]\n        customers = report_data[\"customers\"]\n        inventory = report_data[\"inventory\"]\n        
        message_parts = [\n            f\"📊 DAILY BUSINESS REPORT - {report_data['date']}\",\n            \"\",\n            \"💰 SALES PERFORMANCE:\",\n            f\"Revenue: ₦{sales['total_revenue']:,.0f}\",\n            f\"Orders: {sales['order_count']}\",\n            f\"Avg Order: ₦{sales['avg_order_value']:,.0f}\",\n            \"\",\n            \"👥 CUSTOMER METRICS:\",\n            f\"New Customers: {customers['new_customers']}\",\n            f\"Active Customers: {customers['active_customers']}\",\n            f\"Conversion Rate: {customers['conversion_rate']}%\",\n            f\"Missed Opportunities: {customers['missed_opportunities']}\",\n            \"\",\n            \"📦 INVENTORY STATUS:\",\n            f\"Low Stock Items: {inventory['low_stock_count']}\",\n            f\"Out of Stock: {inventory['out_of_stock_count']}\",\n            f\"Total Value: ₦{inventory['total_inventory_value']:,.0f}\"\n        ]
        
        # Add top selling products\n        if sales[\"top_products\"]:\n            message_parts.extend([\n                \"\",\n                \"🏆 TOP SELLERS:\"\n            ])\n            for i, product in enumerate(sales[\"top_products\"][:3], 1):\n                message_parts.append(\n                    f\"{i}. {product['name']} - {product['units_sold']} sold\"\n                )
        
        # Add low stock alerts\n        if inventory[\"low_stock_products\"]:\n            message_parts.extend([\n                \"\",\n                \"⚠️ RESTOCK NEEDED:\"\n            ])\n            for product in inventory[\"low_stock_products\"][:3]:\n                message_parts.append(\n                    f\"• {product['name']} ({product['stock']} left)\"\n                )
        
        message_parts.extend([\n            \"\",\n            f\"Generated: {datetime.now().strftime('%H:%M')}\",\n            \"Reply 'DETAILS' for full analytics\"\n        ])
        
        return \"\\n\".join(message_parts)

# Celery Tasks
@celery_app.task\ndef generate_and_send_daily_report():\n    \"\"\"Celery task to generate and send daily report at 8 PM\"\"\"\n    try:\n        session = next(get_session())\n        analytics = AnalyticsEngine()\n        \n        # Generate report\n        report_data = analytics.generate_daily_report(session)\n        \n        # Format for WhatsApp\n        whatsapp_message = analytics.format_whatsapp_report(report_data)\n        \n        # Get business config\n        business_config = session.exec(select(BusinessConfig)).first()\n        if not business_config or not business_config.owner_phone:\n            print(\"No business config found or owner not registered\")\n            return False\n        \n        # Send report to owner\n        result = analytics.notification_manager.whatsapp.send_message(\n            business_config.owner_phone,\n            whatsapp_message\n        )\n        \n        session.close()\n        return result.get(\"success\", False)\n        \n    except Exception as e:\n        print(f\"Daily report task failed: {e}\")\n        return False

@celery_app.task\ndef check_low_stock_alerts():\n    \"\"\"Celery task to check and send low stock alerts\"\"\"\n    try:\n        session = next(get_session())\n        analytics = AnalyticsEngine()\n        \n        # Get low stock products\n        low_stock_products = session.exec(\n            select(Product)\n            .where(Product.inventory_count <= 2)\n            .where(Product.inventory_count > 0)\n        ).all()\n        \n        # Send alerts for each low stock product\n        alerts_sent = 0\n        for product in low_stock_products:\n            result = analytics.notification_manager.send_low_stock_alert(\n                session, product.id\n            )\n            if result.get(\"success\"):\n                alerts_sent += 1\n        \n        session.close()\n        return alerts_sent\n        \n    except Exception as e:\n        print(f\"Low stock alert task failed: {e}\")\n        return 0

@celery_app.task\ndef retarget_ghost_customers():\n    \"\"\"Celery task to retarget customers who didn't convert\"\"\"\n    try:\n        session = next(get_session())\n        analytics = AnalyticsEngine()\n        \n        # Find customers with inquiries but no orders in last 7 days\n        cutoff_date = datetime.utcnow() - timedelta(days=7)\n        \n        ghost_customers = session.exec(\n            select(Customer.phone, SalesLog.product_id)\n            .join(SalesLog, Customer.id == SalesLog.customer_id)\n            .where(SalesLog.inquiry_date >= cutoff_date)\n            .where(SalesLog.purchased == False)\n            .where(~Customer.id.in_(\n                select(Order.customer_id)\n                .where(Order.created_at >= cutoff_date)\n            ))\n            .limit(10)  # Limit to avoid spam\n        ).all()\n        \n        # Send retargeting messages\n        messages_sent = 0\n        for customer_phone, product_id in ghost_customers:\n            result = analytics.notification_manager.send_customer_retarget_message(\n                session, customer_phone, product_id\n            )\n            if result.get(\"success\"):\n                messages_sent += 1\n        \n        session.close()\n        return messages_sent\n        \n    except Exception as e:\n        print(f\"Retargeting task failed: {e}\")\n        return 0

# Celery Beat Schedule (add to main.py or separate scheduler)\ncelery_app.conf.beat_schedule = {\n    'daily-report': {\n        'task': 'engine.analytics.generate_and_send_daily_report',\n        'schedule': 20.0 * 60 * 60,  # 8 PM (20:00)\n    },\n    'low-stock-check': {\n        'task': 'engine.analytics.check_low_stock_alerts',\n        'schedule': 60.0 * 60,  # Every hour\n    },\n    'retarget-customers': {\n        'task': 'engine.analytics.retarget_ghost_customers',\n        'schedule': 24.0 * 60 * 60,  # Daily\n    },\n}\n\ncelery_app.conf.timezone = 'Africa/Lagos'