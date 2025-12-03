# SmartShop Predictor - Comprehensive Project Plan

## Vision
Transform SmartShop from a simple shopping list manager into an intelligent **predictive shopping assistant** that learns from user purchase history and predicts when items will be needed, enabling proactive shopping suggestions.

## Core Problem Solved

**Old Design (Wrong):**
- User manually creates shopping list
- AI suggests complementary items (static recommendations)
- No learning from past purchases
- Users still need to remember when to rebuy

**New Design (Correct):**
- User records all purchases (via receipt OCR or manual entry)
- System learns purchase patterns and frequency
- AI predicts when items need repurchasing
- Bot proactively suggests: "You usually buy milk every 7 days. Last purchase: 6 days ago → GET MILK NOW"

## Project Phases

### Phase 1: Data Model Architecture
**Objective:** Build foundation for purchase history tracking and analytics

**Models to Create:**

1. **PurchaseRecord** (app/models/purchase_record.py)
   - `id` (UUID)
   - `user_id` (FK to User)
   - `item_name` (str) - e.g., "Milk"
   - `category` (str) - e.g., "Dairy" (inferred or manual)
   - `quantity` (float)
   - `unit` (str) - e.g., "liters", "kg"
   - `price` (float)
   - `currency` (str) - e.g., "BRL"
   - `purchase_date` (datetime) - critical for pattern analysis
   - `source` (str) - "receipt" or "manual"
   - `receipt_id` (FK to Receipt, nullable)
   - `created_at` (datetime)
   - `updated_at` (datetime)

2. **ProductAnalytics** (app/models/product_analytics.py)
   - `id` (UUID)
   - `user_id` (FK to User)
   - `product_name` (str)
   - `total_purchases` (int) - lifetime count
   - `last_purchase_date` (datetime)
   - `avg_days_between_purchases` (float) - calculated from history
   - `days_since_last_purchase` (float) - dynamic
   - `repurchase_urgency` (float) - 0-100 score
   - `repurchase_probability` (float) - 0-100 confidence
   - `purchase_frequency_pattern` (JSON) - weekly/monthly breakdowns
   - `estimated_next_purchase_date` (datetime)
   - `min_days_interval` (float) - shortest gap
   - `max_days_interval` (float) - longest gap
   - `is_seasonal` (bool) - detected seasonal purchase?
   - `created_at` (datetime)
   - `updated_at` (datetime)

3. **ShoppingPreference** (app/models/shopping_preference.py)
   - `id` (UUID)
   - `user_id` (FK to User)
   - `category` (str) - e.g., "Dairy", "Vegetables", "Wine"
   - `avg_spend_per_category` (float)
   - `preferred_days` (JSON) - e.g., {"Monday": 0.8, "Friday": 0.9}
   - `notification_threshold` (float) - e.g., alert at 85% of avg interval
   - `created_at` (datetime)
   - `updated_at` (datetime)

**Database Schema:**
- Ensure proper indexing on `user_id`, `product_name`, `purchase_date`
- Add indexes on `last_purchase_date`, `repurchase_urgency`

---

### Phase 2: Enhanced Receipt Processing
**Objective:** Automatically populate PurchaseRecord from receipts and manual entries

**Components:**

1. **Receipt Handler Enhancement** (app/handlers/receipt_handler.py)
   - Process receipt OCR results
   - For each extracted item:
     - Create PurchaseRecord entry
     - Link to Receipt model
     - Store timestamp
   - Trigger ProductAnalytics update
   - Store receipt metadata (store name, total, date)

2. **Purchase Recording Handler** (app/handlers/purchase_handler.py - NEW)
   - Command: `/purchase <item> <quantity> <unit> <price>`
   - Manual purchase entry for non-receipt items
   - Example: `/purchase Milk 2 liters 12.50`
   - Creates PurchaseRecord with source="manual"

3. **Bulk Import Handler** (app/handlers/import_handler.py - NEW)
   - Command: `/import` with file upload
   - Accept CSV format: item_name,quantity,price,date
   - Batch create PurchaseRecords
   - Useful for historical data migration

---

### Phase 3: Analytics & Pattern Recognition Engine
**Objective:** Calculate purchase patterns from historical data

**Services:**

1. **PurchaseAnalyticsService** (app/services/purchase_analytics_service.py - NEW)
   ```
   Methods:
   - analyze_user_purchases(user_id) → ProductAnalytics[]
   - calculate_purchase_frequency(product_name, user_id) → float
   - detect_seasonal_patterns(product_name, user_id) → bool
   - get_purchase_intervals(product_name, user_id) → [int]
   - calculate_repurchase_urgency(product_name, user_id) → float
   ```

2. **Logic - Repurchase Urgency Calculation:**
   ```
   avg_days_interval = avg(days between purchases)
   days_since_last = today - last_purchase_date
   urgency_score = (days_since_last / avg_days_interval) * 100
   
   Examples:
   - Milk: avg=7 days, last=6 days ago → score=85% (good, remind soon)
   - Milk: avg=7 days, last=8 days ago → score=114% (OVERDUE!)
   - Wine: avg=30 days, last=15 days ago → score=50% (low urgency)
   ```

3. **Logic - Repurchase Probability:**
   ```
   probability = (total_purchases / total_receipts) * 100
   
   Examples:
   - Milk: 52 purchases in 52 receipts → 100% (always bought)
   - Eggs: 48 purchases in 52 receipts → 92% (usually bought)
   - Wine: 15 purchases in 52 receipts → 29% (occasional)
   ```

4. **Logic - Category Analytics:**
   - Group purchases by category (inferred from item name or ML)
   - Track spending trends per category
   - Identify peak shopping days

---

### Phase 4: AI Prediction Service
**Objective:** Replace generic suggestions with predictive intelligence

**Service:** PurchasePredictionService (app/services/purchase_prediction_service.py - NEW)

```python
class PurchasePredictionService:
    
    async def get_predicted_purchases(user_id, threshold=0.7):
        """
        Returns items user is likely to need SOON, ranked by urgency
        Only includes items with repurchase_probability >= threshold
        Sorted by urgency_score descending
        """
        → [{"item": "Milk", "urgency": 0.95, "confidence": 1.0, "days_since": 8, "avg_interval": 7}]
    
    async def get_item_prediction(user_id, product_name):
        """
        Detailed prediction for specific product
        """
        → {
            "product": "Milk",
            "last_purchase": "2025-12-02",
            "avg_interval_days": 7,
            "purchase_history": [7, 7, 8, 6, 7, 7],
            "next_predicted_date": "2025-12-09",
            "urgency_score": 95,
            "confidence": 100,
            "seasonal_factor": 1.0,
            "recommendation": "🔴 GET MILK NOW (8 days since last purchase)"
        }
    
    async def get_shopping_summary(user_id):
        """
        Personalized shopping recommendation summary
        """
        → {
            "urgent": [{"item": "Milk", "urgency": 0.95}],
            "upcoming": [{"item": "Bread", "urgency": 0.75}],
            "optional": [{"item": "Wine", "urgency": 0.45}],
            "estimated_next_shopping_date": "2025-12-09"
        }
```

---

### Phase 5: New Commands & Bot Interface
**Objective:** Expose predictive features through Telegram commands

**New/Modified Commands:**

1. **`/predict`** - Get AI predictions
   - Shows items you're likely to need soon
   - Ranked by urgency
   - Format: "🔴 MILK (95% urgency) - Last bought 8 days ago"

2. **`/history <item>`** - View purchase history
   - Shows last 10 purchases of specific item
   - Displays dates, quantities, prices
   - Calculates average interval

3. **`/pattern <item>`** - Detailed pattern analysis
   - Frequency distribution
   - Seasonality detection
   - Confidence score

4. **`/analytics`** - Personal shopping analytics
   - Most frequent items
   - Average spending
   - Top categories

5. **`/purchase <item> [qty] [price]`** - Manual purchase recording
   - Records immediate purchase
   - Triggers analytics update
   - Format: `/purchase Milk 2L 12.50`

6. **`/remind me`** - Smart reminder settings
   - Set urgency threshold (default 70%)
   - Configure notification frequency
   - Choose notification style

---

### Phase 6: ML Enhancement (Future)
**Objective:** Add machine learning for improved predictions

**Features:**
1. Seasonal pattern detection (winter/summer variations)
2. Price sensitivity analysis (buying patterns vs price changes)
3. Category cross-purchase (milk often bought with bread)
4. Holiday/special event adjustments
5. Anomaly detection (unusual purchase patterns)

---

## File Structure (Refactored)

```
smart shop-predictor/
├── app/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── purchase_record.py          [NEW]
│   │   ├── product_analytics.py        [NEW]
│   │   ├── shopping_preference.py      [NEW]
│   │   ├── receipt.py                  [ENHANCED]
│   │   ├── shopping_item.py
│   │   └── product.py
│   │
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── receipt_handler.py          [ENHANCED]
│   │   ├── purchase_handler.py         [NEW]
│   │   ├── import_handler.py           [NEW]
│   │   ├── prediction_handler.py       [NEW]
│   │   ├── analytics_handler.py        [NEW]
│   │   └── ...
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── purchase_analytics_service.py     [NEW]
│   │   ├── purchase_prediction_service.py    [NEW]
│   │   ├── ai_service.py               [REFACTORED]
│   │   ├── ocr_service.py
│   │   └── ...
│   │
│   ├── core/
│   │   ├── database.py
│   │   └── ...
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   └── main.py                         [ENHANCED]
│
├── PROJECT_PLAN.md                     [THIS FILE]
├── ARCHITECTURE.md                     [NEW - Technical details]
├── DATA_MODELS.md                      [NEW - Schema documentation]
├── docker-compose.yml
├── Dockerfile
├── requirements.txt                    [UPDATED]
├── .env.example
├── README.md                           [ENHANCED]
└── init.sql                            [UPDATED]
```

---

## Implementation Sequence

### Week 1-2: Foundation
1. Create new models (PurchaseRecord, ProductAnalytics, ShoppingPreference)
2. Create database migrations
3. Implement PurchaseAnalyticsService
4. Add purchase recording handler

### Week 2-3: Core Features
1. Enhance receipt processing to populate analytics
2. Implement PurchasePredictionService
3. Create prediction handler command
4. Add history/pattern commands

### Week 3-4: Polish & Testing
1. Integrate predictions into main workflow
2. Add analytics dashboard commands
3. Testing & bug fixes
4. Portainer deployment

---

## Key Metrics & Success Criteria

✅ System tracks every purchase with timestamp
✅ Calculates purchase frequency per item
✅ Predicts next purchase with >80% accuracy (after 10 purchases)
✅ Users get actionable suggestions (not generic)
✅ Bot learns and improves with more data
✅ Handles seasonal variations
✅ All features deployable via Portainer

---

## Critical Success Factor

**Data Quality = Prediction Quality**

The more accurate and complete the purchase history, the better the predictions. Early focus on reliable data collection (receipt OCR + manual entries) is essential.

---

## Next Steps

1. ✅ Create PROJECT_PLAN.md (THIS FILE)
2. Create data models (Phase 1)
3. Implement PurchaseAnalyticsService
4. Enhance receipt processing
5. Build prediction service
6. Implement commands
7. Test & deploy
