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
                    updated_at TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                    updated_at VARCHAR(100),
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
            """)

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