from brain.llama_client import LlamaClient
from brain.prompts import ARBITRAGE_ANALYST_PROMPT
from brain.predictive import PredictiveEngine
from app.models import (
    Product, Customer, CustomerType, Strategy, 
    PricingDecision, CompetitorPrice, DataTier
)
from sqlmodel import Session, select, func
from typing import Dict, Optional, List
from datetime import datetime
import random
import string

class PricingAgent:
    """The Arbitrage Engine: Tiered Intelligence & Real-Time Fact Checking"""
    
    def __init__(self):
        self.llama = LlamaClient()
        self.predictor = PredictiveEngine()
    
    def get_tiered_market_data(self, session: Session, product_id: int) -> Dict:
        """Get tiered market intelligence with surge detection"""
        prices = session.exec(
            select(CompetitorPrice)
            .where(CompetitorPrice.product_id == product_id)
        ).all()
        
        if not prices:
            return {"surge_mode": False, "trusted_competitors": [], "noise_competitors": [], "market_price": 0}
        
        # Separate by tiers
        tier1_prices = [p for p in prices if p.tier == DataTier.TIER_1_TRUTH]
        tier2_prices = [p for p in prices if p.tier == DataTier.TIER_2_MARKET]
        tier3_prices = [p for p in prices if p.tier == DataTier.TIER_3_NOISE]
        
        # Check surge mode - FIXED: Handle scraper failures
        # If no tier1 data AND no recent scraping activity, assume surge
        if len(tier1_prices) == 0:
            # Check if we have ANY recent price data (last 6 hours)
            from datetime import timedelta
            recent_cutoff = datetime.utcnow() - timedelta(hours=6)
            recent_prices = [p for p in prices if p.scraped_at > recent_cutoff]
            # If no recent data, assume scrapers are blocked = potential surge
            surge_mode = len(recent_prices) == 0
        else:
            # Normal logic: all tier1 out of stock
            surge_mode = all(p.is_out_of_stock for p in tier1_prices)
        
        # Calculate market price
        market_price = 0
        if tier1_prices:
            tier1_available = [p.price for p in tier1_prices if not p.is_out_of_stock]
            if tier1_available:
                market_price = sum(tier1_available) / len(tier1_available)
            elif surge_mode:
                # Use last known Tier 1 prices + 10% surge
                tier1_all = [p.price for p in tier1_prices]
                market_price = (sum(tier1_all) / len(tier1_all)) * 1.1
        elif tier2_prices:
            tier2_available = [p.price for p in tier2_prices]
            market_price = sum(tier2_available) / len(tier2_available)
        
        return {
            "surge_mode": surge_mode,
            "trusted_competitors": [(p.price, p.url, p.source) for p in tier1_prices + tier2_prices],
            "noise_competitors": [(p.price, p.url, p.source, p.seller_joined_date) for p in tier3_prices],
            "market_price": market_price
        }
    
    def make_pricing_decision(
        self,
        session: Session,
        product: Product,
        customer: Optional[Customer] = None,
        customer_claim: Optional[str] = None
    ) -> Dict:
        """
        Arbitrage Engine decision-making logic
        Returns: {strategy, price, reasoning, message_angle, conversion_prob, flash_code}
        """
        market_intel = self.get_tiered_market_data(session, product.id)
        
        customer_type = customer.customer_type if customer else CustomerType.UNKNOWN
        
        # Build arbitrage context for Llama 3 - NO FLOOR PRICE
        prompt = ARBITRAGE_ANALYST_PROMPT.format(
            product_name=product.name,
            current_price=product.current_price,
            floor_price="CONFIDENTIAL",  # Don't expose real floor price
            market_price=market_intel["market_price"],
            surge_mode=market_intel["surge_mode"],
            trusted_competitors=str(market_intel["trusted_competitors"][:3]),
            noise_competitors=str(market_intel["noise_competitors"][:3]),
            customer_type=customer_type.value,
            customer_claim=customer_claim or "No specific claim"
        )
        
        # Get AI recommendation
        ai_decision = self.llama.generate_json(prompt)
        
        if not ai_decision:
            ai_decision = self._fallback_arbitrage_decision(product, market_intel, customer_type)
        
        # Validate floor price constraint
        recommended_price = ai_decision.get("recommended_price", product.current_price)
        if recommended_price < product.min_negotiable_price:
            recommended_price = product.min_negotiable_price
            ai_decision["reasoning"] += " (Floor price enforced)"
        
        # Generate flash liquidity code if offering discount
        flash_code = None
        if recommended_price < product.current_price:
            flash_code = "PAY-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Calculate conversion probability
        customer_type_score = 0.0 if customer_type == CustomerType.PRICE_SENSITIVE else 1.0
        conversion_prob = self.predictor.calculate_heuristic_probability(
            current_price=product.current_price,
            new_price=recommended_price,
            market_avg=market_intel["market_price"],
            customer_type_score=customer_type_score
        )
        
        # Log decision
        decision_log = PricingDecision(
            product_id=product.id,
            customer_id=customer.id if customer else None,
            old_price=product.current_price,
            new_price=recommended_price,
            strategy=Strategy(ai_decision["strategy"]),
            reasoning=ai_decision["reasoning"],
            market_avg_price=market_intel["market_price"],
            lowest_competitor_price=min([p[0] for p in market_intel["trusted_competitors"]], default=0),
            conversion_probability=conversion_prob
        )
        session.add(decision_log)
        session.commit()
        
        return {
            "strategy": ai_decision["strategy"],
            "recommended_price": recommended_price,
            "reasoning": ai_decision["reasoning"],
            "message_angle": ai_decision.get("message_angle", ""),
            "conversion_probability": conversion_prob,
            "flash_code": flash_code,
            "surge_mode": market_intel["surge_mode"],
            "market_intel": market_intel
        }
    
    def _fallback_arbitrage_decision(
        self,
        product: Product,
        market_intel: Dict,
        customer_type: CustomerType
    ) -> Dict:
        """Rule-based arbitrage fallback when AI is unavailable"""
        if market_intel["surge_mode"]:
            return {
                "strategy": "value_reinforcement",
                "recommended_price": product.current_price,
                "reasoning": "Surge mode active - major retailers out of stock. Price firm.",
                "message_angle": "Supply is scarce, price is firm"
            }
        
        market_price = market_intel["market_price"]
        if market_price and market_price < product.current_price:
            target_price = max(market_price - 500, product.min_negotiable_price)
            return {
                "strategy": "match_offer",
                "recommended_price": target_price,
                "reasoning": f"Matching market at ₦{target_price}",
                "message_angle": "Market-matched price with added value"
            }
        
        return {
            "strategy": "value_reinforcement",
            "recommended_price": product.current_price,
            "reasoning": "Maintaining premium positioning",
            "message_angle": "Premium quality with warranty"
        }
    
    def should_retarget_customer(
        self,
        session: Session,
        customer_id: int,
        product_id: int,
        days_since_inquiry: int = 7
    ) -> bool:
        """Check if customer should be retargeted"""
        from app.models import SalesLog
        from datetime import timedelta
        
        # Find recent inquiries without purchase
        cutoff_date = datetime.utcnow() - timedelta(days=days_since_inquiry)
        
        inquiry = session.exec(
            select(SalesLog)
            .where(SalesLog.customer_id == customer_id)
            .where(SalesLog.product_id == product_id)
            .where(SalesLog.inquiry_date > cutoff_date)
            .where(SalesLog.purchased == False)
        ).first()
        
        return inquiry is not None
