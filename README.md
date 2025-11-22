# Finance Tracker 💰

A comprehensive personal finance dashboard built with Python, Dash, and DuckDB.

## Features

✅ **Multi-currency support** - EUR/USD with automatic exchange rate fetching  
✅ **Zero-based budgeting** - Track every euro against your budget  
✅ **Quorum tracking** - Separate tracking for reimbursable expenses  
✅ **Budget templates** - Single, Couples, Working Couples  
✅ **Savings buckets** - Goal-based savings with progress tracking  
✅ **Historical analytics** - Spending trends and insights  
✅ **PDF reports** - Monthly reports for mobile viewing  
✅ **Merchant learning** - Auto-categorization based on patterns  

---

## Setup

### 1. Install Dependencies

```bash
pip install --break-system-packages -r requirements.txt
```

### 2. Initialize Database

The database has already been initialized with:
- ✅ Schema created
- ✅ Categories seeded (37 subcategories across 5 budget types)
- ✅ Budget templates created (Single, Couples, Working Couples)
- ✅ App configuration set

Database location: `data/finance.db`

### 3. Migrate Historical Data

To import your 6-month transaction history:

```bash
PYTHONPATH=/home/claude/finance_tracker python3 import_pipeline/migrate_historical.py <path_to_csv>
```

**CSV Format Requirements:**
- Tab-separated values
- Columns: `DATE`, `DESCRIPTION`, `AMOUNT`, `SUBCATEGORY`, `CATEGORY`
- Date format: `DD.MM.YYYY`
- Amount format: European (`1.234,56 €`)

**What the migration does:**
1. Parses dates and amounts
2. Generates unique UUIDs (deduplication)
3. Identifies Quorum transactions (Subcategory = "Quorum")
4. Fetches EUR/USD exchange rates from Frankfurter API
5. Maps categories and budget types
6. Calculates monthly Quorum totals
7. Inserts all data into database

---

## Project Structure

```
finance_tracker/
├── app.py                       # Main Dash application (TODO)
├── requirements.txt             # Python dependencies
├── setup.py                     # Complete setup script
│
├── database/
│   ├── models.py               # Database schema
│   ├── db.py                   # DuckDB connection manager
│   ├── init_db.py              # Database initialization
│   └── __init__.py
│
├── import_pipeline/
│   ├── exchange_rates.py       # Currency API integration
│   ├── migrate_historical.py   # Historical data migration
│   └── __init__.py
│
├── data/
│   └── finance.db              # DuckDB database (✅ initialized)
│
└── (Coming soon)
    ├── pages/                   # Dash pages
    ├── components/              # Reusable UI components
    ├── utils/                   # Helper functions
    └── reports/                 # PDF exports
```

---

## Database Schema

### Core Tables

**transactions** - All your transactions
- Stores both EUR and USD amounts
- Tracks Quorum separately
- Auto-categorization ready

**categories** - Category definitions
- Budget type (Needs/Wants/Savings/etc.)
- Category → Subcategory hierarchy

**budget_templates** - Pre-defined budget scenarios
- Single, Couples, Working Couples
- Editable in settings

**monthly_budgets** - Actual monthly budgets
- Locked after month ends (immutable historical data)
- Tracks which template was used

**reimbursements** - Monthly Quorum totals
- Automatically calculated
- Track reimbursement status

**exchange_rates** - Cached EUR/USD rates
- Fetched from European Central Bank
- Cached to avoid repeated API calls

---

## Currency Handling

### Quorum Transactions (USD)
- **In CSV:** Amount is in USD (you added `€` symbol manually)
- **In Database:** Stored as USD natively
- **No conversion needed** - These are already in the payment currency

### Your Transactions (EUR)
- **In CSV:** Amount is in EUR
- **In Database:** Stored as both EUR and USD (with exchange rate)
- **Exchange rate fetched** from Frankfurter API at transaction date
- **Fallback:** Uses nearby dates if exact date unavailable

### Example
```
Transaction: REWE 23.45€
- original_amount: 23.45
- original_currency: 'EUR'
- amount_eur: 23.45
- amount_usd: 25.12 (rate: 1.0712)
- exchange_rate: 1.0712

Transaction: DIRECTV $78.41 (Quorum)
- original_amount: 78.41
- original_currency: 'USD'
- amount_eur: NULL
- amount_usd: 78.41
- exchange_rate: NULL
```

---

## Next Steps

### Phase 2: Import Pipeline (Next to build)
- CSV processor for new transactions
- Deduplication (UUID-based)
- Auto-categorization with merchant patterns
- Import UI page

### Phase 3: Dashboard (Priority #1)
- Month overview
- Budget vs Actual tracking
- Quorum reimbursement widget
- Quick actions

### Phase 4: Budget Management
- Monthly budget view (replicate your Template sheet)
- Template switching
- Rollover processing

### Phase 5: Savings & Analytics
- Savings buckets with progress bars
- Timeline projections
- Spending trends
- Top merchants

### Phase 6: Polish & Export
- Transactions page (filterable table)
- PDF monthly reports
- Settings page
- Theme toggle (light/dark)
- Backup/export

---

## Usage Notes

### Billing Cycle vs Calendar Month
- **Primary view:** Calendar month (transaction date)
- **Secondary view:** Billing cycle (25th-25th) for payment planning
- Transactions are always stored by transaction date

### Reimbursements
- Quorum transactions tracked monthly (total, not per-transaction)
- Dashboard shows pending reimbursements
- Mark as received when father reimburses

### Budget Templates
- Switch templates anytime for current month
- Past months locked (immutable)
- Templates define default budgets for new months

---

## Running the App

```bash
PYTHONPATH=/home/claude/finance_tracker python3 app.py
```

(App development in progress - coming in Phase 3!)

---

## Development Status

### ✅ Completed (Phase 1)
- [x] Database schema designed
- [x] Database initialized with seed data
- [x] Exchange rate fetcher (Frankfurter API)
- [x] Historical data migration script
- [x] Category mappings seeded
- [x] Budget templates created

### 🚧 In Progress
- [ ] CSV import pipeline
- [ ] Dashboard UI
- [ ] Transaction management
- [ ] Budget tracking
- [ ] Savings pages
- [ ] Analytics & reports

---

## Support

For issues or questions:
1. Check database: `data/finance.db`
2. Review logs from migration
3. Test database queries manually

---

**Built with:** Python 3.12, Dash, DuckDB, Plotly, Pandas
