"""
Database schema definitions for Finance Tracker
"""

SCHEMA = """
-- Core transaction storage
CREATE TABLE IF NOT EXISTS transactions (
    uuid TEXT PRIMARY KEY,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    
    -- Currency handling
    original_amount DECIMAL(10,2) NOT NULL,
    original_currency TEXT NOT NULL CHECK(original_currency IN ('EUR', 'USD')),
    amount_eur DECIMAL(10,2),
    amount_usd DECIMAL(10,2),
    exchange_rate DECIMAL(10,6),
    
    -- Categorization
    subcategory TEXT,
    category TEXT,
    budget_type TEXT,
    
    -- Metadata
    card_number TEXT,
    is_quorum BOOLEAN DEFAULT FALSE,
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Category definitions
CREATE SEQUENCE IF NOT EXISTS seq_categories;
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY DEFAULT NEXTVAL('seq_categories'),
    budget_type TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(budget_type, category, subcategory)
);

-- Budget templates (Single, Couples, Working Couples)
CREATE SEQUENCE IF NOT EXISTS seq_budget_templates;
CREATE TABLE IF NOT EXISTS budget_templates (
    id INTEGER PRIMARY KEY DEFAULT NEXTVAL('seq_budget_templates'),
    name TEXT NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Template category budgets
CREATE SEQUENCE IF NOT EXISTS seq_template_categories;
CREATE TABLE IF NOT EXISTS template_categories (
    id INTEGER PRIMARY KEY DEFAULT NEXTVAL('seq_template_categories'),
    template_id INTEGER NOT NULL,
    budget_type TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    budgeted_amount DECIMAL(10,2) NOT NULL,
    FOREIGN KEY(template_id) REFERENCES budget_templates(id)
);

-- Monthly budget actuals (locked after month ends)
CREATE SEQUENCE IF NOT EXISTS seq_monthly_budgets;
CREATE TABLE IF NOT EXISTS monthly_budgets (
    id INTEGER PRIMARY KEY DEFAULT NEXTVAL('seq_monthly_budgets'),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    template_id INTEGER NOT NULL,
    budget_type TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    budgeted_amount DECIMAL(10,2) NOT NULL,
    is_locked BOOLEAN DEFAULT FALSE,
    notes TEXT,
    FOREIGN KEY(template_id) REFERENCES budget_templates(id),
    UNIQUE(year, month, budget_type, category, subcategory)
);

-- Savings buckets
CREATE SEQUENCE IF NOT EXISTS seq_savings_buckets;
CREATE TABLE IF NOT EXISTS savings_buckets (
    id INTEGER PRIMARY KEY DEFAULT NEXTVAL('seq_savings_buckets'),
    name TEXT NOT NULL,
    currency TEXT NOT NULL CHECK(currency IN ('EUR', 'USD')),
    goal_amount DECIMAL(10,2) NOT NULL,
    start_amount DECIMAL(10,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    target_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Savings transactions (credits/debits to buckets)
CREATE SEQUENCE IF NOT EXISTS seq_savings_transactions;
CREATE TABLE IF NOT EXISTS savings_transactions (
    id INTEGER PRIMARY KEY DEFAULT NEXTVAL('seq_savings_transactions'),
    bucket_id INTEGER NOT NULL,
    date DATE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    transaction_type TEXT CHECK(transaction_type IN ('credit', 'debit', 'transfer')),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(bucket_id) REFERENCES savings_buckets(id)
);

-- Income sources (you + future partner)
CREATE SEQUENCE IF NOT EXISTS seq_income_streams;
CREATE TABLE IF NOT EXISTS income_streams (
    id INTEGER PRIMARY KEY DEFAULT NEXTVAL('seq_income_streams'),
    name TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    frequency TEXT DEFAULT 'monthly',
    is_active BOOLEAN DEFAULT TRUE,
    owner TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quorum reimbursements (monthly totals)
CREATE SEQUENCE IF NOT EXISTS seq_reimbursements;
CREATE TABLE IF NOT EXISTS reimbursements (
    id INTEGER PRIMARY KEY DEFAULT NEXTVAL('seq_reimbursements'),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    total_quorum_usd DECIMAL(10,2) NOT NULL,
    reimbursed_amount_usd DECIMAL(10,2) DEFAULT 0,
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
    eur_to_usd DECIMAL(10,6) NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_transactions_is_quorum ON transactions(is_quorum);
CREATE INDEX IF NOT EXISTS idx_monthly_budgets_year_month ON monthly_budgets(year, month);
CREATE INDEX IF NOT EXISTS idx_savings_transactions_bucket ON savings_transactions(bucket_id);
"""
