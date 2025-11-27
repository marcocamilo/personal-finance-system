"""
Database schema definitions for Finance Tracker (SQLite)
"""

SCHEMA = """
-- Core transaction storage
CREATE TABLE IF NOT EXISTS transactions (
    uuid TEXT PRIMARY KEY,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    
    -- Currency handling
    original_amount REAL NOT NULL,
    original_currency TEXT NOT NULL CHECK(original_currency IN ('EUR', 'USD')),
    amount_eur REAL,
    amount_usd REAL,
    exchange_rate REAL,
    
    -- Categorization
    subcategory TEXT,
    category TEXT,
    budget_type TEXT,
    
    -- Metadata
    card_number TEXT,
    is_quorum BOOLEAN DEFAULT 0,
    is_manual BOOLEAN DEFAULT 0,
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Income transactions
CREATE TABLE IF NOT EXISTS income_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount_eur REAL NOT NULL,
    income_stream_id INTEGER,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(income_stream_id) REFERENCES income_streams(id)
);

CREATE INDEX IF NOT EXISTS idx_income_transactions_date ON income_transactions(date);
CREATE INDEX IF NOT EXISTS idx_income_transactions_year_month ON income_transactions(year, month);

-- Category definitions
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    budget_type TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(budget_type, category, subcategory)
);

-- Budget templates (Single, Couples, Working Couples)
CREATE TABLE IF NOT EXISTS budget_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Template category budgets
CREATE TABLE IF NOT EXISTS template_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    budget_type TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    budgeted_amount REAL NOT NULL,
    FOREIGN KEY(template_id) REFERENCES budget_templates(id)
);

-- Monthly budget actuals (locked after month ends)
CREATE TABLE IF NOT EXISTS monthly_budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    template_id INTEGER NOT NULL,
    budget_type TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    budgeted_amount REAL NOT NULL,
    is_locked BOOLEAN DEFAULT 0,
    notes TEXT,
    FOREIGN KEY(template_id) REFERENCES budget_templates(id),
    UNIQUE(year, month, budget_type, category, subcategory)
);

-- Savings buckets
CREATE TABLE IF NOT EXISTS savings_buckets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    currency TEXT NOT NULL CHECK(currency IN ('EUR', 'USD')),
    goal_amount REAL,
    start_amount REAL DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    target_date DATE,
    is_ongoing BOOLEAN DEFAULT 0,
    is_archived BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 999,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Savings transactions (credits/debits to buckets)
CREATE TABLE IF NOT EXISTS savings_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bucket_id INTEGER NOT NULL,
    date DATE NOT NULL,
    amount REAL NOT NULL,
    transaction_type TEXT CHECK(transaction_type IN ('credit', 'debit', 'transfer')),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(bucket_id) REFERENCES savings_buckets(id)
);

-- Savings allocations (linked to budgets)
CREATE TABLE IF NOT EXISTS savings_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bucket_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    allocated_amount REAL NOT NULL,
    actual_amount REAL DEFAULT 0,
    is_allocated BOOLEAN DEFAULT 0,
    allocation_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(bucket_id) REFERENCES savings_buckets(id),
    UNIQUE(bucket_id, year, month)
);

CREATE INDEX IF NOT EXISTS idx_savings_allocations_year_month ON savings_allocations(year, month);

-- Income sources (you + future partner)
CREATE TABLE IF NOT EXISTS income_streams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    frequency TEXT DEFAULT 'monthly',
    is_active BOOLEAN DEFAULT 1,
    owner TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quorum reimbursements (monthly totals)
CREATE TABLE IF NOT EXISTS reimbursements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    total_quorum_usd REAL NOT NULL,
    reimbursed_amount_usd REAL DEFAULT 0,
    reimbursement_date DATE,
    notes TEXT,
    UNIQUE(year, month)
);

-- Merchant auto-categorization patterns
CREATE TABLE IF NOT EXISTS merchant_mapping (
    merchant_pattern TEXT PRIMARY KEY,
    subcategory TEXT NOT NULL,
    confidence INTEGER DEFAULT 1,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- App configuration (theme, settings)
CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exchange rate cache
CREATE TABLE IF NOT EXISTS exchange_rates (
    date DATE PRIMARY KEY,
    eur_to_usd REAL NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_transactions_is_quorum ON transactions(is_quorum);
CREATE INDEX IF NOT EXISTS idx_monthly_budgets_year_month ON monthly_budgets(year, month);
CREATE INDEX IF NOT EXISTS idx_savings_transactions_bucket ON savings_transactions(bucket_id);
"""
