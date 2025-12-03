"""Purchase Prediction Service - Makes shopping predictions based on analytics."""

import logging
from typing import Optional, List, Dict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product_analytics import ProductAnalytics
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class PurchasePredictionService:
    """Service for generating purchase predictions based on ProductAnalytics.
    
    This service:
    1. Queries ProductAnalytics records
    2. Ranks items by urgency
    3. Generates prediction messages
    4. Returns recommendations grouped by urgency levels
    """
    
    @staticmethod
    async def get_predicted_purchases(
        user_id: int,
        urgency_threshold: float = 0.0,
        limit: int = 10,
        session: Session = None
    ) -> List[Dict]:
        """Get predicted items ranked by repurchase urgency.
        
        Returns items the user likely needs soon, sorted by urgency score.
        Only includes items with urgency >= threshold.
        
        Args:
            user_id: User ID
            urgency_threshold: Minimum urgency score (0-100) to include
            limit: Maximum items to return
            session: Database session
        
        Returns:
            List of dicts with item predictions
        """
        if session is None:
            async with AsyncSessionLocal() as session:
                return await PurchasePredictionService.get_predicted_purchases(
                    user_id, urgency_threshold, limit, session
                )
        
        try:
            logger.info(f"Getting predictions for user {user_id}")
            
            # Query analytics ordered by urgency
            stmt = select(ProductAnalytics).where(
                ProductAnalytics.user_id == user_id,
                ProductAnalytics.repurchase_urgency >= urgency_threshold,
                ProductAnalytics.repurchase_probability > 0  # Only items with purchase history
            ).order_by(
                ProductAnalytics.repurchase_urgency.desc()
            ).limit(limit)
            
            result = await session.execute(stmt)
            analytics_list = result.scalars().all()
            
            predictions = []
            for analytics in analytics_list:
                prediction = {
                    "product_name": analytics.product_name,
                    "urgency": analytics.repurchase_urgency,
                    "confidence": analytics.repurchase_probability,
                    "days_since_last": int(analytics.days_since_last_purchase or 0),
                    "avg_interval": int(analytics.avg_days_between_purchases or 0),
                    "status": analytics.get_urgency_status(),
                    "message": analytics.get_prediction_message(),
                    "last_purchase": analytics.last_purchase_date.isoformat() if analytics.last_purchase_date else None,
                    "estimated_next": analytics.estimated_next_purchase_date.isoformat() if analytics.estimated_next_purchase_date else None,
                }
                predictions.append(prediction)
            
            logger.info(f"Found {len(predictions)} predictions")
            return predictions
            
        except Exception as e:
            logger.error(f"Error getting predictions: {e}")
            return []
    
    @staticmethod
    async def get_shopping_summary(
        user_id: int,
        session: Session = None
    ) -> Dict:
        """Get grouped shopping summary (urgent/upcoming/optional).
        
        Returns:
            Dict with 'urgent', 'upcoming', 'optional' lists
        """
        if session is None:
            async with AsyncSessionLocal() as session:
                return await PurchasePredictionService.get_shopping_summary(
                    user_id, session
                )
        
        try:
            logger.info(f"Getting shopping summary for user {user_id}")
            
            # Get all predictions
            predictions = await PurchasePredictionService.get_predicted_purchases(
                user_id, 0.0, 999, session
            )
            
            # Categorize by urgency
            urgent = [p for p in predictions if p["urgency"] >= 90]
            upcoming = [p for p in predictions if 70 <= p["urgency"] < 90]
            optional = [p for p in predictions if p["urgency"] < 70]
            
            return {
                "urgent": urgent,
                "upcoming": upcoming,
                "optional": optional,
                "total": len(predictions),
                "summary": f"You need to shop soon! {len(urgent)} urgent items, {len(upcoming)} upcoming."
            }
            
        except Exception as e:
            logger.error(f"Error getting shopping summary: {e}")
            return {"urgent": [], "upcoming": [], "optional": [], "total": 0}
    
    @staticmethod
    async def get_item_prediction(
        user_id: int,
        product_name: str,
        session: Session = None
    ) -> Optional[Dict]:
        """Get detailed prediction for specific product.
        
        Returns:
            Detailed prediction dict or None if not found
        """
        if session is None:
            async with AsyncSessionLocal() as session:
                return await PurchasePredictionService.get_item_prediction(
                    user_id, product_name, session
                )
        
        try:
            stmt = select(ProductAnalytics).where(
                ProductAnalytics.user_id == user_id,
                ProductAnalytics.product_name == product_name
            )
            
            result = await session.execute(stmt)
            analytics = result.scalars().first()
            
            if not analytics:
                logger.warning(f"No analytics for {product_name}")
                return None
            
            return {
                "product_name": analytics.product_name,
                "total_purchases": analytics.total_purchases,
                "last_purchase_date": analytics.last_purchase_date.isoformat() if analytics.last_purchase_date else None,
                "avg_interval_days": analytics.avg_days_between_purchases,
                "days_since_last": analytics.days_since_last_purchase,
                "min_interval": analytics.min_days_interval,
                "max_interval": analytics.max_days_interval,
                "urgency_score": analytics.repurchase_urgency,
                "confidence": analytics.repurchase_probability,
                "is_seasonal": analytics.is_seasonal,
                "next_purchase_estimate": analytics.estimated_next_purchase_date.isoformat() if analytics.estimated_next_purchase_date else None,
                "status": analytics.get_urgency_status(),
                "recommendation": analytics.get_prediction_message(),
            }
            
        except Exception as e:
            logger.error(f"Error getting item prediction: {e}")
            return None


# Singleton instance
purchase_prediction_service = PurchasePredictionService()
