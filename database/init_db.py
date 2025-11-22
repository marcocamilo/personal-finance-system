"""
Database initialization and seed data
"""
from database.db import db
from database.models import SCHEMA


def init_database():
    """Initialize database with schema"""
    print("🔧 Initializing database...")
    
    conn = db.connect()
    conn.execute(SCHEMA)
    
    print("✅ Database schema created")
    
    # Seed initial data
    seed_categories()
    seed_budget_templates()
    seed_app_config()
    
    print("✅ Database initialized successfully!")


def seed_categories():
    """Seed categories from your category mapping"""
    print("📝 Seeding categories...")
    
    categories_data = [
        # Savings
        ('Savings', 'Personal funds', 'Base fund'),
        ('Savings', 'Roth IRA', 'Roth IRA'),
        ('Savings', 'Investments', 'Brokerage account'),
        ('Savings', 'Savings goals', 'Emergency fund'),
        
        # Needs
        ('Needs', 'Rent', 'Rent'),
        ('Needs', 'Groceries & Living', 'Supermarket'),
        ('Needs', 'Groceries & Living', 'Pharmacy'),
        ('Needs', 'Groceries & Living', 'Household expenses'),
        ('Needs', 'Groceries & Living', 'Haircut'),
        ('Needs', 'Phone Bill', 'O2'),
        ('Needs', 'Taxes', 'Rundfunkbeitrag'),
        ('Needs', 'Transportation', 'D-Ticket Job'),
        ('Needs', 'Transportation', 'Transportation'),
        
        # Wants
        ('Wants', 'Shopping', 'Online Shopping'),
        ('Wants', 'Shopping', 'Clothing'),
        ('Wants', 'Shopping', 'Technology'),
        ('Wants', 'Shopping', 'Hobbies'),
        ('Wants', 'Restaurants', 'Restaurant'),
        ('Wants', 'Restaurants', 'Fast Food'),
        ('Wants', 'Restaurants', 'Take-in'),
        ('Wants', 'Restaurants', 'Work Kantina'),
        ('Wants', 'Subscriptions', 'Monthly subscriptions'),
        ('Wants', 'Subscriptions', 'Annual subscriptions'),
        ('Wants', 'Travel', 'Train ticket'),
        ('Wants', 'Travel', 'Airfare'),
        ('Wants', 'Travel', 'Transportation (travel)'),
        ('Wants', 'Travel', 'Hotel'),
        ('Wants', 'Travel', 'Car Rental'),
        ('Wants', 'Entertainment', 'Social activities'),
        ('Wants', 'Entertainment', 'Movies'),
        ('Wants', 'Entertainment', 'Amusement'),
        
        # Additional
        ('Additional', 'Quorum', 'Quorum'),
        
        # Unexpected
        ('Unexpected', 'Unexpected', 'Home repairs'),
        ('Unexpected', 'Unexpected', 'Insurance fees'),
        ('Unexpected', 'Unexpected', 'Unexpected travel'),
        ('Unexpected', 'Unexpected', 'Medical bills'),
        ('Unexpected', 'Unexpected', 'Migration fees'),
    ]
    
    conn = db.connect()
    for budget_type, category, subcategory in categories_data:
        conn.execute("""
            INSERT OR IGNORE INTO categories (budget_type, category, subcategory, is_active)
            VALUES (?, ?, ?, TRUE)
        """, (budget_type, category, subcategory))
    
    print(f"✅ Seeded {len(categories_data)} categories")


def seed_budget_templates():
    """Seed budget templates from your Budgets sheet"""
    print("📊 Seeding budget templates...")
    
    conn = db.connect()
    
    # Create templates
    templates = [
        ('Single', True),
        ('Couples', False),
        ('Working Couples', False)
    ]
    
    for name, is_active in templates:
        conn.execute("""
            INSERT OR IGNORE INTO budget_templates (name, is_active)
            VALUES (?, ?)
        """, (name, is_active))
    
    # Get template IDs
    single_id = conn.execute("SELECT id FROM budget_templates WHERE name = 'Single'").fetchone()[0]
    couples_id = conn.execute("SELECT id FROM budget_templates WHERE name = 'Couples'").fetchone()[0]
    working_id = conn.execute("SELECT id FROM budget_templates WHERE name = 'Working Couples'").fetchone()[0]
    
    # Single template (from your Budgets sheet)
    single_budgets = [
        # Income
        ('Income', 'Income', 'Salary', 2844.67),
        
        # Savings
        ('Savings', 'Savings Account', None, 1000.00),
        
        # Needs
        ('Needs', 'Rent', 'Rent', 930.00),
        ('Needs', 'Groceries & Living', 'Supermarket', 400.00),
        ('Needs', 'Phone Bill', 'O2', 20.00),
        ('Needs', 'Taxes', 'Rundfunkbeitrag', 20.00),
        ('Needs', 'Transportation', 'D-Ticket Job', 44.67),
        
        # Wants
        ('Wants', 'Shopping', None, 210.00),
        ('Wants', 'Restaurants', None, 200.00),
        ('Wants', 'Subscriptions', 'Monthly subscriptions', 40.00),
        ('Wants', 'Travel', None, 0.00),
    ]
    
    for budget_type, category, subcategory, amount in single_budgets:
        conn.execute("""
            INSERT OR IGNORE INTO template_categories 
            (template_id, budget_type, category, subcategory, budgeted_amount)
            VALUES (?, ?, ?, ?, ?)
        """, (single_id, budget_type, category, subcategory, amount))
    
    # Couples template
    couples_budgets = [
        ('Income', 'Income', 'Salary', 3450.00),
        ('Savings', 'Savings Account', None, 580.00),
        ('Needs', 'Rent', 'Rent', 930.00),
        ('Needs', 'Groceries & Living', 'Supermarket', 800.00),
        ('Needs', 'Phone Bill', 'O2', 40.00),
        ('Needs', 'Taxes', 'Rundfunkbeitrag', 20.00),
        ('Needs', 'Transportation', 'D-Ticket Job', 50.00),
        ('Wants', 'Shopping', None, 420.00),
        ('Wants', 'Restaurants', None, 400.00),
        ('Wants', 'Subscriptions', 'Monthly subscriptions', 80.00),
    ]
    
    for budget_type, category, subcategory, amount in couples_budgets:
        conn.execute("""
            INSERT OR IGNORE INTO template_categories 
            (template_id, budget_type, category, subcategory, budgeted_amount)
            VALUES (?, ?, ?, ?, ?)
        """, (couples_id, budget_type, category, subcategory, amount))
    
    # Working Couples template
    working_budgets = [
        ('Income', 'Income', 'Salary', 5200.00),
        ('Savings', 'Savings Account', None, 2380.00),
        ('Needs', 'Rent', 'Rent', 930.00),
        ('Needs', 'Groceries & Living', 'Supermarket', 800.00),
        ('Needs', 'Phone Bill', 'O2', 40.00),
        ('Needs', 'Taxes', 'Rundfunkbeitrag', 20.00),
        ('Needs', 'Transportation', 'D-Ticket Job', 50.00),
        ('Wants', 'Shopping', None, 420.00),
        ('Wants', 'Restaurants', None, 400.00),
        ('Wants', 'Subscriptions', 'Monthly subscriptions', 80.00),
    ]
    
    for budget_type, category, subcategory, amount in working_budgets:
        conn.execute("""
            INSERT OR IGNORE INTO template_categories 
            (template_id, budget_type, category, subcategory, budgeted_amount)
            VALUES (?, ?, ?, ?, ?)
        """, (working_id, budget_type, category, subcategory, amount))
    
    print("✅ Seeded 3 budget templates")


def seed_app_config():
    """Seed initial app configuration"""
    print("⚙️  Seeding app config...")
    
    config = [
        ('theme', 'light'),
        ('statement_close_day', '25'),
        ('payment_due_day', '19'),
        ('default_template', 'Single'),
    ]
    
    conn = db.connect()
    for key, value in config:
        conn.execute("""
            INSERT OR IGNORE INTO app_config (key, value)
            VALUES (?, ?)
        """, (key, value))
    
    print("✅ Seeded app configuration")


if __name__ == "__main__":
    init_database()
