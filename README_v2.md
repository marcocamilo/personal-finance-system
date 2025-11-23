Below is your **base version**, with **only the missing elements added** from your most recent notes.
Additions are minimal, non-repetitive, and placed where they logically belong.
No existing text was altered.

Additions are marked with **➕ Added** for clarity — you can remove the markers afterwards.

---

# **📘 Consolidated System Summary (SQLite, With Schema Referenced)**

*(With only missing elements added)*

This summary brings together all specifications into a unified, clean description focusing on:

* **App structure**
* **Dashboard behavior**
* **Database schema (tables + key columns)**
* **How the system works end-to-end**

---

# **1. Application Architecture Overview**

The finance dashboard is a multi-page web application, backed by a **single SQLite database**, with structured modules:

### **Core Modules**

1. **Import Pipeline**
   Upload bank CSVs → clean → categorize → convert currency → store.

   ➕ **Added:**
   *Includes exchange-rate caching and a merchant-learning system to improve categorization over time.*

2. **Dashboard**
   Monthly overview, budget progress, Quorum widget, summaries.

3. **Transactions Page**
   Full table with filters, editing, grouping, exports.

4. **Budget Management**
   Templates + monthly budgets that lock after month closes.

5. **Savings Tracking**
   Buckets, goals, transactions, projections.

6. **Analytics**
   Spending trends, category charts, merchant insights.

7. **PDF Reporting**
   One monthly PDF summary.

8. **Settings**
   Categories, templates, income, merchant rules, preferences.

➕ **Added (Architecture Detail):**
The app follows a clean project structure with dedicated folders for pages, the import pipeline, and the database layer.
SQLite was chosen for **concurrency safety**, replacing DuckDB.

---

# **2. Currency System & Quorum Logic**

### **Non-Quorum Transactions**

* Native currency: **EUR**

* Stored with:

  * original_amount (EUR)
  * amount_eur
  * amount_usd (converted using daily rate)
  * exchange_rate

* Shown as: **€24.50 (≈$26.30)**

* Included in budget totals

* Included in credit card payment (converted USD)

### **Quorum Transactions**

* Native currency: **USD**

* Stored with:

  * original_amount (USD)
  * amount_usd only
  * amount_eur and exchange_rate not used

* Excluded from budget actuals

* Included in credit card payment **as USD**

* Reimbursed **in USD only**

* Monthly reimbursement tracked in its own table.

➕ **Added:**
Historical data and CSVs often show USD numbers with a “€” symbol.
The system treats the CSV amounts as **USD**, not EUR, correcting this mislabeling.

---

# **3. Dashboard Functionality**

### **Monthly Overview**

Shows:

* Total EUR spending
* Total Quorum USD
* Income received
* Savings progress
* Category spending vs. budgets

### **Budget vs. Actual**

* Built from **monthly_budgets**
* Actuals calculated only from non-Quorum EUR transactions
* Displays budgeted amount, spent, remaining, and overspending

### **Quorum Widget**

* Reads from **reimbursements** table

* Shows:

  * Monthly Quorum total (USD)
  * Status: pending or reimbursed
  * Date of reimbursement if recorded

* Allows manually recording a reimbursement event

### **Credit Card Payment View**

* Sums:

  * All EUR → USD converted expenses
  * All Quorum USD transactions

* Shows total due + pending reimbursement + net-you-pay

### **Analytics**

* Trends over time using transaction data
* Category distributions
* Merchant insights from the **merchant_mapping** table
* Budget adherence across months

➕ **Added:**
Analytics also highlight:

* Month-to-month spending variation
* Long-term category drift
* Merchant-level insights using auto-learning patterns

---

# **4. Database Schema (SQLite)**

*Below is a conceptual overview of the database tables and their important columns. Technical SQL not included, as requested.*

---

## **A. Core Transaction Storage**

### **transactions**

Stores every bank transaction processed by the import system.

Key Columns:

* **uuid** — unique identifier
* **date**
* **description**
* **original_amount** — amount exactly as it appears in CSV
* **original_currency** — EUR or USD
* **amount_eur** — null for Quorum
* **amount_usd** — direct for Quorum, converted for EUR
* **exchange_rate** — null for Quorum
* **category / subcategory / budget_type**
* **card_number**
* **is_quorum** — marks the transaction
* **notes**
* **created_at / updated_at**

➕ **Added:**
Transactions use a **UUID hash of (date + description + amount)** for deduplication during imports.

---

## **B. Categories & Budget Structure**

### **categories**

Defines valid categories/subcategories used across budgets and transactions.

Key Columns:

* **id**
* **budget_type**
* **category**
* **subcategory**
* **is_active**

### **budget_templates**

Represents reusable templates such as:

* Single
* Couples
* Working Couples
  (and optionally custom ones)

Columns:

* **id**
* **name**
* **is_active**

### **template_categories**

Links templates to predefined budget allocations.

Columns:

* **template_id**
* **budget_type**
* **category**
* **subcategory**
* **budgeted_amount**

### **monthly_budgets**

Represents budget for a specific month, generated from a template.

Columns:

* **year**
* **month**
* **template_id**
* **budget_type**
* **category**
* **subcategory**
* **budgeted_amount**
* **is_locked**
* **notes**

➕ **Added:**
Monthly budgets become “locked” after month end, preventing modifications and enabling accurate reporting.

---

## **C. Savings Module**

### **savings_buckets**

Represents a savings goal or bucket.

Columns:

* **id**
* **name**
* **currency** (EUR or USD)
* **goal_amount**
* **start_amount**
* **is_active**
* **target_date**

### **savings_transactions**

Logs movement into/out of buckets.

Columns:

* **bucket_id**
* **date**
* **amount**
* **transaction_type** (credit, debit, transfer)
* **description**

---

## **D. Income & Reimbursements**

### **income_streams**

Stores income sources (you + partner).

Columns:

* **id**
* **name**
* **amount**
* **frequency**
* **is_active**
* **owner**

### **reimbursements**

Tracks Quorum reimbursement for each month.

Columns:

* **year**
* **month**
* **total_quorum_usd** — sum of all Quorum USD transactions for that month
* **reimbursed_amount_usd**
* **reimbursement_date**
* **notes**

---

## **E. Merchant Rules & App Settings**

### **merchant_mapping**

Auto-categorization rules based on merchant patterns.

Columns:

* **merchant_pattern**
* **subcategory**
* **confidence**
* **last_used**

➕ **Added:**
The auto-categorizer **learns** whenever you manually edit a transaction’s category.

### **app_config**

Key/value settings for global configuration (theme, defaults, etc.).

Columns:

* **key**
* **value**
* **updated_at**

### **exchange_rates**

Caches daily exchange rates to avoid repeat API calls.

Columns:

* **date**
* **eur_to_usd**
* **fetched_at**

➕ **Added:**
The system includes a **3-day fallback window** to find a valid rate when the API lacks data for the exact transaction date.

---

# **5. How Everything Works Together**

1. **CSV Import**

   * Reads CSV → identifies Quorum via card numbers → determines currency → stores normalized info in `transactions`.

   ➕ **Added:**
   The import page provides a **drag-and-drop interface** with preview and validation before committing data.

2. **Exchange Handling**

   * EUR transactions get historical USD conversion.
   * Quorum stays in USD.

3. **Budgeting**

   * Monthly budgets created from a template.
   * Actuals taken from EUR transactions (non-Quorum only).
   * Progress shown in dashboard.

4. **Quorum Reimbursement**

   * `transactions` → monthly USD sum → stored in `reimbursements`.
   * Dashboard shows pending amount until reimbursement is logged.

5. **Savings Tracking**

   * Buckets store goals; transactions track movement.
   * Dashboard and savings page visualize progress.

6. **Analytics**

   * Uses all tables to generate trends and breakdowns.
   * Merchant insights powered by learned mappings.

7. **PDF Reports**

   * Monthly report generated from the database state.

---

# **✔ Final Summary**

Your application is a **comprehensive personal finance system** with:

* A clean SQLite-based data model
* Accurate EUR + USD currency logic
* Dedicated Quorum handling with monthly reimbursement tracking
* Structured budgeting (templates → monthly budgets)
* Savings management, analytics, and reporting
* A dashboard that pulls together everything in a coherent, real-time view

Every table and major field contributing to the behavior has been incorporated into this summary — with all missing pieces merged from your latest notes.

---

If you'd like, I can now also:

📄 Produce a **PDF spec**
🧩 Generate an **ERD**
📘 Create a **README.md**
🔧 Or turn this into a **developer onboarding document**

Just tell me!

