"""Product Analytics Model - Stores calculated metrics for purchases."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class ProductAnalytics(Base):
    """Model for storing calculated purchase analytics per product per user.
    
    This model stores pre-calculated metrics to optimize query performance
    for predictions. It's updated whenever a new PurchaseRecord is added.
    """
    
    __tablename__ = "product_analytics"
    __table_args__ = (
        UniqueConstraint("user_id", "product_name", name="uq_user_product"),
        Index("idx_pa_user_product", "user_id", "product_name"),
        Index("idx_pa_urgency", "user_id", "repurchase_urgency"),
    )
    
    # Primary Key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Product Identity
    product_name = Column(String(255), nullable=False, index=True)
    
    # Purchase Statistics
    total_purchases = Column(Integer, default=0)  # Lifetime purchase count
    last_purchase_date = Column(DateTime, nullable=True)  # Most recent purchase
    
    # Frequency Metrics
    avg_days_between_purchases = Column(Float, nullable=True)  # Average interval
    days_since_last_purchase = Column(Float, nullable=True)  # Dynamic calculation
    min_days_interval = Column(Float, nullable=True)  # Shortest gap seen
    max_days_interval = Column(Float, nullable=True)  # Longest gap seen
    
    # Prediction Scores (0-100 scale)
    repurchase_urgency = Column(Float, default=0.0)  # 0-100+ (over 100% = overdue)
    repurchase_probability = Column(Float, default=0.0)  # 0-100 confidence
    
    # Pattern Detection
    purchase_frequency_pattern = Column(JSON, nullable=True)  # {"Mon": 0.1, "Fri": 0.9}
    is_seasonal = Column(Boolean, default=False)  # Detected seasonal variation
    
    # Predictions
    estimated_next_purchase_date = Column(DateTime, nullable=True)  # Predicted date
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_analyzed_at = Column(DateTime, nullable=True)  # Last time metrics were recalculated
    
    # Relationships
    user = relationship("User", back_populates="product_analytics")
    
    def __repr__(self) -> str:
        return f"""<ProductAnalytics(
            id={self.id},
            user_id={self.user_id},
            product_name={self.product_name},
            total_purchases={self.total_purchases},
            avg_days={self.avg_days_between_purchases},
            urgency={self.repurchase_urgency:.1f}%,
            probability={self.repurchase_probability:.1f}%
        )>"""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_name": self.product_name,
            "total_purchases": self.total_purchases,
            "last_purchase_date": self.last_purchase_date.isoformat() if self.last_purchase_date else None,
            "avg_days_between_purchases": self.avg_days_between_purchases,
            "days_since_last_purchase": self.days_since_last_purchase,
            "min_days_interval": self.min_days_interval,
            "max_days_interval": self.max_days_interval,
            "repurchase_urgency": self.repurchase_urgency,
            "repurchase_probability": self.repurchase_probability,
            "purchase_frequency_pattern": self.purchase_frequency_pattern,
            "is_seasonal": self.is_seasonal,
            "estimated_next_purchase_date": self.estimated_next_purchase_date.isoformat() if self.estimated_next_purchase_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def get_urgency_status(self) -> str:
        """Return human-readable urgency status."""
        if self.repurchase_urgency >= 100:
            return "🔴 OVERDUE"
        elif self.repurchase_urgency >= 85:
            return "🟠 URGENT"
        elif self.repurchase_urgency >= 70:
            return "🟡 SOON"
        elif self.repurchase_urgency >= 50:
            return "🟢 UPCOMING"
        else:
            return "⚪ OPTIONAL"
    
    def get_prediction_message(self) -> str:
        """Generate human-readable prediction message."""
        if self.avg_days_between_purchases and self.days_since_last_purchase:
            return f"You usually buy {self.product_name} every {self.avg_days_between_purchases:.0f} days. Last purchase: {self.days_since_last_purchase:.0f} days ago."
        return f"Not enough data for {self.product_name} predictions yet."
