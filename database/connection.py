import os
import sqlite3
import psycopg2
import psycopg2.extras
import logging
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DB_FILE = Path(__file__).parent / "enercore.db"


def get_connection():
    """Return a database connection. Tries PostgreSQL first if credentials are set,
    falling back to local SQLite.
    """
    import os
    test_db = os.getenv("TEST_DB_FILE")
    if test_db:
        print(f"[db_connection] Opening connection to TEST SQLite database: {os.path.abspath(test_db)} (Process ID: {os.getpid()})")
        conn = sqlite3.connect(test_db, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_port = os.getenv("DB_PORT", "5432")

    if db_host and db_name and db_user and db_password:
        try:
            print(f"[db_connection] Opening connection to PostgreSQL database: {db_name} on {db_host}:{db_port} (Process ID: {os.getpid()})")
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

    print(f"[db_connection] Opening connection to local SQLite database: {DB_FILE.resolve()} (Process ID: {os.getpid()})")
    conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
    # Enable foreign keys on SQLite connection
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def run_migrations(conn, is_sqlite: bool, dry_run: bool = False):
    """Run non-destructive database migrations and integrity audits."""
    import datetime
    import shutil
    import uuid
    from pathlib import Path
    
    # 1. Automatic backup (SQLite only)
    db_file = Path(__file__).parent / "enercore.db"
    backup_file = None
    backup_created = False
    migration_failed = False
    
    if is_sqlite and db_file.exists():
        backup_file = db_file.with_suffix(".db.bak")
        try:
            shutil.copy2(str(db_file), str(backup_file))
            backup_created = True
            logging.info(f"[{datetime.datetime.now().isoformat()}] [migration] Backup successfully created at: {backup_file}")
        except PermissionError as pe:
            logging.warning(f"[{datetime.datetime.now().isoformat()}] [migration] Backup skipped (File locked / PermissionError: {pe}). Skipping backup and continuing startup.")
        except Exception as e:
            logging.warning(f"[{datetime.datetime.now().isoformat()}] [migration] Backup skipped (Backup failed: {e}). Skipping backup and continuing startup.")

    # Report counters
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "mode": "DRY-RUN" if dry_run else "ACTUAL",
        "customers_found": 0,
        "deals_found": 0,
        "migrated": 0,
        "created": 0,
        "skipped": 0,
        "duplicates": 0,
        "errors": 0,
        "integrity": "FAIL",
        "dashboard_kpi": "FAIL",
        "proposal_links": "FAIL",
        "project_links": "FAIL"
    }
    
    logging.info(f"[{datetime.datetime.now().isoformat()}] [migration] Database migration started. Mode: {'DRY-RUN' if dry_run else 'ACTUAL'}")

    try:
        cur = conn.cursor()
        
        # Start transaction explicitly
        if is_sqlite:
            conn.execute("BEGIN IMMEDIATE TRANSACTION;")
        else:
            conn.execute("BEGIN;")

        # Count customers initially
        cur.execute("SELECT COUNT(*) FROM customers;")
        report["customers_found"] = cur.fetchone()[0]

        # 2. Normalize ID data types to TEXT strings (Bug #3)
        # Fetch customers to inspect
        cur.execute("SELECT id FROM customers;")
        customers_to_normalize = [r[0] for r in cur.fetchall()]
        
        for old_id in customers_to_normalize:
            # If ID is purely numeric, we normalize it to 'cus_<id>' format
            if isinstance(old_id, int) or (isinstance(old_id, str) and old_id.isdigit()):
                new_id = f"cus_{old_id}"
                print(f"[migration] Normalizing customer ID: {old_id} -> {new_id}")
                
                # Update references across all tables (Customers, Proposals, Projects, Sites)
                cur.execute("UPDATE customers SET id = ? WHERE id = ?;" if is_sqlite else "UPDATE customers SET id = %s WHERE id = %s;", (new_id, old_id))
                cur.execute("UPDATE proposals SET customer_id = ? WHERE customer_id = ?;" if is_sqlite else "UPDATE proposals SET customer_id = %s WHERE customer_id = %s;", (new_id, old_id))
                cur.execute("UPDATE projects SET customer_id = ? WHERE customer_id = ?;" if is_sqlite else "UPDATE projects SET customer_id = %s WHERE customer_id = %s;", (new_id, old_id))
                cur.execute("UPDATE sites SET customer_id = ? WHERE customer_id = ?;" if is_sqlite else "UPDATE sites SET customer_id = %s WHERE customer_id = %s;", (new_id, old_id))
                
                # Update pipeline deals too if table exists and has customer_id column
                try:
                    cur.execute("UPDATE pipeline_deals SET customer_id = ? WHERE customer_id = ?;" if is_sqlite else "UPDATE pipeline_deals SET customer_id = %s WHERE customer_id = %s;", (new_id, old_id))
                except Exception:
                    pass
                    
        # Check and normalize numeric values stored as string in proposals/projects/sites as well
        cur.execute("SELECT DISTINCT customer_id FROM proposals WHERE customer_id NOT LIKE 'cus_%' AND customer_id IS NOT NULL;")
        mismatched_props = [r[0] for r in cur.fetchall()]
        for m_id in mismatched_props:
            new_id = f"cus_{m_id}"
            cur.execute("UPDATE proposals SET customer_id = ? WHERE customer_id = ?;" if is_sqlite else "UPDATE proposals SET customer_id = %s WHERE customer_id = %s;", (new_id, m_id))
            
        cur.execute("SELECT DISTINCT customer_id FROM projects WHERE customer_id NOT LIKE 'cus_%' AND customer_id IS NOT NULL;")
        mismatched_projs = [r[0] for r in cur.fetchall()]
        for m_id in mismatched_projs:
            new_id = f"cus_{m_id}"
            cur.execute("UPDATE projects SET customer_id = ? WHERE customer_id = ?;" if is_sqlite else "UPDATE projects SET customer_id = %s WHERE customer_id = %s;", (new_id, m_id))

        cur.execute("SELECT DISTINCT customer_id FROM sites WHERE customer_id NOT LIKE 'cus_%' AND customer_id IS NOT NULL;")
        mismatched_sites = [r[0] for r in cur.fetchall()]
        for m_id in mismatched_sites:
            new_id = f"cus_{m_id}"
            cur.execute("UPDATE sites SET customer_id = ? WHERE customer_id = ?;" if is_sqlite else "UPDATE sites SET customer_id = %s WHERE customer_id = %s;", (new_id, m_id))

        # 3. Handle schema migration of pipeline_deals
        has_customer_id = False
        table_exists = False
        
        if is_sqlite:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pipeline_deals';")
            table_exists = len(cur.fetchall()) > 0
            if table_exists:
                cur.execute("PRAGMA table_info(pipeline_deals);")
                cols = [row[1] for row in cur.fetchall()]
                has_customer_id = "customer_id" in cols
        else:
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pipeline_deals');")
            table_exists = cur.fetchone()[0]
            if table_exists:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'pipeline_deals';")
                cols = [r[0] if not isinstance(r, dict) else r['column_name'] for r in cur.fetchall()]
                has_customer_id = "customer_id" in cols

        # If table exists but lacks customer_id, do non-destructive rename and recreation
        if table_exists and not has_customer_id:
            print("[migration] Legacy pipeline_deals schema detected. Renaming table to pipeline_deals_old...")
            cur.execute("ALTER TABLE pipeline_deals RENAME TO pipeline_deals_old;")
            table_exists = False

        # Create the normalized table if it doesn't exist
        if not table_exists:
            print("[migration] Creating normalized pipeline_deals table...")
            if is_sqlite:
                cur.execute("""
                    CREATE TABLE pipeline_deals (
                        id TEXT PRIMARY KEY,
                        customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                        category TEXT NOT NULL,
                        value_numeric REAL DEFAULT 0,
                        stage TEXT NOT NULL,
                        contact_person TEXT,
                        is_archived INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'Active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            else:
                cur.execute("""
                    CREATE TABLE pipeline_deals (
                        id VARCHAR(50) PRIMARY KEY,
                        customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                        category VARCHAR(100) NOT NULL,
                        value_numeric NUMERIC DEFAULT 0,
                        stage VARCHAR(100) NOT NULL,
                        contact_person VARCHAR(255),
                        is_archived INTEGER DEFAULT 0,
                        status VARCHAR(50) DEFAULT 'Active',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)

        # Migrate data from pipeline_deals_old if it exists
        has_old_table = False
        if is_sqlite:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pipeline_deals_old';")
            has_old_table = len(cur.fetchall()) > 0
        else:
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pipeline_deals_old');")
            has_old_table = cur.fetchone()[0]

        if has_old_table:
            cur.execute("SELECT COUNT(*) FROM pipeline_deals_old;")
            report["deals_found"] = cur.fetchone()[0]
            
            cur.execute("SELECT id, company_name, category, value_numeric, stage, contact_person, created_at FROM pipeline_deals_old;")
            old_deals = cur.fetchall()
            for od in old_deals:
                od_id = od[0]
                company_name = od[1]
                category = od[2]
                val = od[3]
                stage = od[4]
                contact = od[5]
                created_at = od[6]
                
                # Match company_name to a customer
                cur.execute("SELECT id FROM customers WHERE LOWER(name) = LOWER(?);" if is_sqlite else "SELECT id FROM customers WHERE LOWER(name) = LOWER(%s);", (company_name,))
                c_row = cur.fetchone()
                if c_row:
                    cust_id = c_row[0]
                else:
                    # Create new backing customer if missing (to preserve historical deal data)
                    cust_id = f"cus_{uuid.uuid4().hex[:8]}"
                    cur.execute("""
                        INSERT INTO customers (id, name, category, status, is_deleted)
                        VALUES (?, ?, ?, ?, 0);
                    """ if is_sqlite else """
                        INSERT INTO customers (id, name, category, status, is_deleted)
                        VALUES (%s, %s, %s, %s, 0);
                    """, (cust_id, company_name, category, stage))
                    print(f"[migration] Created backing customer: {cust_id} ({company_name}) for legacy deal.")
                
                # Insert into new pipeline_deals table
                # Check for duplicates first
                cur.execute("SELECT COUNT(*) FROM pipeline_deals WHERE customer_id = ?;" if is_sqlite else "SELECT COUNT(*) FROM pipeline_deals WHERE customer_id = %s;", (cust_id,))
                if cur.fetchone()[0] == 0:
                    cur.execute("""
                        INSERT INTO pipeline_deals (id, customer_id, category, value_numeric, stage, contact_person, is_archived, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 0, 'Active', ?);
                    """ if is_sqlite else """
                        INSERT INTO pipeline_deals (id, customer_id, category, value_numeric, stage, contact_person, is_archived, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, 0, 'Active', %s);
                    """, (od_id, cust_id, category, val, stage, contact, created_at))
                    report["migrated"] += 1
                else:
                    report["duplicates"] += 1

        # 4. Auto-create missing deals ONLY if they meet specific criteria
        cur.execute("SELECT id, name, category, value_numeric, status, contact, is_deleted, created_at FROM customers;")
        all_customers = cur.fetchall()
        for cust in all_customers:
            c_id = cust[0]
            c_name = cust[1]
            c_cat = cust[2]
            c_val = cust[3]
            c_status = cust[4]
            c_contact = cust[5]
            c_del = cust[6]
            c_created = cust[7]
            
            # Check if active deal already exists in new table
            cur.execute("SELECT COUNT(*) FROM pipeline_deals WHERE customer_id = ?;" if is_sqlite else "SELECT COUNT(*) FROM pipeline_deals WHERE customer_id = %s;", (c_id,))
            if cur.fetchone()[0] > 0:
                continue # Already has a deal, skip to avoid duplicates!
                
            # Perform selective filters check
            # Criteria A: Has an existing proposal
            cur.execute("SELECT COUNT(*) FROM proposals WHERE customer_id = ?;" if is_sqlite else "SELECT COUNT(*) FROM proposals WHERE customer_id = %s;", (c_id,))
            has_prop = cur.fetchone()[0] > 0
            
            # Criteria B: Has an existing bill
            cur.execute("""
                SELECT COUNT(*) FROM electricity_bills b
                JOIN sites s ON b.site_id = s.id
                WHERE s.customer_id = ? AND s.is_deleted = 0;
            """ if is_sqlite else """
                SELECT COUNT(*) FROM electricity_bills b
                JOIN sites s ON b.site_id = s.id
                WHERE s.customer_id = %s AND s.is_deleted = 0;
            """, (c_id,))
            has_bill = cur.fetchone()[0] > 0
            
            # Criteria C: Has legacy pipeline history
            has_history = False
            if has_old_table:
                cur.execute("SELECT COUNT(*) FROM pipeline_deals_old WHERE LOWER(company_name) = LOWER(?);" if is_sqlite else "SELECT COUNT(*) FROM pipeline_deals_old WHERE LOWER(company_name) = LOWER(%s);", (c_name,))
                has_history = cur.fetchone()[0] > 0
                
            # Criteria D: Was visible on dashboard (active + has status)
            was_visible = (c_del == 0) and (c_status in ['New Lead', 'Proposal Sent', 'Contract Signed', 'Analysis Phase', 'Survey Scheduled', 'Survey Completed', 'Project Won', 'Project Lost', 'Completed'])
            
            # Auto-create ONLY if matches one of the criteria
            if has_prop or has_bill or has_history or was_visible:
                new_deal_id = f"deal_{c_id}"
                cur.execute("""
                    INSERT INTO pipeline_deals (id, customer_id, category, value_numeric, stage, contact_person, is_archived, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """ if is_sqlite else """
                    INSERT INTO pipeline_deals (id, customer_id, category, value_numeric, stage, contact_person, is_archived, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (new_deal_id, c_id, c_cat, c_val, c_status, c_contact, c_del, 'Archived' if c_del == 1 else 'Active', c_created))
                report["created"] += 1
            else:
                report["skipped"] += 1

        # 5. Automated Post-Migration Integrity Checks
        # Validate Customer ↔ Pipeline Deals
        cur.execute("SELECT COUNT(*) FROM pipeline_deals d LEFT JOIN customers c ON d.customer_id = c.id WHERE c.id IS NULL;")
        missing_deal_custs = cur.fetchone()[0]
        
        # Validate Customer ↔ Proposals
        cur.execute("SELECT COUNT(*) FROM proposals p LEFT JOIN customers c ON p.customer_id = c.id WHERE c.id IS NULL;")
        missing_prop_custs = cur.fetchone()[0]
        
        # Validate Customer ↔ Projects
        cur.execute("SELECT COUNT(*) FROM projects p LEFT JOIN customers c ON p.customer_id = c.id WHERE c.id IS NULL;")
        missing_proj_custs = cur.fetchone()[0]
        
        # Validate Duplicates
        cur.execute("SELECT COUNT(*) FROM (SELECT customer_id FROM pipeline_deals GROUP BY customer_id HAVING COUNT(*) > 1);")
        dup_deals_cnt = cur.fetchone()[0]
        
        # Final status determinations
        if missing_deal_custs == 0 and dup_deals_cnt == 0:
            report["integrity"] = "PASS"
            
        if missing_prop_custs == 0:
            report["proposal_links"] = "PASS"
            
        if missing_proj_custs == 0:
            report["project_links"] = "PASS"
            
        # Validate dashboard KPIs query execution
        try:
            # Check pipeline summary aggregate execution
            cur.execute("""
                SELECT 
                    COUNT(d.id),
                    COALESCE(SUM(d.value_numeric), 0)
                FROM pipeline_deals d
                JOIN customers c ON d.customer_id = c.id
                WHERE d.is_archived = 0 AND c.is_deleted = 0;
            """)
            cur.fetchone()
            report["dashboard_kpi"] = "PASS"
        except Exception as e:
            print(f"[migration] Dashboard KPI test query failed: {e}")
            report["dashboard_kpi"] = "FAIL"

        # Check for absolute failure conditions
        if report["integrity"] == "FAIL" or report["proposal_links"] == "FAIL" or report["project_links"] == "FAIL" or report["dashboard_kpi"] == "FAIL":
            raise ValueError(f"Integrity check failed! Report: {report}")

        # If it's a dry-run, we rollback the transaction!
        if dry_run:
            logging.info(f"[{datetime.datetime.now().isoformat()}] [migration] Dry-run validation passed. Rolling back transaction.")
            conn.rollback()
        else:
            logging.info(f"[{datetime.datetime.now().isoformat()}] [migration] Migration completed successfully. Committing transaction.")
            conn.commit()

        logging.info(f"[{datetime.datetime.now().isoformat()}] [migration] Database migration completed successfully.")

    except Exception as e:
        migration_failed = True
        logging.error(f"[{datetime.datetime.now().isoformat()}] [migration] Database migration failed: {e}")
        report["errors"] += 1
        try:
            conn.rollback()
            logging.info(f"[{datetime.datetime.now().isoformat()}] [migration] Transaction successfully rolled back.")
        except Exception:
            pass
            
        # Restore database from backup in case of failures (SQLite only)
        if not dry_run and migration_failed and backup_created and backup_file and backup_file.exists():
            logging.info(f"[{datetime.datetime.now().isoformat()}] [migration] Database restore executed from backup: {backup_file}")
            try:
                shutil.copy2(str(backup_file), str(db_file))
                logging.info(f"[{datetime.datetime.now().isoformat()}] [migration] Database restore completed.")
            except Exception as re_err:
                logging.error(f"[{datetime.datetime.now().isoformat()}] [migration] Critical: Failed to restore backup: {re_err}")
        else:
            logging.info(f"[{datetime.datetime.now().isoformat()}] [migration] Database restore skipped (migration_failed={migration_failed}, backup_created={backup_created})")
        raise e
    finally:
        # Write report to log file
        log_file = Path(__file__).parent / "migration_report.log"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{report['timestamp']}] MODE: {report['mode']}\n")
                f.write(f"  Customers Found     : {report['customers_found']}\n")
                f.write(f"  Pipeline Deals Found: {report['deals_found']}\n")
                f.write(f"  Migrated            : {report['migrated']}\n")
                f.write(f"  Created             : {report['created']}\n")
                f.write(f"  Skipped             : {report['skipped']}\n")
                f.write(f"  Duplicates          : {report['duplicates']}\n")
                f.write(f"  Errors              : {report['errors']}\n")
                f.write(f"  Integrity           : {report['integrity']}\n")
                f.write(f"  Dashboard KPI       : {report['dashboard_kpi']}\n")
                f.write(f"  Proposal Links      : {report['proposal_links']}\n")
                f.write(f"  Project Links       : {report['project_links']}\n")
                f.write("--------------------------------------------------\n")
            print(f"[migration] Migration report written to {log_file}")
        except Exception as log_err:
            print(f"[error] Failed to write migration report to file: {log_err}")

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
                try:
                    cur.execute("""
                        INSERT OR IGNORE INTO users (full_name, email, password, role)
                        VALUES (?, ?, ?, ?);
                    """, ("Admin User", "admin@enercore.com", hashed_pw, "Sales Engineer"))
                except sqlite3.IntegrityError:
                    pass

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
                    due_order INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("PRAGMA table_info(followups);")
            existing_followup_cols = [row[1] for row in cur.fetchall()]
            if 'created_at' not in existing_followup_cols:
                cur.execute("ALTER TABLE followups ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

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
            cur.execute("CREATE INDEX IF NOT EXISTS idx_projects_customer_id ON projects (customer_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_projects_proposal_id ON projects (proposal_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (status);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects (created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_customers_is_deleted ON customers (is_deleted);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers (created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_deals_created_at ON pipeline_deals (created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_proposals_created_at ON proposals (created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_electricity_bills_created_at ON electricity_bills (created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_followups_created_at ON followups (created_at);")

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
                try:
                    cur.execute("""
                        INSERT INTO users (full_name, email, password, role)
                        VALUES (%s, %s, %s, %s);
                    """, ("Admin User", "admin@enercore.com", hashed_pw, "Sales Engineer"))
                except Exception:
                    pass
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
                    due_order INTEGER DEFAULT 1,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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
            cur.execute("CREATE INDEX IF NOT EXISTS idx_projects_customer_id ON projects (customer_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_projects_proposal_id ON projects (proposal_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (status);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects (created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_customers_is_deleted ON customers (is_deleted);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers (created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_deals_created_at ON pipeline_deals (created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_proposals_created_at ON proposals (created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_electricity_bills_created_at ON electricity_bills (created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_followups_created_at ON followups (created_at);")

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

            if not is_sqlite:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'followups' AND column_name = 'created_at';
                """)
                if not cur.fetchone():
                    cur.execute("ALTER TABLE followups ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;")

        conn.commit()
        
        # Execute database migration and normalization audits
        run_migrations(conn, is_sqlite, dry_run=False)

    except Exception as e:
        print(f"[error] Error initializing database: {e}")
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
