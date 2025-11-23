# Finance Tracker 💰

A comprehensive personal finance dashboard built with Python, Dash, and SQLite for managing multi-currency expenses, zero-based budgeting, and reimbursable transaction tracking.

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Application Architecture](#application-architecture)
4. [Currency System & Quorum Logic](#currency-system--quorum-logic)
5. [Dashboard Pages & Features](#dashboard-pages--features)
6. [Database Schema](#database-schema)
7. [How Everything Works Together](#how-everything-works-together)
8. [Project Structure](#project-structure)
9. [Setup & Installation](#setup--installation)
10. [Usage Guide](#usage-guide)
11. [Development Roadmap](#development-roadmap)

---

## Overview

Finance Tracker is a personal finance management system designed for tracking expenses across multiple currencies (EUR/USD), managing zero-based budgets with flexible templates, and handling reimbursable transactions (Quorum) separately from personal spending. The application provides real-time insights into spending patterns, budget adherence, and savings progress.

**Built with:** Python 3.12, Dash, SQLite, Plotly, Pandas

---

## Key Features

### Financial Management
- ✅ **Multi-currency support** - Native EUR and USD handling with automatic exchange rate fetching
- ✅ **Zero-based budgeting** - Track every euro against your budget with rollover management
- ✅ **Budget templates** - Pre-configured scenarios (Single, Couples, Working Couples) with easy switching
- ✅ **Intelligent categorization** - Auto-categorization with merchant pattern learning
- ✅ **Billing cycle views** - Toggle between calendar month and billing period (25th-25th)

### Quorum (Reimbursable Transactions)
- ✅ **Separate tracking** - Automatic detection and isolation of reimbursable expenses
- ✅ **Monthly summaries** - Aggregate Quorum totals with reimbursement status tracking
- ✅ **Payment calculations** - Accurately separate personal vs. reimbursable amounts in credit card payments

### Savings & Goals
- ✅ **Savings buckets** - Goal-based savings with progress tracking and timeline projections
- ✅ **Multi-currency buckets** - Separate EUR and USD savings management
- ✅ **Target date tracking** - Monitor progress toward time-based financial goals

### Analytics & Reporting
- ✅ **Historical analytics** - Spending trends, category breakdowns, and budget adherence
- ✅ **Merchant insights** - Top merchants and spending patterns
- ✅ **PDF reports** - Monthly reports optimized for mobile viewing
- ✅ **CSV exports** - Flexible data export for backup and analysis

### User Experience
- ✅ **Theme switching** - Light and dark mode support
- ✅ **Drag-and-drop imports** - Easy CSV upload with preview and validation
- ✅ **Smart deduplication** - UUID-based duplicate detection during imports
- ✅ **Responsive design** - Mobile-friendly interface

---

## Application Architecture

### Core Modules

**1. Import Pipeline**
- CSV processing with format validation
- Automatic Quorum detection (via card numbers: 7575, 4479)
- Currency conversion using historical exchange rates (Frankfurter API)
- Merchant-based auto-categorization with learning
- UUID-based deduplication (hash of date + description + amount)
- Preview and manual correction before commit

**2. Dashboard (Main Page)**
- Monthly income/spending/savings overview
- Budget vs. actual progress bars
- Quorum reimbursement widget
- Quick actions (import, manual entry)
- Top category spending

**3. Transactions Management**
- Filterable, sortable transaction table
- Advanced filters (date range, category, amount, Quorum status)
- Inline editing with bulk operations
- Transaction grouping and analysis
- CSV export functionality

**4. Budget System**
- Template-based budget creation
- Monthly budget view (replicating spreadsheet layouts)
- Budget locking after month closes (immutable history)
- Rollover management (manual trigger)
- Budget vs. actual tracking across all categories

**5. Savings Module**
- Visual progress bars for each bucket
- Goal completion indicators
- Transaction history per bucket
- Timeline projections based on contribution patterns
- Combined EUR/USD overview

**6. Analytics Dashboard**
- Spending trends over time (line charts)
- Category breakdown (pie/bar charts)
- Month-to-month variation analysis
- Top merchants ranking
- Budget adherence patterns
- Long-term spending drift detection

**7. PDF Reporting**
- Monthly summary reports
- Embedded charts and tables
- Optimized for mobile viewing
- One file per month (overwrites on regeneration)
- Filename format: `Finance_Report_Nov_2025.pdf`

**8. Settings & Configuration**
- Category management (add/edit/deactivate)
- Budget template editor
- Income stream configuration
- Merchant mapping rules
- Backup and restore functions
- Theme preferences

---

## Currency System & Quorum Logic

### Non-Quorum Transactions (Your Personal Expenses)

**Native Currency:** EUR (transactions in Germany)

**Storage:**
- `original_amount`: Amount in EUR from CSV
- `original_currency`: 'EUR'
- `amount_eur`: EUR amount
- `amount_usd`: Converted using historical exchange rate
- `exchange_rate`: EUR/USD rate at transaction date

**Display:** `€23.45 (≈$25.12)`

**Budget Impact:** Included in budget calculations

**Credit Card Payment:** Converted to USD for payment calculation

**Example:**
```
Transaction: REWE Supermarket
- original_amount: 23.45
- original_currency: 'EUR'
- amount_eur: 23.45
- amount_usd: 25.12
- exchange_rate: 1.0712
- Counts toward Groceries budget
```

### Quorum Transactions (Reimbursable Expenses)

**Native Currency:** USD (transactions in Puerto Rico, cards 7575 & 4479)

**Storage:**
- `original_amount`: Amount in USD
- `original_currency`: 'USD'
- `amount_eur`: NULL (not applicable)
- `amount_usd`: USD amount (no conversion)
- `exchange_rate`: NULL
- `is_quorum`: TRUE

**Display:** `$78.41`

**Budget Impact:** Excluded from budget calculations

**Credit Card Payment:** Included as-is in USD total

**Reimbursement:** Tracked monthly, reimbursed in USD only

**Example:**
```
Transaction: DIRECTV Puerto Rico
- original_amount: 78.41
- original_currency: 'USD'
- amount_eur: NULL
- amount_usd: 78.41
- exchange_rate: NULL
- Does NOT count toward budget
- Tracked in monthly reimbursement total
```

### Exchange Rate Handling

**API:** Frankfurter (European Central Bank data)
- Endpoint: `https://api.frankfurter.app/{YYYY-MM-DD}?from=EUR&to=USD`
- **Caching:** Rates stored in `exchange_rates` table to avoid repeated API calls
- **Fallback Strategy:** If exact date unavailable, searches ±3 days window
- **Manual Override:** Prompts user if no rate found within window

### Credit Card Payment Calculation

**Statement Period:** 26th of previous month to 25th of current month  
**Payment Due:** 19th of following month

**Calculation:**
```
Your EUR Expenses:  €1,573.45 → $1,686.48 (avg rate: 1.072)
Quorum (USD):                 → $267.75
                             ──────────
Total Due:                     $1,954.23

Pending Reimbursement:        -$267.75
                             ──────────
Net You Pay:                   $1,686.48
```

---

## Dashboard Pages & Features

### Page 1: Dashboard (Home)

**Month Overview Card**
- Total income (EUR)
- Total spent (EUR, excluding Quorum)
- Total saved (EUR)
- Rollover amount (if any)
- Status indicator (under/over budget)

**Budget vs. Actual Section**
- Progress bars for top 5 categories
- Visual indicators: green (under budget), yellow (approaching limit), red (over budget)
- Percentage spent vs. budgeted

**Quorum Widget**
```
┌─────────────────────────────────────┐
│ NOVEMBER QUORUM                      │
│ Total: $267.75                       │
│ Status: ⏳ Pending                  │
│ [Record Reimbursement]               │
└─────────────────────────────────────┘
```

**Quick Actions**
- Import new transactions (CSV upload)
- Add manual transaction
- Process rollover (appears when month has leftover)
- View billing cycle summary

**Template Indicator**
- Shows current budget template
- Quick switch button: `Current Template: Single 🔄 [Switch]`

### Page 2: Transactions

**Filter Bar**
- Date range picker (with presets: This Month, Last Month, Last 3 Months, etc.)
- Category and subcategory dropdowns
- Amount range (min/max)
- Quorum filter (All / Only Quorum / Exclude Quorum)
- Text search (description)
- Card number filter

**Transaction Table**
- Columns: Date, Description, Amount, Category, Subcategory, Budget Type, Card, Quorum Flag
- Sortable by any column
- Pagination (configurable rows per page)
- Row colors: Quorum transactions highlighted
- Click row to open edit modal

**Edit Modal**
- All fields editable
- Merchant pattern suggestion
- "Apply this mapping to all similar merchants" checkbox
- Notes field
- Save/Cancel actions

**Bulk Operations**
- Select multiple transactions
- Bulk categorization
- Bulk export to CSV

**Export Options**
- Export filtered view
- Export all transactions
- Export current month only

### Page 3: Budget Management

**Monthly View Header**
- Month/year selector
- Template indicator and switcher
- Billing period indicator
- Lock status (past months are locked)

**Summary Card**
```
┌─────────────────────────────────────┐
│ NOVEMBER 2025 SUMMARY               │
│ Template: Single                     │
│ Billing: Oct 26 - Nov 25            │
│                                      │
│ Budgeted:  €2,844.67                │
│ Spent:     €1,823.45 (64%)          │
│ Saved:     €1,000.00 (35%)          │
│ Leftover:     €21.22 (1%)           │
│ Status: ✅ Zero-based achieved      │
└─────────────────────────────────────┘
```

**Budget Breakdown Tables**

**INCOME Section**
| Source | Budgeted | Actual | Variance |
|--------|----------|--------|----------|
| Salary | €2,844.67 | €2,844.67 | €0.00 |
| Rollover from Oct | €0.00 | €0.00 | €0.00 |

**SAVINGS Section**
| Bucket | Budgeted | Actual | Status |
|--------|----------|--------|--------|
| Personal Fund | €600.00 | €600.00 | ✅ |
| Roth IRA | €400.00 | €400.00 | ✅ |

**NEEDS Section**
| Category | Subcategory | Budgeted | Actual | Remaining |
|----------|-------------|----------|--------|-----------|
| Rent | Rent | €930.00 | €930.00 | €0.00 |
| Groceries | Supermarket | €300.00 | €287.45 | €12.55 |
| Groceries | Pharmacy | €50.00 | €23.18 | €26.82 |

**WANTS Section**
(Same structure as Needs)

**UNEXPECTED Section**
(Same structure)

**ADDITIONAL Section**
(Same structure)

**Actions**
- Edit budgets (only for unlocked months)
- Copy budget to next month
- Generate PDF report
- Process rollover

### Page 4: Savings

**Total Savings Overview**
```
┌──────────────────────────────────────┐
│ TOTAL SAVINGS                         │
│ EUR:  €10,056.00                     │
│ USD:  $5,447.00 (≈€4,892.00)        │
│ Combined: ≈€14,948.00                │
└──────────────────────────────────────┘
```

**Bucket Cards**
```
┌────────────────────────────────────────┐
│ 🇪🇺 Personal Fund (EUR)               │
│ ████████████████████░░  €5,221/€5,000 │
│ 104% • Goal exceeded! ✅              │
│ Started: €0 (Jan 2025)                 │
│ [View Transactions] [Add Transaction]  │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ 🇺🇸 Marriage Fund (USD)                │
│ ████████████████░░░░  $9,750/$10,720  │
│ 91% • $970 remaining                   │
│ Target: Apr 2026 • On track ✅        │
│ Projected completion: Mar 2026         │
│ [View Transactions] [Add Transaction]  │
└────────────────────────────────────────┘
```

**Timeline Projection Chart**
- Historical contributions (solid lines)
- Projected progress (dashed lines)
- Goal milestones marked
- Calculated using 3-month average contribution

**Actions**
- Add new bucket
- Record deposit/withdrawal
- Transfer between buckets
- Deactivate completed goals

### Page 5: Analytics

**Time Range Selector**
- Preset ranges (Last 3 months, Last 6 months, This year, All time)
- Custom date range picker

**Spending Trends Chart**
- Line chart showing monthly spending by top categories
- Toggle categories on/off
- Hover for exact amounts

**Category Breakdown**
- Pie chart: Needs vs. Wants vs. Savings vs. Unexpected
- Drill-down by clicking segments
- Percentage and amount labels

**Budget Adherence Over Time**
- Bar chart: Budgeted vs. Actual for each month
- Color coding: green (under), red (over)
- Trend line showing improvement/decline

**Top Merchants Table**
| Rank | Merchant | Total Spent | Transactions | Avg per Transaction |
|------|----------|-------------|--------------|---------------------|
| 1 | REWE | €1,234.56 | 52 | €23.74 |
| 2 | Netto | €876.43 | 38 | €23.06 |
| 3 | MCDONALDS | €543.21 | 29 | €18.73 |

**Month-to-Month Variance**
- Shows spending volatility by category
- Highlights unusual patterns

**Export Options**
- Export charts as images
- Export full analytics report (PDF)
- Export raw data (CSV)

### Page 6: Settings

**Categories Management**
```
Budget Types
├─ Needs
│  ├─ Rent
│  ├─ Groceries
│  │  ├─ Supermarket
│  │  └─ Pharmacy
│  └─ Transportation
├─ Wants
├─ Savings
├─ Income
└─ Unexpected
```
- Expandable tree view
- Add/Edit/Deactivate categories
- Cannot delete categories with historical transactions

**Budget Templates**
- View all templates (Single, Couples, Working Couples)
- Edit template budgets
- Create custom templates
- Set default template for new months
- Cannot modify templates used in locked months

**Income Streams**
| Name | Amount | Frequency | Owner | Active |
|------|--------|-----------|-------|--------|
| Salary - You | €2,844.67 | Monthly | You | ✅ |
| Salary - Partner | €0.00 | Monthly | Partner | ❌ |

- Add/Edit/Deactivate streams
- Support for different frequencies (monthly, biweekly, etc.)
- Multi-owner support for couples

**Merchant Mappings**
| Pattern | Subcategory | Confidence | Last Used |
|---------|-------------|------------|-----------|
| REWE% | Supermarket | 47 | Nov 22, 2025 |
| MCDONALDS% | Fast Food | 23 | Nov 20, 2025 |

- View learned patterns
- Edit mappings
- Clear learning data (reset confidence)

**Billing Cycle Configuration**
- Statement close date: [25th ▼]
- Payment due date: [19th ▼]

**Data Management**
- Export all transactions (CSV)
- Export database backup (.db file)
- Import backup
- Clear all data (with confirmation)

**Preferences**
- Theme: ☀️ Light / 🌙 Dark
- Default view: Calendar month / Billing cycle
- Currency display preferences

---

## Database Schema

The application uses **SQLite** as its database backend for concurrency safety and reliability.

### Core Transaction Storage

#### **transactions**
Stores all bank transactions processed through the import system.

**Key Columns:**
- `uuid` (TEXT, PRIMARY KEY) - Unique identifier generated from date + description + amount
- `date` (DATE) - Transaction date
- `description` (TEXT) - Merchant/transaction description
- `original_amount` (DECIMAL) - Amount exactly as it appears in CSV
- `original_currency` (TEXT) - 'EUR' or 'USD'
- `amount_eur` (DECIMAL) - EUR amount (NULL for Quorum)
- `amount_usd` (DECIMAL) - USD amount (direct for Quorum, converted for EUR)
- `exchange_rate` (DECIMAL) - EUR/USD rate (NULL for Quorum)
- `subcategory` (TEXT) - Fine-grained category
- `category` (TEXT) - Broad category
- `budget_type` (TEXT) - Needs/Wants/Savings/Income/Unexpected/Additional
- `card_number` (TEXT) - Last 4 digits of card
- `is_quorum` (BOOLEAN) - Flags reimbursable transactions
- `notes` (TEXT) - User notes
- `created_at` (TIMESTAMP) - Import timestamp
- `updated_at` (TIMESTAMP) - Last modification timestamp

**Purpose:** Central repository for all financial transactions with full currency and categorization metadata.

---

### Categories & Budget Structure

#### **categories**
Defines the valid category hierarchy used across the application.

**Key Columns:**
- `id` (INTEGER, PRIMARY KEY)
- `budget_type` (TEXT) - Needs/Wants/Savings/Income/Unexpected/Additional
- `category` (TEXT) - Broad category (e.g., "Groceries")
- `subcategory` (TEXT) - Specific subcategory (e.g., "Supermarket")
- `is_active` (BOOLEAN) - Active status
- `created_at` (TIMESTAMP)

**Unique Constraint:** (budget_type, category, subcategory)

**Purpose:** Master list of all categories; maintains consistency across transactions and budgets.

---

#### **budget_templates**
Reusable budget scenarios for different life situations.

**Key Columns:**
- `id` (INTEGER, PRIMARY KEY)
- `name` (TEXT) - "Single", "Couples", "Working Couples"
- `is_active` (BOOLEAN)
- `created_at` (TIMESTAMP)

**Purpose:** Allows quick switching between predefined budget structures.

---

#### **template_categories**
Links templates to specific budget allocations.

**Key Columns:**
- `id` (INTEGER, PRIMARY KEY)
- `template_id` (INTEGER, FOREIGN KEY → budget_templates)
- `budget_type` (TEXT)
- `category` (TEXT)
- `subcategory` (TEXT)
- `budgeted_amount` (DECIMAL) - Default budget for this category

**Purpose:** Stores the budget amounts for each category within a template.

---

#### **monthly_budgets**
Actual budget for a specific month, instantiated from a template.

**Key Columns:**
- `id` (INTEGER, PRIMARY KEY)
- `year` (INTEGER)
- `month` (INTEGER)
- `template_id` (INTEGER, FOREIGN KEY → budget_templates) - Which template was used
- `budget_type` (TEXT)
- `category` (TEXT)
- `subcategory` (TEXT)
- `budgeted_amount` (DECIMAL) - Budget amount for this month
- `is_locked` (BOOLEAN) - TRUE after month ends (prevents editing)
- `notes` (TEXT)

**Unique Constraint:** (year, month, budget_type, category, subcategory)

**Purpose:** Historical record of what was budgeted each month; locked after month closes for immutable records.

---

### Savings Module

#### **savings_buckets**
Represents individual savings goals or buckets.

**Key Columns:**
- `id` (INTEGER, PRIMARY KEY)
- `name` (TEXT) - "Personal Fund", "Marriage Fund", etc.
- `currency` (TEXT) - 'EUR' or 'USD'
- `goal_amount` (DECIMAL) - Target amount
- `start_amount` (DECIMAL) - Initial balance (default: 0)
- `is_active` (BOOLEAN) - Active status
- `target_date` (DATE) - Optional goal completion date
- `created_at` (TIMESTAMP)

**Purpose:** Defines savings goals with target amounts and deadlines.

---

#### **savings_transactions**
Logs all movements into or out of savings buckets.

**Key Columns:**
- `id` (INTEGER, PRIMARY KEY)
- `bucket_id` (INTEGER, FOREIGN KEY → savings_buckets)
- `date` (DATE) - Transaction date
- `amount` (DECIMAL) - Amount moved
- `transaction_type` (TEXT) - 'credit' (add), 'debit' (withdraw), 'transfer'
- `description` (TEXT) - Transaction description
- `created_at` (TIMESTAMP)

**Purpose:** Maintains full transaction history for each bucket; current balance calculated by summing transactions.

---

### Income & Reimbursements

#### **income_streams**
Tracks recurring income sources.

**Key Columns:**
- `id` (INTEGER, PRIMARY KEY)
- `name` (TEXT) - "Salary - You", "Salary - Partner"
- `amount` (DECIMAL) - Income amount
- `frequency` (TEXT) - 'monthly', 'biweekly', etc.
- `is_active` (BOOLEAN)
- `owner` (TEXT) - "You", "Partner" (for couples)
- `created_at` (TIMESTAMP)

**Purpose:** Tracks expected income; used in budget planning and rollover calculations.

---

#### **reimbursements**
Tracks monthly Quorum reimbursement totals.

**Key Columns:**
- `id` (INTEGER, PRIMARY KEY)
- `year` (INTEGER)
- `month` (INTEGER)
- `total_quorum_usd` (DECIMAL) - Sum of all Quorum transactions for this month
- `reimbursed_amount_usd` (DECIMAL) - Amount actually reimbursed (default: 0)
- `reimbursement_date` (DATE) - Date reimbursement received
- `notes` (TEXT)

**Unique Constraint:** (year, month)

**Purpose:** Aggregates Quorum transactions by month; tracks reimbursement status separately from individual transactions.

---

### Merchant Rules & Configuration

#### **merchant_mapping**
Auto-categorization rules based on merchant patterns.

**Key Columns:**
- `merchant_pattern` (TEXT, PRIMARY KEY) - Pattern like "REWE%", "MCDONALDS%"
- `subcategory` (TEXT) - Target subcategory
- `confidence` (INTEGER) - Number of times this mapping was confirmed (default: 1)
- `last_used` (TIMESTAMP)

**Purpose:** Powers the auto-categorization engine; learns from user corrections over time.

---

#### **app_config**
Global application settings stored as key-value pairs.

**Key Columns:**
- `key` (TEXT, PRIMARY KEY) - Setting name (e.g., 'theme', 'default_view')
- `value` (TEXT) - Setting value
- `updated_at` (TIMESTAMP)

**Purpose:** Stores user preferences and application configuration.

---

#### **exchange_rates**
Caches daily EUR/USD exchange rates.

**Key Columns:**
- `date` (DATE, PRIMARY KEY)
- `eur_to_usd` (DECIMAL) - Exchange rate
- `fetched_at` (TIMESTAMP)

**Purpose:** Caches API responses to avoid repeated calls; improves performance and reliability.

---

### Database Relationships

```
transactions
├─ References: categories (via subcategory/category/budget_type)
├─ Used by: monthly_budgets (for actual calculations)
└─ Aggregated into: reimbursements (for Quorum totals)

monthly_budgets
├─ References: budget_templates (via template_id)
└─ References: categories (via budget_type/category/subcategory)

budget_templates
└─ Has many: template_categories

savings_buckets
└─ Has many: savings_transactions

merchant_mapping
└─ Used by: import pipeline (for auto-categorization)

exchange_rates
└─ Used by: import pipeline (for currency conversion)
```

---

## How Everything Works Together

### 1. CSV Import Workflow

**Process Flow:**
1. User uploads CSV via drag-and-drop interface
2. System parses CSV and validates format
3. For each transaction:
   - Generates UUID hash (date + description + amount) for deduplication
   - Checks if UUID exists in database (duplicate detection)
   - Identifies Quorum via card number (7575 or 4479)
   - Determines original currency:
     - Quorum → USD (no conversion needed)
     - Non-Quorum → EUR (fetch exchange rate)
   - Fetches historical EUR/USD rate from Frankfurter API (with caching)
   - Attempts auto-categorization using merchant_mapping table
4. Preview screen shows:
   - ✅ Auto-categorized transactions (green highlight)
   - ⚠️ Needs manual categorization (yellow highlight)
   - 🔄 Duplicates (grayed out, will be skipped)
5. User reviews and corrects categories
6. User confirms import
7. System:
   - Inserts validated transactions into database
   - Updates merchant_mapping confidence scores
   - Recalculates monthly Quorum totals
   - Updates exchange_rates cache

**CSV Format Expected:**
- Tab-separated values
- Columns: `DATE`, `DESCRIPTION`, `AMOUNT`, `SUBCATEGORY`, `CATEGORY`, `Card No.`
- Date format: `DD.MM.YYYY`
- Amount format: European decimal (`1.234,56 €`)

---

### 2. Exchange Rate Management

**Fetching Strategy:**
1. Check `exchange_rates` table for cached rate
2. If not cached:
   - Call Frankfurter API: `https://api.frankfurter.app/{date}?from=EUR&to=USD`
   - If exact date unavailable, try ±3 day window
   - If still unavailable, prompt user for manual entry
3. Cache fetched rate for future use

**Conversion Logic:**
```
Non-Quorum (EUR → USD):
  amount_usd = amount_eur × exchange_rate

Quorum (USD native):
  amount_usd = original_amount
  amount_eur = NULL
  exchange_rate = NULL
```

---

### 3. Budget Calculation & Tracking

**Creating a Monthly Budget:**
1. User selects a budget template (or uses default)
2. System copies all `template_categories` to `monthly_budgets` for the selected month
3. User can edit individual budget amounts before month starts
4. Once month begins, budget is active

**Calculating Actuals:**
1. Query all transactions for the month
2. **Exclude Quorum transactions** (is_quorum = TRUE)
3. Group by budget_type → category → subcategory
4. Sum `amount_eur` for each group
5. Compare against `budgeted_amount` from `monthly_budgets`

**Progress Calculation:**
```python
spent_percentage = (actual_spent / budgeted_amount) * 100
remaining = budgeted_amount - actual_spent

Status:
  - Green: spent_percentage < 80%
  - Yellow: 80% ≤ spent_percentage < 100%
  - Red: spent_percentage ≥ 100%
```

**Budget Locking:**
- At month-end, `is_locked` set to TRUE
- Locked budgets become immutable historical records
- Prevents retroactive budget adjustments

---

### 4. Quorum Reimbursement Tracking

**Automatic Calculation:**
1. All transactions with `is_quorum = TRUE` flagged during import
2. Monthly job (or on-demand) calculates:
   ```sql
   total_quorum_usd = SUM(amount_usd) 
   WHERE is_quorum = TRUE 
   AND year = X 
   AND month = Y
   ```
3. Creates/updates record in `reimbursements` table

**Recording Reimbursement:**
1. User clicks "Record Reimbursement" in dashboard widget
2. Modal prompts for:
   - Reimbursed amount (USD)
   - Reimbursement date
   - Optional notes
3. System updates `reimbursements` record
4. Widget updates to show "Reimbursed ✅"

**Dashboard Display:**
```
Pending:
┌─────────────────────────────────────┐
│ NOVEMBER QUORUM                      │
│ Total: $267.75                       │
│ Status: ⏳ Pending                  │
│ [Record Reimbursement]               │
└─────────────────────────────────────┘

After Recording:
┌─────────────────────────────────────┐
│ NOVEMBER QUORUM                      │
│ Total: $267.75                       │
│ Reimbursed: $267.75 on Nov 30       │
│ Status: ✅ Received                 │
└─────────────────────────────────────┘
```

---

### 5. Credit Card Payment Calculation

**Billing Cycle Logic:**
- **Statement Period:** 26th (previous month) to 25th (current month)
- **Payment Due:** 19th (following month)

**Total Due Calculation:**
```python
# Get all transactions in billing period
transactions = get_transactions_between(
    start_date=f"{previous_month}-26",
    end_date=f"{current_month}-25"
)

# Calculate totals
eur_total_usd = sum([tx.amount_usd for tx in transactions if not tx.is_quorum])
quorum_total_usd = sum([tx.amount_usd for tx in transactions if tx.is_quorum])

total_due = eur_total_usd + quorum_total_usd

# Reimbursement
pending_reimbursement = get_reimbursement(year, month).total_quorum_usd
net_you_pay = total_due - pending_reimbursement
```

**Display Format:**
```
STATEMENT: Oct 26 - Nov 25

Your EUR Expenses:  €1,573.45 → $1,686.48 (avg rate: 1.072)
Quorum (USD):                 →   $267.75
                              ─────────────
Total Due (Dec 19):              $1,954.23

Pending Reimbursement:           -$267.75
                              ─────────────
Net You Pay:                     $1,686.48
```

---

### 6. Savings Management

**Creating a Bucket:**
1. User defines: name, currency (EUR/USD), goal amount, optional target date
2. System creates entry in `savings_buckets`

**Recording Transactions:**
1. User records deposit/withdrawal/transfer
2. System creates entry in `savings_transactions` linked to bucket
3. Transaction types:
   - **credit:** Money added to bucket
   - **debit:** Money withdrawn from bucket
   - **transfer:** Money moved between buckets

**Current Balance Calculation:**
```python
current_balance = bucket.start_amount + sum([
    tx.amount if tx.transaction_type == 'credit'
    else -tx.amount if tx.transaction_type == 'debit'
    else 0  # Transfers handled separately
    for tx in bucket.transactions
])
```

**Progress Calculation:**
```python
progress_percentage = (current_balance / goal_amount) * 100

Status:
  - On track: progress_percentage ≥ expected_progress_for_target_date
  - Behind: progress_percentage < expected_progress
  - Exceeded: current_balance > goal_amount
```

**Timeline Projection:**
1. Calculate average monthly contribution (last 3 months)
2. Project forward: `months_to_goal = (goal - current) / avg_contribution`
3. Display dashed projection line on chart

---

### 7. Merchant Auto-Categorization

**Learning Process:**
1. User manually categorizes a transaction (e.g., "REWE FRANKFURT" → "Supermarket")
2. System prompts: "Apply this mapping to all similar merchants?"
3. If yes:
   - Extract pattern (e.g., "REWE%")
   - Create/update entry in `merchant_mapping`
   - Set `subcategory = "Supermarket"`
   - Increment `confidence` score

**Auto-Categorization During Import:**
1. For each transaction, check `merchant_mapping` for pattern match
2. If match found:
   - Apply subcategory automatically
   - Look up category and budget_type from `categories` table
   - Mark as "auto-categorized" in preview
3. If no match or multiple matches:
   - Mark as "needs manual review"

**Pattern Matching:**
- Uses SQL LIKE operator
- Supports wildcards: `REWE%` matches "REWE FRANKFURT", "REWE BERLIN", etc.
- Case-insensitive matching

---

### 8. Rollover Management

**Calculation:**
```python
# At month-end
income = sum(income_streams.amount for stream in active_streams)
spent = sum(tx.amount_eur for tx in transactions if not tx.is_quorum)
saved = sum(savings_transactions.amount for tx in month_savings)

rollover = income - spent - saved
```

**Processing:**
1. Dashboard shows "Process Rollover" button if `rollover != 0`
2. User clicks button
3. Modal presents options:
   - **Add to next month's income** (increases budget flexibility)
   - **Transfer to savings bucket** (keeps budget strict)
4. User selects option and confirms
5. System:
   - If "next month": Creates income adjustment in `monthly_budgets`
   - If "savings": Creates entry in `savings_transactions`

---

### 9. Analytics Generation

**Spending Trends:**
- Query transactions grouped by month and category
- Calculate totals over time
- Generate line chart with multiple series (one per category)

**Category Breakdown:**
- Sum transactions by budget_type (Needs/Wants/Savings)
- Calculate percentages
- Generate pie chart

**Budget Adherence:**
- For each month: calculate spent vs. budgeted percentage
- Track over time
- Generate bar chart showing variance

**Top Merchants:**
- Group transactions by merchant pattern
- Sum total spent and count transactions
- Calculate average per transaction
- Rank by total spent

**Month-to-Month Variance:**
- Calculate standard deviation of spending by category
- Highlight categories with high volatility
- Useful for identifying inconsistent spending patterns

---

### 10. PDF Report Generation

**Trigger:** User clicks "Export Month as PDF" button

**Content Structure:**
```
PAGE 1: Summary
├─ Month overview card (income/spent/saved)
├─ Budget vs. actual table
├─ Spending breakdown pie chart
└─ Top 5 categories

PAGE 2: Transactions
├─ Full transaction list (grouped by category)
└─ Quorum transactions separate section

PAGE 3: Savings
├─ Bucket progress bars (embedded as images)
├─ Timeline chart
└─ Transaction summaries

PAGE 4: Analytics (if multi-month data available)
├─ Spending trend chart
├─ Top merchants table
└─ Budget adherence chart
```

**Technical Implementation:**
- Uses `reportlab` library
- Plotly charts converted to images (PNG) for embedding
- Portrait orientation, A4 size
- Mobile-optimized layout
- Filename: `Finance_Report_{Month}_{Year}.pdf`
- Overwrites if regenerated

---

### 11. Theme & Preferences

**Theme Switching:**
- Toggle in navigation bar: ☀️ Light / 🌙 Dark
- Preference saved in `app_config` table (`key='theme'`)
- Uses Dash Bootstrap themes:
  - Light: `FLATLY`
  - Dark: `DARKLY`

**View Preferences:**
- Default date view: Calendar month vs. Billing cycle
- Stored in `app_config`
- Applied across all pages

---

## Project Structure

```
finance_tracker/
├── app.py                          # Main Dash application entry point
├── requirements.txt                # Python dependencies
├── setup.py                        # Complete setup script
├── README.md                       # This file
│
├── database/
│   ├── __init__.py
│   ├── models.py                   # SQLite schema definitions
│   ├── db.py                       # Database connection manager
│   ├── init_db.py                  # Database initialization + seed data
│   └── queries.py                  # Common SQL queries
│
├── import_pipeline/
│   ├── __init__.py
│   ├── csv_processor.py            # CSV parsing and validation
│   ├── exchange_rates.py           # Frankfurter API integration + caching
│   ├── categorizer.py              # Auto-categorization engine
│   ├── deduplicator.py             # UUID-based duplicate detection
│   └── migrate_historical.py       # Historical data migration script
│
├── pages/
│   ├── __init__.py
│   ├── dashboard.py                # Main overview page
│   ├── transactions.py             # Transaction management
│   ├── budget.py                   # Monthly budget view
│   ├── savings.py                  # Savings buckets & goals
│   ├── analytics.py                # Historical trends & insights
│   ├── settings.py                 # Configuration & templates
│   └── import_transactions.py      # CSV upload interface
│
├── components/
│   ├── __init__.py
│   ├── navbar.py                   # Navigation bar with theme toggle
│   ├── filters.py                  # Shared filter components
│   ├── tables.py                   # Reusable transaction tables
│   ├── charts.py                   # Plotly chart templates
│   ├── modals.py                   # Edit/confirm dialogs
│   └── cards.py                    # Summary cards
│
├── utils/
│   ├── __init__.py
│   ├── calculations.py             # Budget math, rollover logic
│   ├── pdf_generator.py            # Monthly report PDF export
│   ├── backup.py                   # Database backup/restore
│   └── helpers.py                  # Date parsing, formatting, etc.
│
├── data/
│   ├── finance.db                  # SQLite database (gitignored)
│   ├── config.json                 # User preferences (gitignored)
│   └── exchange_rates_cache.json   # Cached rates (gitignored)
│
├── reports/                        # PDF exports (gitignored)
│   └── Finance_Report_Nov_2025.pdf
│
├── uploads/                        # Temporary CSV uploads (gitignored)
│
└── assets/                         # Dash static files
    ├── styles.css                  # Custom CSS
    ├── favicon.ico
    └── logo.png                    # Optional branding
```

---

## Setup & Installation

### Prerequisites

- Python 3.12+
- pip (Python package manager)

### Installation Steps

**1. Clone or download the project**

```bash
cd finance_tracker
```

**2. Install dependencies**

```bash
pip install --break-system-packages -r requirements.txt
```

**Requirements:**
```
# Core Framework
dash==2.18.1
dash-bootstrap-components==1.6.0
dash-ag-grid==31.2.0

# Data Processing
sqlite3 (built-in)
pandas==2.2.3
numpy==2.1.3

# Charts & Visualization
plotly==5.24.1

# Currency API
requests==2.32.3

# PDF Generation
reportlab==4.2.5
Pillow==11.0.0

# Utilities
python-dateutil==2.9.0
```

**3. Initialize database**

Run the complete setup script:

```bash
PYTHONPATH=/home/claude/finance_tracker python3 setup.py
```

This script:
- ✅ Creates SQLite database with full schema
- ✅ Seeds categories (37 subcategories across 5 budget types)
- ✅ Creates budget templates (Single, Couples, Working Couples)
- ✅ Initializes app configuration
- ✅ Creates necessary directories

**4. Migrate historical data** (optional)

If you have existing transaction history in CSV format:

```bash
PYTHONPATH=/home/claude/finance_tracker python3 import_pipeline/migrate_historical.py <path_to_csv>
```

**CSV Requirements:**
- Tab-separated values
- Columns: `DATE`, `DESCRIPTION`, `AMOUNT`, `SUBCATEGORY`, `CATEGORY`
- Date format: `DD.MM.YYYY`
- Amount format: European decimal (`1.234,56 €`)

**5. Run the application**

```bash
PYTHONPATH=/home/claude/finance_tracker python3 app.py
```

Access the dashboard at: `http://localhost:8050`

---

## Usage Guide

### First-Time Setup

**1. Configure Income Streams** (Settings page)
- Add your salary and any other recurring income
- Set frequency (monthly, biweekly, etc.)
- Mark as active

**2. Review Category Mappings** (Settings page)
- Verify the pre-seeded categories match your needs
- Add any custom subcategories
- Deactivate categories you won't use

**3. Select Budget Template** (Dashboard or Budget page)
- Choose: Single, Couples, or Working Couples
- This sets your default monthly budgets
- You can customize amounts after selection

**4. Set Billing Cycle** (Settings page)
- Statement close date: [25th]
- Payment due date: [19th]
- These determine billing cycle views

### Importing Transactions

**From Bank CSV:**
1. Go to Dashboard → "Import Transactions"
2. Drag CSV file into upload area
3. System parses and validates
4. Review preview:
   - Green = Auto-categorized
   - Yellow = Needs manual review
   - Gray = Duplicate (will skip)
5. Correct any categories as needed
6. When prompted, confirm: "Apply this mapping to similar merchants?"
7. Click "Confirm Import"

**Manual Entry:**
1. Go to Dashboard → "Add Manual Entry"
2. Fill in fields:
   - Date
   - Description
   - Amount
   - Currency (EUR/USD)
   - Category/Subcategory
   - Card (optional)
   - Mark as Quorum (if applicable)
3. Click "Save"

### Managing Budget

**Creating Monthly Budget:**
1. Dashboard shows current template
2. Click 🔄 "Switch" to change template
3. Go to Budget page to customize amounts
4. Budgets auto-lock after month ends

**Processing Rollover:**
1. End of month: Dashboard shows "Process Rollover" button
2. Click button
3. Choose:
   - Add to next month (flexible budgeting)
   - Move to savings (strict budgeting)
4. Confirm

### Tracking Savings

**Creating a Bucket:**
1. Go to Savings page
2. Click "Add Bucket"
3. Fill in:
   - Name (e.g., "Emergency Fund")
   - Currency (EUR or USD)
   - Goal amount
   - Target date (optional)
4. Save

**Recording Transactions:**
1. Click bucket card
2. Click "Add Transaction"
3. Select type: Credit (deposit) / Debit (withdrawal)
4. Enter amount and description
5. Save

### Handling Quorum Reimbursements

**Recording Reimbursement:**
1. Dashboard shows "Quorum Widget" with pending total
2. Click "Record Reimbursement"
3. Enter:
   - Amount reimbursed (USD)
   - Date received
   - Notes (optional)
4. Save
5. Widget updates to show "Reimbursed ✅"

### Viewing Analytics

**Time-Based Analysis:**
1. Go to Analytics page
2. Select time range (presets or custom)
3. View:
   - Spending trends (line chart)
   - Category breakdown (pie chart)
   - Budget adherence (bar chart)
   - Top merchants (table)

**Exporting Reports:**
1. Dashboard or Budget page → "Export Month as PDF"
2. PDF saved to `reports/` folder
3. Filename: `Finance_Report_{Month}_{Year}.pdf`
4. Optimized for mobile viewing

### Backup & Export

**Database Backup:**
1. Settings → Data Management
2. Click "Export Database Backup"
3. Downloads `finance.db` file
4. Store securely

**CSV Export:**
1. Transactions page → "Export to CSV"
2. Exports current filtered view
3. Or use "Export All Transactions" for complete data

---

## Development Roadmap

### ✅ Phase 1: Foundation (Completed)
- [x] SQLite database schema designed and implemented
- [x] Database initialized with seed data (categories, templates)
- [x] Exchange rate fetcher (Frankfurter API with caching)
- [x] Historical data migration script
- [x] Category mappings seeded (37 subcategories)
- [x] Budget templates created (Single, Couples, Working Couples)

### 🚧 Phase 2: Import Pipeline (In Progress)
- [ ] CSV processor with format validation
- [ ] Deduplication engine (UUID-based)
- [ ] Auto-categorization with merchant learning
- [ ] Import UI with drag-and-drop
- [ ] Preview and correction interface

### 📋 Phase 3: Dashboard (Priority #1)
- [ ] Main dashboard layout
- [ ] Month overview cards
- [ ] Budget vs. actual progress bars
- [ ] Quorum reimbursement widget
- [ ] Quick actions (import, manual entry)
- [ ] Template switcher

### 📋 Phase 4: Budget Management
- [ ] Monthly budget view (replicate spreadsheet layout)
- [ ] Template editor in settings
- [ ] Budget locking after month-end
- [ ] Rollover processing modal
- [ ] Income stream management

### 📋 Phase 5: Savings & Analytics
- [ ] Savings buckets page
- [ ] Bucket progress visualization
- [ ] Timeline projection charts
- [ ] Transaction history per bucket
- [ ] Analytics page with charts
- [ ] Spending trends over time
- [ ] Top merchants analysis
- [ ] Budget adherence tracking

### 📋 Phase 6: Polish & Export
- [ ] Transactions page with advanced filters
- [ ] Transaction edit modal
- [ ] Bulk operations
- [ ] PDF report generator
- [ ] Settings page (complete)
- [ ] Theme toggle (light/dark)
- [ ] Backup/restore functionality
- [ ] CSV export features

### 📋 Phase 7: Enhancements (Future)
- [ ] Multi-user support (couples mode)
- [ ] Recurring transaction templates
- [ ] Budget variance alerts
- [ ] Mobile app (PWA)
- [ ] API for integrations
- [ ] Data encryption at rest

---

## Technical Notes

### Why SQLite?

- **Concurrency Safe:** Better handling of simultaneous read/write operations compared to DuckDB
- **Mature Ecosystem:** Extensive Python support via `sqlite3` (built-in)
- **Lightweight:** Single-file database, no server required
- **Reliable:** ACID-compliant transactions
- **Portable:** Database file can be easily backed up and moved

### Performance Considerations

- **Indexes:** Primary keys and foreign keys automatically indexed
- **Query Optimization:** Uses prepared statements and parameterized queries
- **Caching:** Exchange rates cached to minimize API calls
- **Pagination:** Transaction tables paginated to handle large datasets

### Security

- **Input Validation:** All user inputs sanitized before database insertion
- **SQL Injection Protection:** Parameterized queries throughout
- **File Upload Validation:** CSV files validated for format and content
- **Backup Encryption:** Recommended to encrypt backup files externally

### Testing Strategy

- **Unit Tests:** Database operations, calculations, currency conversions
- **Integration Tests:** Import pipeline, budget calculations, analytics generation
- **UI Tests:** Dash component interactions, form validations
- **Data Migration Tests:** Validation of historical data imports

---

## Troubleshooting

### Common Issues

**1. Import fails with "Exchange rate not found"**
- **Cause:** Frankfurter API doesn't have rate for transaction date
- **Solution:** System will prompt for manual entry, or use fallback rate from nearby date

**2. Transactions not appearing in budget actuals**
- **Cause:** Transaction categorized incorrectly or flagged as Quorum
- **Solution:** Edit transaction, verify category matches budget categories, ensure `is_quorum = FALSE`

**3. Duplicate transactions imported**
- **Cause:** CSV contains previously imported transactions
- **Solution:** System detects via UUID; duplicates shown in gray in preview, automatically skipped

**4. Savings bucket balance incorrect**
- **Cause:** Missing or incorrect transaction entries
- **Solution:** Review transaction history for bucket, verify all deposits/withdrawals recorded

**5. PDF export fails**
- **Cause:** Missing `reports/` directory or reportlab dependency
- **Solution:** Run `mkdir reports` and verify reportlab installed

### Database Corruption

If database becomes corrupted:
1. Stop the application
2. Restore from latest backup: `cp backup/finance.db data/finance.db`
3. If no backup: Re-initialize with `python3 setup.py` (WARNING: loses all data)

### Performance Issues

If application slows down:
1. Check transaction count: `SELECT COUNT(*) FROM transactions;`
2. If >50k transactions, consider archiving old data
3. Run VACUUM: `sqlite3 data/finance.db "VACUUM;"`
4. Verify indexes: `sqlite3 data/finance.db ".schema"`

---

## Contributing

This is a personal project, but improvements are welcome:

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am 'Add feature'`
4. Push branch: `git push origin feature/your-feature`
5. Submit pull request

---

## License

Personal use only. Not licensed for commercial distribution.

---

## Support & Contact

For issues, questions, or feature requests:
- Check database integrity: `sqlite3 data/finance.db ".schema"`
- Review application logs
- Verify CSV format matches expected structure
- Test with sample data

---

## Acknowledgments

- **Frankfurter API** - Free EUR/USD exchange rate data (European Central Bank)
- **Dash Framework** - Modern Python web applications
- **Plotly** - Interactive charts and visualizations
- **SQLite** - Reliable embedded database

---

**Built with ❤️ for personal finance management**
**Version:** 1.0.0
**Last Updated:** November 2025
