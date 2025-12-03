# ARCHITECTURE.md - Technical Implementation Details

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    TELEGRAM BOT (User Interface)               │
│  /predict | /history | /pattern | /analytics | /purchase       │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    HANDLER LAYER                                │
│  prediction_handler │ analytics_handler │ purchase_handler      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    SERVICE LAYER                                │
│  PurchasePredictionService │ PurchaseAnalyticsService           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    DATA ACCESS LAYER                            │
│  SQLAlchemy ORM with AsyncSessionLocal                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    DATABASE LAYER                               │
│  PostgreSQL: purchase_records | product_analytics | preferences │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

### Purchase Recording Flow
```
User Receipt/Manual Entry
    ↓
[Receipt Handler / Purchase Handler]
    ↓
Create PurchaseRecord(item, quantity, price, date)
    ↓
Store in Database
    ↓
Trigger PurchaseAnalyticsService.update_analytics(user_id, product_name)
    ↓
Recalculate ProductAnalytics:
  - avg_days_between_purchases
  - repurchase_urgency
  - repurchase_probability
    ↓
Update ProductAnalytics Record
```

### Prediction Flow
```
User calls /predict
    ↓
[Prediction Handler]
    ↓
PurchasePredictionService.get_predicted_purchases(user_id)
    ↓
Query ProductAnalytics where repurchase_urgency > threshold
    ↓
Sort by urgency (DESC)
    ↓
Format response with emoji indicators
    ↓
Return to User
```

## Core Services

### 1. PurchaseAnalyticsService
**Location:** `app/services/purchase_analytics_service.py`

**Responsibility:** Calculate metrics from raw purchase history

**Key Methods:**
```python
class PurchaseAnalyticsService:
    
    async def update_analytics(user_id: int, product_name: str) -> None:
        """
        Recalculate all metrics for a product after new purchase
        """
        # 1. Get all purchases for this product
        # 2. Calculate avg_days_between
        # 3. Calculate days_since_last
        # 4. Calculate urgency (days_since_last / avg_days) * 100
        # 5. Calculate probability
        # 6. Update ProductAnalytics
    
    async def calculate_purchase_frequency(
        user_id: int, 
        product_name: str
    ) -> float:
        """
        Returns average days between purchases
        Formula: (last_date - first_date) / (count - 1)
        """
        pass
    
    async def calculate_urgency_score(
        user_id: int,
        product_name: str
    ) -> float:
        """
        Returns 0-100+ urgency score
        Formula: (days_since_last / avg_interval) * 100
        """
        pass
```

### 2. PurchasePredictionService
**Location:** `app/services/purchase_prediction_service.py`

**Responsibility:** Generate prediction recommendations for users

**Key Methods:**
```python
class PurchasePredictionService:
    
    async def get_predicted_purchases(
        user_id: int,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Returns items ranked by urgency
        Only includes items with probability >= threshold
        
        Returns:
        [
            {
                'product': 'Milk',
                'urgency': 0.95,
                'confidence': 1.0,
                'emoji': '🔴',
                'message': 'GET MILK NOW (8 days since last purchase)'
            },
            ...
        ]
        """
        pass
    
    async def get_item_prediction(
        user_id: int,
        product_name: str
    ) -> Dict:
        """
        Detailed prediction for specific item
        """
        pass
    
    async def get_shopping_summary(user_id: int) -> Dict:
        """
        Categorized suggestions:
        - urgent (urgency > 0.9)
        - upcoming (0.7 < urgency <= 0.9)
        - optional (urgency <= 0.7)
        """
        pass
```

## Database Schema

### PurchaseRecord Table
```sql
CREATE TABLE purchase_records (
    id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    item_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    quantity FLOAT,
    unit VARCHAR(50),
    price FLOAT,
    currency VARCHAR(3) DEFAULT 'BRL',
    purchase_date TIMESTAMP NOT NULL,  -- CRITICAL INDEX
    source VARCHAR(20),  -- 'receipt' or 'manual'
    receipt_id UUID REFERENCES receipts(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pr_user_product_date 
    ON purchase_records(user_id, item_name, purchase_date DESC);
CREATE INDEX idx_pr_user_date 
    ON purchase_records(user_id, purchase_date DESC);
```

### ProductAnalytics Table
```sql
CREATE TABLE product_analytics (
    id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_name VARCHAR(255) NOT NULL,
    total_purchases INTEGER DEFAULT 0,
    last_purchase_date TIMESTAMP,
    avg_days_between_purchases FLOAT,
    days_since_last_purchase FLOAT,  -- dynamic
    repurchase_urgency FLOAT,  -- 0-100+
    repurchase_probability FLOAT,  -- 0-100
    purchase_frequency_pattern JSONB,  -- {"Mon": 0.1, "Fri": 0.9}
    estimated_next_purchase_date TIMESTAMP,
    min_days_interval FLOAT,
    max_days_interval FLOAT,
    is_seasonal BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_pa_user_product 
    ON product_analytics(user_id, product_name);
CREATE INDEX idx_pa_urgency 
    ON product_analytics(user_id, repurchase_urgency DESC);
```

## Handler Implementation Examples

### PredictionHandler
**Location:** `app/handlers/prediction_handler.py`

```python
async def prediction_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    /predict - Show AI-predicted items user needs
    """
    user_id = update.effective_user.id
    
    async with AsyncSessionLocal() as db:
        predictions = await prediction_service.get_predicted_purchases(
            user_id,
            threshold=0.7
        )
        
        if not predictions:
            await update.message.reply_text(
                "No predictions yet. Add purchases to train the AI."
            )
            return
        
        msg = "🎯 **Your Predictions:**\n\n"
        for pred in predictions:
            msg += f"{pred['emoji']} {pred['product']}\n"
            msg += f"   Urgency: {pred['urgency']:.0%}\n"
            msg += f"   {pred['message']}\n\n"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
```

### PurchaseHandler  
**Location:** `app/handlers/purchase_handler.py`

```python
async def purchase_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    /purchase <item> [quantity] [unit] [price]
    Manual purchase recording
    
    Example: /purchase Milk 2 liters 12.50
    """
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /purchase <item> [qty] [unit] [price]\n"
            "Example: /purchase Milk 2 liters 12.50"
        )
        return
    
    user_id = update.effective_user.id
    
    # Parse arguments
    item_name = context.args[0]
    quantity = float(context.args[1]) if len(context.args) > 1 else None
    unit = context.args[2] if len(context.args) > 2 else None
    price = float(context.args[3]) if len(context.args) > 3 else None
    
    async with AsyncSessionLocal() as db:
        # Create PurchaseRecord
        record = PurchaseRecord(
            user_id=user_id,
            item_name=item_name,
            quantity=quantity,
            unit=unit,
            price=price,
            purchase_date=datetime.now(),
            source="manual"
        )
        db.add(record)
        await db.commit()
        
        # Update analytics
        await analytics_service.update_analytics(user_id, item_name)
        
        await update.message.reply_text(
            f"✅ Recorded: {item_name}\n"
            f"Analytics updated!"
        )
```

## Calculation Examples

### Example 1: Milk Purchase Pattern
```
Purchase History:
- 2025-10-01: 2L milk
- 2025-10-08: 2L milk (7 days)
- 2025-10-15: 2L milk (7 days)
- 2025-10-22: 2L milk (7 days)
- 2025-10-29: 2L milk (7 days)
- 2025-11-05: 2L milk (7 days)
- 2025-11-12: 2L milk (7 days)
- 2025-12-01: 2L milk (19 days - unusual)
- 2025-12-02: (TODAY)

Calculations:
- total_purchases = 8
- avg_days_between = (2025-12-01 - 2025-10-01) / 7 = 61 / 7 = 8.7 days
- last_purchase = 2025-12-01 (1 day ago)
- days_since_last = 1
- urgency_score = (1 / 8.7) * 100 = 11.5%
- probability = 8/8 * 100 = 100%

Recommendation: Low urgency (too recent), but confidence is 100%
```

### Example 2: Wine Purchase Pattern
```
Purchase History:
- 2025-01-15: 1 bottle
- 2025-02-20: 1 bottle (36 days)
- 2025-03-25: 1 bottle (33 days)
- 2025-05-10: 1 bottle (46 days)
- 2025-06-15: 1 bottle (36 days)
- 2025-07-20: 1 bottle (35 days)
- 2025-12-02: (TODAY)

Calculations:
- total_purchases = 6
- avg_days_between = (2025-07-20 - 2025-01-15) / 5 = 186 / 5 = 37.2 days
- last_purchase = 2025-07-20 (135 days ago)
- days_since_last = 135
- urgency_score = (135 / 37.2) * 100 = 363%  ← VERY OVERDUE!
- probability = 6/6 * 100 = 100%  ← Always buys

Recommendation: 🔴 VERY URGENT! (1.5 years worth of cycles)
```

## Testing Strategy

### Unit Tests
- Test analytics calculations
- Test urgency scoring logic
- Test probability calculations

### Integration Tests
- Test purchase recording → analytics update flow
- Test prediction generation
- Test database constraints

### End-to-End Tests
- Simulate user purchases
- Verify predictions improve over time
- Test all commands

## Performance Considerations

1. **Index Strategy:**
   - Always index on (user_id, purchase_date) for range queries
   - Always index on (user_id, product_name) for unique lookups
   - Always index on (user_id, repurchase_urgency DESC) for sorting

2. **Query Optimization:**
   - Use pagination for large result sets
   - Cache ProductAnalytics for 1 hour
   - Update analytics asynchronously via background job

3. **Database Connection:**
   - Use AsyncSessionLocal for async operations
   - Pool size: DATABASE_POOL_SIZE=20
   - Max overflow: DATABASE_MAX_OVERFLOW=10

---

**Reference:** See PROJECT_PLAN.md for full architecture overview
