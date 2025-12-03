"""Purchase Record Model - Stores individual purchase transactions."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class PurchaseRecord(Base):
    """Model for storing individual purchase records with timestamps.
    
    Critical for pattern analysis - purchase_date timestamp is essential
    for calculating purchase frequency and urgency scores.
    """
    
    __tablename__ = "purchase_records"
    __table_args__ = (
        Index("idx_pr_user_product_date", "user_id", "item_name", "purchase_date"),
        Index("idx_pr_user_date", "user_id", "purchase_date"),
    )
    
    # Primary Key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receipt_id = Column(String(36), ForeignKey("receipts.id"), nullable=True)
    
    # Item Details
    item_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True)  # "Dairy", "Vegetables", etc.
    
    # Quantity Information
    quantity = Column(Float, nullable=True)  # 2.0
    unit = Column(String(50), nullable=True)  # "liters", "kg", "units"
    
    # Price Information
    price = Column(Float, nullable=True)  # 12.50
    currency = Column(String(3), default="BRL")  # Brazilian Real
    
    # CRITICAL: Purchase date for pattern analysis
    purchase_date = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    
    # Source tracking
    source = Column(String(20), nullable=False, default="manual")  # "receipt" or "manual"
    
    # Metadata
    notes = Column(Text, nullable=True)  # Store name, comments, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="purchase_records")
    receipt = relationship("Receipt", back_populates="purchase_records")
    
    def __repr__(self) -> str:
        return f"""<PurchaseRecord(
            id={self.id},
            user_id={self.user_id},
            item_name={self.item_name},
            quantity={self.quantity} {self.unit},
            price={self.price} {self.currency},
            purchase_date={self.purchase_date},
            source={self.source}
        )>"""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "item_name": self.item_name,
            "category": self.category,
            "quantity": self.quantity,
            "unit": self.unit,
            "price": self.price,
            "currency": self.currency,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "source": self.source,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
