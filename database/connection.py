import os
import sqlite3
import psycopg2
import psycopg2.extras
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DB_FILE = Path(__file__).parent / "enercore.db"


def get_connection():
    """Return a database connection. Tries PostgreSQL first if credentials are set,
    falling back to local SQLite.
    """
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_port = os.getenv("DB_PORT", "5432")

    if db_host and db_name and db_user and db_password:
        try:
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                connect_timeout=3
            )
            return conn
        except Exception as e:
            print(f"⚠️ PostgreSQL Connection warning: {e}. Falling back to local SQLite.")

    conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
    # Enable foreign keys on SQLite connection
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(seed_demo: bool = False):
    """Initialize database schema tables cleanly. Demo data is only seeded if seed_demo=True."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)

    try:
        cur = conn.cursor()

        if is_sqlite:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT DEFAULT 'Sales Engineer',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Seed default admin user
            cur.execute("SELECT COUNT(*) FROM users;")
            if cur.fetchone()[0] == 0:
                import bcrypt
                hashed_pw = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
                cur.execute("""
                    INSERT INTO users (full_name, email, password, role)
                    VALUES (?, ?, ?, ?);
                """, ("Admin User", "admin@enercore.com", hashed_pw, "Sales Engineer"))

            cur.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    segment TEXT,
                    contact TEXT,
                    phone TEXT,
                    status TEXT NOT NULL,
                    tone TEXT DEFAULT 'neutral',
                    value_numeric REAL DEFAULT 0,
                    capacity_mw REAL DEFAULT 0,
                    email TEXT,
                    address TEXT,
                    gstin TEXT,
                    is_deleted INTEGER DEFAULT 0,
                    updated_at TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Idempotent SQLite migrations check
            cur.execute("PRAGMA table_info(customers);")
            existing_cols = [row[1] for row in cur.fetchall()]
            if 'email' not in existing_cols:
                cur.execute("ALTER TABLE customers ADD COLUMN email TEXT;")
            if 'address' not in existing_cols:
                cur.execute("ALTER TABLE customers ADD COLUMN address TEXT;")
            if 'gstin' not in existing_cols:
                cur.execute("ALTER TABLE customers ADD COLUMN gstin TEXT;")
            if 'is_deleted' not in existing_cols:
                cur.execute("ALTER TABLE customers ADD COLUMN is_deleted INTEGER DEFAULT 0;")

            cur.execute("DROP TABLE IF EXISTS site_activities;")
            cur.execute("DROP TABLE IF EXISTS sites;")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS sites (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    address_street TEXT,
                    address_city TEXT,
                    address_state TEXT,
                    address_zip TEXT,
                    contact_person TEXT,
                    contact_number TEXT,
                    status TEXT DEFAULT 'New',
                    is_archived INTEGER DEFAULT 0,
                    is_deleted INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                    UNIQUE(customer_id, name)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS site_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    description TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
                );
            """)

            cur.execute("DROP TABLE IF EXISTS project_documents;")
            cur.execute("DROP TABLE IF EXISTS project_activities;")
            cur.execute("DROP TABLE IF EXISTS projects;")
            cur.execute("DROP TABLE IF EXISTS ocr_results;")
            cur.execute("DROP TABLE IF EXISTS electricity_bills;")
            cur.execute("DROP TABLE IF EXISTS proposal_versions;")
            cur.execute("DROP TABLE IF EXISTS proposals;")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS electricity_bills (
                    id TEXT PRIMARY KEY,
                    site_id TEXT NOT NULL,
                    billing_month INTEGER NOT NULL,
                    billing_year INTEGER NOT NULL,
                    billing_period_start TEXT,
                    billing_period_end TEXT,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    original_filename TEXT,
                    stored_filename TEXT,
                    file_path TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    bill_status TEXT DEFAULT 'Uploaded',
                    ocr_status TEXT DEFAULT 'Not Started',
                    ocr_started_at TIMESTAMP,
                    ocr_completed_at TIMESTAMP,
                    latest_ocr_result_id INTEGER,
                    latest_calculation_id INTEGER,
                    notes TEXT,
                    is_deleted INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
                    UNIQUE(site_id, billing_month, billing_year)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ocr_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id TEXT NOT NULL,
                    raw_response TEXT,
                    normalized_json TEXT,
                    ocr_provider TEXT,
                    ocr_version TEXT,
                    ocr_confidence REAL,
                    duration_ms INTEGER,
                    warnings TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bill_id) REFERENCES electricity_bills(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS calculation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id TEXT NOT NULL,
                    plant_size_kw REAL,
                    recommended_inverter_kw REAL,
                    estimated_monthly_generation REAL,
                    estimated_annual_generation REAL,
                    monthly_savings REAL,
                    annual_savings REAL,
                    system_cost REAL,
                    payback_years REAL,
                    co2_offset REAL,
                    trees_equivalent REAL,
                    calculation_version TEXT DEFAULT '1.0',
                    calculation_status TEXT,
                    warnings TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bill_id) REFERENCES electricity_bills(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS proposals (
                    id TEXT PRIMARY KEY,
                    proposal_number TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    site_id TEXT,
                    bill_id TEXT,
                    calculation_id INTEGER,
                    proposal_name TEXT,
                    version INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'Draft',
                    plant_size_kw REAL,
                    recommended_inverter_kw REAL,
                    annual_generation REAL,
                    annual_savings REAL,
                    system_cost REAL,
                    payback_years REAL,
                    prepared_by TEXT,
                    prepared_date TEXT,
                    remarks TEXT,
                    is_active INTEGER DEFAULT 1,
                    pdf_filename TEXT,
                    pdf_path TEXT,
                    pdf_generated_at TIMESTAMP,
                    pdf_generated_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE SET NULL,
                    FOREIGN KEY (bill_id) REFERENCES electricity_bills(id) ON DELETE SET NULL,
                    FOREIGN KEY (calculation_id) REFERENCES calculation_results(id) ON DELETE SET NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    project_number TEXT NOT NULL UNIQUE,
                    proposal_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    site_id TEXT,
                    project_name TEXT NOT NULL,
                    status TEXT DEFAULT 'Planning',
                    execution_model TEXT DEFAULT 'EPC',
                    capacity_kw REAL DEFAULT 0,
                    contract_value REAL DEFAULT 0,
                    project_manager TEXT,
                    start_date TEXT,
                    expected_completion TEXT,
                    actual_completion TEXT,
                    progress_percentage REAL DEFAULT 0,
                    remarks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE RESTRICT,
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE SET NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS project_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    description TEXT,
                    created_by TEXT DEFAULT 'System',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS project_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    stored_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    uploaded_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS site_surveys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id TEXT NOT NULL,
                    surveyor_name TEXT,
                    survey_date TEXT,
                    roof_type TEXT,
                    shading_factor REAL DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS engineering_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT NOT NULL,
                    tilt_degrees REAL DEFAULT 0,
                    azimuth_degrees REAL DEFAULT 0,
                    inverter_location TEXT,
                    grid_coupling TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS bill_of_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    quantity INTEGER DEFAULT 0,
                    unit_price REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    associated_type TEXT NOT NULL,
                    associated_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    category TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS accepted_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT UNIQUE NOT NULL,
                    contract_date TEXT,
                    target_commission_date TEXT,
                    assigned_pm_id INTEGER,
                    status TEXT DEFAULT 'Design',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS followups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    due_when TEXT NOT NULL,
                    title TEXT NOT NULL,
                    note TEXT,
                    icon TEXT DEFAULT 'call',
                    tone TEXT DEFAULT 'primary',
                    due_order INTEGER DEFAULT 1
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_monthly (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month_name TEXT NOT NULL,
                    month_order INTEGER NOT NULL,
                    residential_mw REAL DEFAULT 0,
                    commercial_mw REAL DEFAULT 0
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_deals (
                    id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    value_numeric REAL DEFAULT 0,
                    stage TEXT NOT NULL,
                    contact_person TEXT,
                    time_ago TEXT DEFAULT 'Just now',
                    avatar_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create indexes on foreign keys and search fields to optimize query execution
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sites_customer_id ON sites (customer_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_site_activities_site_id ON site_activities (site_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_site_id ON electricity_bills (site_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ocr_bill_id ON ocr_results (bill_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_proposals_customer_id ON proposals (customer_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_proposals_site_id ON proposals (site_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_site_surveys_site_id ON site_surveys (site_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_engineering_details_proposal_id ON engineering_details (proposal_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bill_of_materials_proposal_id ON bill_of_materials (proposal_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_accepted_projects_proposal_id ON accepted_projects (proposal_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_customers_status ON customers (status);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_deals_stage ON pipeline_deals (stage);")

            # Seed system_settings if empty
            settings_defaults = [
                ("peak_sun_hours", "4.5", "Peak Sun Hours per day (hours)"),
                ("performance_ratio", "0.75", "Performance Ratio of solar system (0.0 to 1.0)"),
                ("panel_degradation", "0.007", "Annual Panel Degradation factor (0.0 to 1.0)"),
                ("inverter_efficiency", "0.97", "Inverter Efficiency factor (0.0 to 1.0)"),
                ("system_loss", "0.14", "System Loss percentage (0.0 to 1.0)"),
                ("electricity_tariff", "8.0", "Electricity tariff rate per kWh"),
                ("annual_tariff_escalation", "0.05", "Annual electricity tariff escalation rate (0.0 to 1.0)"),
                ("installation_cost_per_kw", "50000.0", "Solar installation cost per kW"),
                ("co2_conversion_factor", "0.82", "CO2 offset conversion factor (kg CO2 per kWh)"),
                ("tree_conversion_factor", "0.04", "Tree equivalent conversion factor (trees per kg CO2)")
            ]
            cur.execute("SELECT COUNT(*) FROM system_settings;")
            sett_count = cur.fetchone()[0]
            if sett_count == 0:
                for s in settings_defaults:
                    cur.execute("""
                        INSERT INTO system_settings (key, value, description)
                        VALUES (?, ?, ?);
                    """, s)

            cur.execute("SELECT COUNT(*) FROM customers;")
            row_count = cur.fetchone()[0]

            if row_count == 0 and seed_demo:
                seed_data(cur)

            conn.commit()

        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role VARCHAR(50) DEFAULT 'Sales Engineer',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("SELECT COUNT(*) FROM users;")
            row = cur.fetchone()
            user_cnt = row['count'] if isinstance(row, dict) else row[0]
            if user_cnt == 0:
                import bcrypt
                hashed_pw = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
                cur.execute("""
                    INSERT INTO users (full_name, email, password, role)
                    VALUES (%s, %s, %s, %s);
                """, ("Admin User", "admin@enercore.com", hashed_pw, "Sales Engineer"))
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    segment VARCHAR(255),
                    contact VARCHAR(255),
                    phone VARCHAR(50),
                    status VARCHAR(100) NOT NULL,
                    tone VARCHAR(50) DEFAULT 'neutral',
                    value_numeric NUMERIC DEFAULT 0,
                    capacity_mw NUMERIC DEFAULT 0,
                    email VARCHAR(255),
                    address TEXT,
                    gstin VARCHAR(100),
                    is_deleted INTEGER DEFAULT 0,
                    updated_at VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Idempotent PostgreSQL migrations check
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'customers';
            """)
            existing_cols = [row[0] if isinstance(row, dict) else row[0] for row in cur.fetchall()]
            if 'email' not in existing_cols:
                cur.execute("ALTER TABLE customers ADD COLUMN email VARCHAR(255);")
            if 'address' not in existing_cols:
                cur.execute("ALTER TABLE customers ADD COLUMN address TEXT;")
            if 'gstin' not in existing_cols:
                cur.execute("ALTER TABLE customers ADD COLUMN gstin VARCHAR(100);")
            if 'is_deleted' not in existing_cols:
                cur.execute("ALTER TABLE customers ADD COLUMN is_deleted INTEGER DEFAULT 0;")

            cur.execute("""
                DROP TABLE IF EXISTS site_activities CASCADE;
                DROP TABLE IF EXISTS sites CASCADE;

                CREATE TABLE IF NOT EXISTS sites (
                    id VARCHAR(50) PRIMARY KEY,
                    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    address_street VARCHAR(255),
                    address_city VARCHAR(255),
                    address_state VARCHAR(255),
                    address_zip VARCHAR(50),
                    contact_person VARCHAR(255),
                    contact_number VARCHAR(50),
                    status VARCHAR(100) DEFAULT 'New',
                    is_archived INTEGER DEFAULT 0,
                    is_deleted INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(customer_id, name)
                );

                CREATE TABLE IF NOT EXISTS site_activities (
                    id SERIAL PRIMARY KEY,
                    site_id VARCHAR(50) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
                    activity_type VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_by VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                DROP TABLE IF EXISTS ocr_results CASCADE;
                DROP TABLE IF EXISTS electricity_bills CASCADE;
                DROP TABLE IF EXISTS calculation_results CASCADE;
                DROP TABLE IF EXISTS system_settings CASCADE;
                DROP TABLE IF EXISTS proposal_versions CASCADE;
                DROP TABLE IF EXISTS proposals CASCADE;

                CREATE TABLE IF NOT EXISTS electricity_bills (
                    id VARCHAR(50) PRIMARY KEY,
                    site_id VARCHAR(50) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
                    billing_month INTEGER NOT NULL,
                    billing_year INTEGER NOT NULL,
                    billing_period_start VARCHAR(100),
                    billing_period_end VARCHAR(100),
                    upload_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    original_filename VARCHAR(255),
                    stored_filename VARCHAR(255),
                    file_path TEXT,
                    file_type VARCHAR(50),
                    file_size INTEGER,
                    bill_status VARCHAR(100) DEFAULT 'Uploaded',
                    ocr_status VARCHAR(100) DEFAULT 'Not Started',
                    ocr_started_at TIMESTAMP WITH TIME ZONE,
                    ocr_completed_at TIMESTAMP WITH TIME ZONE,
                    latest_ocr_result_id INTEGER,
                    latest_calculation_id INTEGER,
                    notes TEXT,
                    is_deleted INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(site_id, billing_month, billing_year)
                );

                CREATE TABLE IF NOT EXISTS ocr_results (
                    id SERIAL PRIMARY KEY,
                    bill_id VARCHAR(50) NOT NULL REFERENCES electricity_bills(id) ON DELETE CASCADE,
                    raw_response TEXT,
                    normalized_json TEXT,
                    ocr_provider VARCHAR(255),
                    ocr_version VARCHAR(255),
                    ocr_confidence NUMERIC,
                    duration_ms INTEGER,
                    warnings TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS system_settings (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT
                );

                CREATE TABLE IF NOT EXISTS calculation_results (
                    id SERIAL PRIMARY KEY,
                    bill_id VARCHAR(50) NOT NULL REFERENCES electricity_bills(id) ON DELETE CASCADE,
                    plant_size_kw NUMERIC,
                    recommended_inverter_kw NUMERIC,
                    estimated_monthly_generation NUMERIC,
                    estimated_annual_generation NUMERIC,
                    monthly_savings NUMERIC,
                    annual_savings NUMERIC,
                    system_cost NUMERIC,
                    payback_years NUMERIC,
                    co2_offset NUMERIC,
                    trees_equivalent NUMERIC,
                    calculation_version VARCHAR(50) DEFAULT '1.0',
                    calculation_status VARCHAR(100),
                    warnings TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS proposals (
                    id VARCHAR(50) PRIMARY KEY,
                    proposal_number VARCHAR(100) NOT NULL,
                    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                    site_id VARCHAR(50) REFERENCES sites(id) ON DELETE SET NULL,
                    bill_id VARCHAR(50) REFERENCES electricity_bills(id) ON DELETE SET NULL,
                    calculation_id INTEGER REFERENCES calculation_results(id) ON DELETE SET NULL,
                    proposal_name VARCHAR(255),
                    version INTEGER DEFAULT 1,
                    status VARCHAR(50) DEFAULT 'Draft',
                    plant_size_kw NUMERIC,
                    recommended_inverter_kw NUMERIC,
                    annual_generation NUMERIC,
                    annual_savings NUMERIC,
                    system_cost NUMERIC,
                    payback_years NUMERIC,
                    prepared_by VARCHAR(255),
                    prepared_date VARCHAR(100),
                    remarks TEXT,
                    is_active INTEGER DEFAULT 1,
                    pdf_filename VARCHAR(255),
                    pdf_path TEXT,
                    pdf_generated_at TIMESTAMP WITH TIME ZONE,
                    pdf_generated_by VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id VARCHAR(50) PRIMARY KEY,
                    project_number VARCHAR(100) NOT NULL UNIQUE,
                    proposal_id VARCHAR(50) NOT NULL REFERENCES proposals(id) ON DELETE RESTRICT,
                    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                    site_id VARCHAR(50) REFERENCES sites(id) ON DELETE SET NULL,
                    project_name VARCHAR(255) NOT NULL,
                    status VARCHAR(50) DEFAULT 'Planning',
                    execution_model VARCHAR(50) DEFAULT 'EPC',
                    capacity_kw NUMERIC DEFAULT 0,
                    contract_value NUMERIC DEFAULT 0,
                    project_manager VARCHAR(255),
                    start_date VARCHAR(100),
                    expected_completion VARCHAR(100),
                    actual_completion VARCHAR(100),
                    progress_percentage NUMERIC DEFAULT 0,
                    remarks TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS project_activities (
                    id SERIAL PRIMARY KEY,
                    project_id VARCHAR(50) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    activity_type VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_by VARCHAR(255) DEFAULT 'System',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS project_documents (
                    id SERIAL PRIMARY KEY,
                    project_id VARCHAR(50) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    document_type VARCHAR(100) NOT NULL,
                    original_filename VARCHAR(255) NOT NULL,
                    stored_filename VARCHAR(255) NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    uploaded_by VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS site_surveys (
                    id SERIAL PRIMARY KEY,
                    site_id VARCHAR(50) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
                    surveyor_name VARCHAR(255),
                    survey_date VARCHAR(100),
                    roof_type VARCHAR(100),
                    shading_factor NUMERIC DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS engineering_details (
                    id SERIAL PRIMARY KEY,
                    proposal_id VARCHAR(50) NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
                    tilt_degrees NUMERIC DEFAULT 0,
                    azimuth_degrees NUMERIC DEFAULT 0,
                    inverter_location VARCHAR(255),
                    grid_coupling VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS bill_of_materials (
                    id SERIAL PRIMARY KEY,
                    proposal_id VARCHAR(50) NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
                    component_type VARCHAR(100) NOT NULL,
                    model_name VARCHAR(255) NOT NULL,
                    quantity INTEGER DEFAULT 0,
                    unit_price NUMERIC DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    associated_type VARCHAR(100) NOT NULL,
                    associated_id VARCHAR(100) NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    file_path TEXT NOT NULL,
                    category VARCHAR(100),
                    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS accepted_projects (
                    id SERIAL PRIMARY KEY,
                    proposal_id VARCHAR(50) UNIQUE NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
                    contract_date VARCHAR(100),
                    target_commission_date VARCHAR(100),
                    assigned_pm_id INTEGER,
                    status VARCHAR(100) DEFAULT 'Design',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS followups (
                    id SERIAL PRIMARY KEY,
                    due_when VARCHAR(100) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    note TEXT,
                    icon VARCHAR(50) DEFAULT 'call',
                    tone VARCHAR(50) DEFAULT 'primary',
                    due_order INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS pipeline_monthly (
                    id SERIAL PRIMARY KEY,
                    month_name VARCHAR(20) NOT NULL,
                    month_order INTEGER NOT NULL,
                    residential_mw NUMERIC DEFAULT 0,
                    commercial_mw NUMERIC DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS pipeline_deals (
                    id VARCHAR(50) PRIMARY KEY,
                    company_name VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    value_numeric NUMERIC DEFAULT 0,
                    stage VARCHAR(100) NOT NULL,
                    contact_person VARCHAR(255),
                    time_ago VARCHAR(100) DEFAULT 'Just now',
                    avatar_url TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create indexes on foreign keys and search fields in PostgreSQL
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sites_customer_id ON sites (customer_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_site_activities_site_id ON site_activities (site_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_site_id ON electricity_bills (site_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ocr_bill_id ON ocr_results (bill_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_proposals_customer_id ON proposals (customer_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_proposals_site_id ON proposals (site_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_site_surveys_site_id ON site_surveys (site_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_engineering_details_proposal_id ON engineering_details (proposal_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bill_of_materials_proposal_id ON bill_of_materials (proposal_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_accepted_projects_proposal_id ON accepted_projects (proposal_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_customers_status ON customers (status);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_deals_stage ON pipeline_deals (stage);")

            # Seed system_settings if empty
            settings_defaults = [
                ("peak_sun_hours", "4.5", "Peak Sun Hours per day (hours)"),
                ("performance_ratio", "0.75", "Performance Ratio of solar system (0.0 to 1.0)"),
                ("panel_degradation", "0.007", "Annual Panel Degradation factor (0.0 to 1.0)"),
                ("inverter_efficiency", "0.97", "Inverter Efficiency factor (0.0 to 1.0)"),
                ("system_loss", "0.14", "System Loss percentage (0.0 to 1.0)"),
                ("electricity_tariff", "8.0", "Electricity tariff rate per kWh"),
                ("annual_tariff_escalation", "0.05", "Annual electricity tariff escalation rate (0.0 to 1.0)"),
                ("installation_cost_per_kw", "50000.0", "Solar installation cost per kW"),
                ("co2_conversion_factor", "0.82", "CO2 offset conversion factor (kg CO2 per kWh)"),
                ("tree_conversion_factor", "0.04", "Tree equivalent conversion factor (trees per kg CO2)")
            ]
            cur.execute("SELECT COUNT(*) FROM system_settings;")
            sett_count = cur.fetchone()[0]
            if sett_count == 0:
                for s in settings_defaults:
                    cur.execute("""
                        INSERT INTO system_settings (key, value, description)
                        VALUES (?, ?, ?);
                    """ if is_sqlite else """
                        INSERT INTO system_settings (key, value, description)
                        VALUES (%s, %s, %s);
                    """, s)

            cur.execute("SELECT COUNT(*) FROM customers;")
            row = cur.fetchone()
            row_count = row['count'] if isinstance(row, dict) else row[0]

            if row_count == 0 and seed_demo:
                seed_data(cur)

            conn.commit()

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
    finally:
        conn.close()


def seed_data(cur):
    """Seed initial records into customers, followups, and pipeline_monthly tables if requested."""
    customers = [
        ("cus_1001", "Client Account 1", "Commercial", "Commercial · 1.0MW", "contact1@domain.com", "+1 (555) 010-0001", "New Lead", "neutral", 1000000, 1.0, "Just now"),
    ]

    for c in customers:
        cur.execute("""
            INSERT INTO customers (id, name, category, segment, contact, phone, status, tone, value_numeric, capacity_mw, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """ if hasattr(cur, 'lastrowid') else """
            INSERT INTO customers (id, name, category, segment, contact, phone, status, tone, value_numeric, capacity_mw, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, c)


init_db(seed_demo=False)