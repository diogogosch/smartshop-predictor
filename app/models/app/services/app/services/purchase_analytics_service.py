"""Purchase Analytics Service - Calculates purchase patterns and metrics."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.purchase_record import PurchaseRecord
from app.models.product_analytics import ProductAnalytics
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class PurchaseAnalyticsService:
    """Service for calculating purchase analytics and patterns.
    
    This service:
    1. Analyzes purchase history
    2. Calculates repurchase urgency scores
    3. Calculates repurchase probability
    4. Detects purchase patterns
    5. Updates ProductAnalytics records
    """
    
    @staticmethod
    async def update_analytics(
        user_id: int,
        product_name: str,
        session: Session = None
    ) -> Optional[ProductAnalytics]:
        """Update analytics for a product after new purchase.
        
        This is the main method called when a new PurchaseRecord is created.
        It recalculates all metrics and updates ProductAnalytics.
        """
        if session is None:
            async with AsyncSessionLocal() as session:
                return await PurchaseAnalyticsService.update_analytics(
                    user_id, product_name, session
                )
        
        try:
            logger.info(f"Updating analytics for user {user_id}, product: {product_name}")
            
            # Get all purchases for this product
            stmt = select(PurchaseRecord).where(
                PurchaseRecord.user_id == user_id,
                PurchaseRecord.item_name == product_name
            ).order_by(PurchaseRecord.purchase_date.asc())
            
            result = await session.execute(stmt)
            purchases = result.scalars().all()
            
            if not purchases:
                logger.warning(f"No purchases found for {product_name}")
                return None
            
            # Calculate metrics
            total_purchases = len(purchases)
            last_purchase_date = purchases[-1].purchase_date
            first_purchase_date = purchases[0].purchase_date
            
            # Calculate average days between purchases
            if total_purchases > 1:
                days_diff = (last_purchase_date - first_purchase_date).days
                avg_days = days_diff / (total_purchases - 1)
            else:
                avg_days = None
            
            # Calculate days since last purchase
            days_since_last = (datetime.utcnow() - last_purchase_date).days
            
            # Calculate purchase intervals
            intervals = []
            for i in range(1, len(purchases)):
                interval = (purchases[i].purchase_date - purchases[i-1].purchase_date).days
                intervals.append(interval)
            
            min_interval = min(intervals) if intervals else None
            max_interval = max(intervals) if intervals else None
            
            # Calculate urgency score (days_since_last / avg_days) * 100
            if avg_days and avg_days > 0:
                urgency_score = (days_since_last / avg_days) * 100
            else:
                urgency_score = 0.0
            
            # Calculate repurchase probability
            # (times bought in receipts / total distinct receipt dates)
            stmt_all_purchases = select(func.count(func.distinct(
                PurchaseRecord.purchase_date
            ))).where(PurchaseRecord.user_id == user_id)
            
            result_all = await session.execute(stmt_all_purchases)
            total_purchase_dates = result_all.scalar() or 1
            
            repurchase_probability = (total_purchases / total_purchase_dates) * 100
            
            # Estimate next purchase date
            if avg_days:
                estimated_next = last_purchase_date + timedelta(days=avg_days)
            else:
                estimated_next = None
            
            # Get or create ProductAnalytics record
            stmt_analytics = select(ProductAnalytics).where(
                ProductAnalytics.user_id == user_id,
                ProductAnalytics.product_name == product_name
            )
            result_analytics = await session.execute(stmt_analytics)
            analytics = result_analytics.scalars().first()
            
            if not analytics:
                analytics = ProductAnalytics(
                    user_id=user_id,
                    product_name=product_name
                )
                session.add(analytics)
            
            # Update analytics record
            analytics.total_purchases = total_purchases
            analytics.last_purchase_date = last_purchase_date
            analytics.avg_days_between_purchases = avg_days
            analytics.days_since_last_purchase = float(days_since_last)
            analytics.min_days_interval = float(min_interval) if min_interval else None
            analytics.max_days_interval = float(max_interval) if max_interval else None
            analytics.repurchase_urgency = urgency_score
            analytics.repurchase_probability = repurchase_probability
            analytics.estimated_next_purchase_date = estimated_next
            analytics.last_analyzed_at = datetime.utcnow()
            
            await session.commit()
            logger.info(f"Analytics updated: urgency={urgency_score:.1f}%, probability={repurchase_probability:.1f}%")
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
            await session.rollback()
            return None
    
    @staticmethod
    async def get_user_analytics(
        user_id: int,
        session: Session = None,
        urgency_threshold: float = 0.0
    ) -> List[ProductAnalytics]:
        """Get all analytics for a user, optionally filtered by urgency threshold."""
        if session is None:
            async with AsyncSessionLocal() as session:
                return await PurchaseAnalyticsService.get_user_analytics(
                    user_id, session, urgency_threshold
                )
        
        try:
            stmt = select(ProductAnalytics).where(
                ProductAnalytics.user_id == user_id,
                ProductAnalytics.repurchase_urgency >= urgency_threshold
            ).order_by(ProductAnalytics.repurchase_urgency.desc())
            
            result = await session.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return []
    
    @staticmethod
    async def get_product_analytics(
        user_id: int,
        product_name: str,
        session: Session = None
    ) -> Optional[ProductAnalytics]:
        """Get analytics for specific product."""
        if session is None:
            async with AsyncSessionLocal() as session:
                return await PurchaseAnalyticsService.get_product_analytics(
                    user_id, product_name, session
                )
        
        try:
            stmt = select(ProductAnalytics).where(
                ProductAnalytics.user_id == user_id,
                ProductAnalytics.product_name == product_name
            )
            
            result = await session.execute(stmt)
            return result.scalars().first()
            
        except Exception as e:
            logger.error(f"Error getting product analytics: {e}")
            return None


# Singleton instance
purchase_analytics_service = PurchaseAnalyticsService()
