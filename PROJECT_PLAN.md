# PROJECT_PLAN.md - LLM Reference Guide

**CRITICAL**: This file serves as the single source of truth for the project. LLMs and developers should reference this file for the complete architecture and implementation plan.

---

## Quick Summary

**Project:** SmartShop Predictor - AI-powered shopping prediction engine

**Vision:** Transform shopping list management into a predictive system that learns purchase patterns and suggests items before users realize they need them.

**Current Stage:** Architecture Design Complete → Starting Phase 1 Implementation

---

## The Problem

**User's Issue:** Current bot design is wrong
- AI only suggests complementary items (e.g., "if you have milk, get butter")
- No learning from historical purchase data
- Users still must remember when to rebuy items
- Bot doesn't predict anything

**Correct Approach:** Build predictive system that:
1. Records ALL purchases with timestamps
2. Learns purchase frequency per item
3. Predicts when next purchase is likely
4. Proactively suggests: "You buy milk every 7 days. Last purchase: 6 days ago → GET MILK NOW"

---

## Architecture Overview

### Three Core Services

```
Purchase History → Analytics Engine → Prediction Service → Bot Commands
     (DB)          (Calculate       (Make predictions)    (User Interface)
                    patterns)
```

### Data Flow

1. **Input:** User records purchase (via receipt OCR or manual `/purchase` command)
2. **Store:** PurchaseRecord created with timestamp
3. **Analyze:** PurchaseAnalyticsService calculates patterns
4. **Update:** ProductAnalytics stores calculations (frequency, urgency, etc.)
5. **Predict:** PurchasePredictionService queries ProductAnalytics
6. **Output:** Bot displays `/predict` results to user

---

## Phase Breakdown (6 Phases)

### Phase 1: Data Models (CURRENT)
**Models needed:**
- `PurchaseRecord` - Individual purchase transactions
- `ProductAnalytics` - Calculated metrics per product per user
- `ShoppingPreference` - User preferences and thresholds
- Enhanced `Receipt` model with better metadata

**Files to create:**
- `app/models/purchase_record.py`
- `app/models/product_analytics.py`
- `app/models/shopping_preference.py`

### Phase 2: Enhanced Receipt Processing
**Objective:** Automatically populate purchase history from receipts

**Files to create/modify:**
- `app/handlers/receipt_handler.py` - [ENHANCE] to create PurchaseRecords
- `app/handlers/purchase_handler.py` - [NEW] manual purchase recording
- `app/handlers/import_handler.py` - [NEW] bulk historical data import

### Phase 3: Analytics Engine
**Service:** PurchaseAnalyticsService

**Calculations:**
```
1. Purchase Frequency = (total_purchases / purchase_count) * 100
2. Avg Days Between = (last_date - first_date) / (purchase_count - 1)
3. Urgency Score = (days_since_last / avg_days) * 100
4. Repurchase Probability = (times_bought_in_receipts / total_receipts) * 100
```

**File:** `app/services/purchase_analytics_service.py`

### Phase 4: Prediction Service
**Service:** PurchasePredictionService

**Methods:**
- `get_predicted_purchases(user_id, threshold)` - Returns ranked list of items to buy soon
- `get_item_prediction(user_id, product_name)` - Detailed analysis of one item
- `get_shopping_summary(user_id)` - Categorized suggestions (urgent/upcoming/optional)

**File:** `app/services/purchase_prediction_service.py`

### Phase 5: Commands & Interface
**New commands:**
- `/predict` - Get AI predictions ranked by urgency
- `/history <item>` - Show purchase history
- `/pattern <item>` - Detailed pattern analysis
- `/analytics` - Personal shopping stats
- `/purchase <item> [qty] [price]` - Manual record
- `/remind me` - Configure notification settings

### Phase 6: ML Enhancement (Future)
- Seasonal detection
- Price sensitivity
- Category cross-purchase patterns
- Holiday adjustments
- Anomaly detection

---

## Critical Data Models

### PurchaseRecord
```python
- id (UUID, PK)
- user_id (FK → User)
- item_name (str)
- category (str) # "Dairy", "Vegetables", etc.
- quantity (float)
- unit (str) # "liters", "kg", "units"
- price (float)
- currency (str) # "BRL", "USD"
- purchase_date (datetime) # CRITICAL for pattern analysis
- source (str) # "receipt" or "manual"
- receipt_id (FK → Receipt, nullable)
- created_at (datetime)
- updated_at (datetime)

Indexes:
- (user_id, product_name, purchase_date)
- (user_id, purchase_date)
```

### ProductAnalytics
```python
- id (UUID, PK)
- user_id (FK → User)
- product_name (str)
- total_purchases (int) # lifetime count
- last_purchase_date (datetime)
- avg_days_between_purchases (float) # KEY METRIC
- days_since_last_purchase (float) # dynamic
- repurchase_urgency (float) # 0-100
- repurchase_probability (float) # 0-100
- purchase_frequency_pattern (JSON) # {"Mon": 0.1, "Fri": 0.9}
- estimated_next_purchase_date (datetime) # prediction
- min_days_interval (float)
- max_days_interval (float)
- is_seasonal (bool)
- created_at (datetime)
- updated_at (datetime)

Indexes:
- (user_id, repurchase_urgency DESC) # for quick ranking
- (user_id, product_name)
```

---

## Key Formulas

### Urgency Score (0-100, higher = more urgent)
```
urgency = (days_since_last / avg_days_between) * 100

Examples:
- Milk: avg=7, last=6 days ago → 85% (coming soon)
- Milk: avg=7, last=8 days ago → 114% (OVERDUE)
- Wine: avg=30, last=15 days ago → 50% (not urgent)
```

### Repurchase Probability (0-100, how often user buys it)
```
probability = (total_times_purchased / total_receipts) * 100

Examples:
- Milk: 52 purchases in 52 receipts → 100% (always)
- Eggs: 48 purchases in 52 receipts → 92% (usually)
- Wine: 15 purchases in 52 receipts → 29% (sometimes)
```

### Purchase Frequency
```
freq_days = (last_date - first_date) / (purchase_count - 1)

Example:
- First milk purchase: 2025-01-01
- Last milk purchase: 2025-12-03
- Total purchases: 52
- Frequency = (335 days / 51) = 6.5 days average
```

---

## File Structure (Final)

```
smart shop-predictor/
├── app/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── purchase_record.py          [NEW - Phase 1]
│   │   ├── product_analytics.py        [NEW - Phase 1]
│   │   ├── shopping_preference.py      [NEW - Phase 1]
│   │   ├── receipt.py                  [ENHANCE]
│   │   ├── shopping_item.py
│   │   └── product.py
│   ├── handlers/
│   │   ├── receipt_handler.py          [ENHANCE - Phase 2]
│   │   ├── purchase_handler.py         [NEW - Phase 2]
│   │   ├── import_handler.py           [NEW - Phase 2]
│   │   ├── prediction_handler.py       [NEW - Phase 5]
│   │   ├── analytics_handler.py        [NEW - Phase 5]
│   │   └── ...
│   ├── services/
│   │   ├── purchase_analytics_service.py    [NEW - Phase 3]
│   │   ├── purchase_prediction_service.py   [NEW - Phase 4]
│   │   ├── ai_service.py               [REFACTOR]
│   │   ├── ocr_service.py
│   │   └── ...
│   ├── core/
│   ├── config/
│   └── main.py
├── PROJECT_PLAN.md                     [THIS FILE]
├── ARCHITECTURE.md                     [Coming]
├── DATA_MODELS.md                      [Coming]
├── README.md
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── ...
```

---

## Implementation Checklist

### Phase 1: Data Models
- [ ] Create PurchaseRecord model
- [ ] Create ProductAnalytics model
- [ ] Create ShoppingPreference model
- [ ] Create database migrations
- [ ] Verify indexes

### Phase 2: Purchase Recording
- [ ] Enhance receipt handler to create PurchaseRecords
- [ ] Create purchase_handler for manual entry
- [ ] Create import_handler for CSV uploads
- [ ] Add `/purchase` command

### Phase 3: Analytics
- [ ] Implement PurchaseAnalyticsService
- [ ] Implement purchase frequency calculation
- [ ] Implement urgency score calculation
- [ ] Implement repurchase probability calculation
- [ ] Add background job to update ProductAnalytics

### Phase 4: Prediction
- [ ] Implement PurchasePredictionService
- [ ] Implement get_predicted_purchases()
- [ ] Implement get_item_prediction()
- [ ] Implement get_shopping_summary()

### Phase 5: Commands
- [ ] Create prediction_handler.py
- [ ] Create analytics_handler.py
- [ ] Implement `/predict` command
- [ ] Implement `/history` command
- [ ] Implement `/pattern` command
- [ ] Implement `/analytics` command

### Phase 6: ML (Future)
- [ ] Add seasonal detection
- [ ] Add price sensitivity tracking
- [ ] Add category correlation

---

## Success Metrics

✅ All purchases tracked with timestamps
✅ Frequency calculation accurate for each item
✅ Urgency scores correctly prioritize items
✅ Predictions improve after 10+ purchases
✅ User gets actionable, personalized suggestions
✅ System deployable via Portainer
✅ Can be completely refactored from old design

---

## Important Notes

1. **Data Quality is Everything** - System is only as good as input data. Emphasis on reliable receipt OCR and manual entry.

2. **User Feedback Loop** - System learns better when users consistently record purchases. First 10-20 purchases establish baseline.

3. **Cold Start Problem** - New users need manual purchase entry or historical data import to see predictions.

4. **Seasonality** - Some items show clear patterns (milk weekly, wine monthly). System should detect and account for this.

5. **Currency Handling** - Track multiple currencies for international users. Current focus: Brazilian Real (BRL).

---

## References

- Full README.md: Comprehensive project overview
- ARCHITECTURE.md: Technical implementation details (coming)
- DATA_MODELS.md: Complete schema documentation (coming)

---

**Last Updated:** 2025-12-03
**Status:** Architecture Complete - Ready for Phase 1 Implementation
**Next Action:** Create data models
