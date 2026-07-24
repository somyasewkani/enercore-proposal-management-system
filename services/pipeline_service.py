"""
Enercore AI Solar Proposal Generator
services/pipeline_service.py

Service layer for CRM Kanban pipeline deals, stage movement, and pipeline metrics.
"""

import sqlite3
from typing import Dict, List, Any, Tuple
from database.connection import get_connection
from services.dashboard_service import _format_value_display


def init_pipeline_db(seed_demo: bool = False):
    """Ensure pipeline_deals table exists in database cleanly."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        if is_sqlite:
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

            cur.execute("SELECT COUNT(*) FROM pipeline_deals;")
            if cur.fetchone()[0] == 0 and seed_demo:
                seed_pipeline_deals(cur, is_sqlite=True)
            conn.commit()

        else:
            cur.execute("""
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
            cur.execute("SELECT COUNT(*) FROM pipeline_deals;")
            row = cur.fetchone()
            count = row[0] if is_sqlite else (row['count'] if isinstance(row, dict) else row[0])
            if count == 0 and seed_demo:
                seed_pipeline_deals(cur, is_sqlite=False)
            conn.commit()
    except Exception as e:
        print(f"Error initializing pipeline table: {e}")
    finally:
        conn.close()


def seed_pipeline_deals(cur, is_sqlite: bool):
    """Seed initial pipeline deals if explicitly requested."""
    deals = [
        ("deal_1", "Client Account 1", "COMMERCIAL", 100000, "New Lead", "Just now"),
    ]

    for d in deals:
        cur.execute("""
            INSERT INTO pipeline_deals (id, company_name, category, value_numeric, stage, time_ago)
            VALUES (?, ?, ?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO pipeline_deals (id, company_name, category, value_numeric, stage, time_ago)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, d)


def get_all_deals_by_stage() -> Dict[str, Dict[str, Any]]:
    """Return pipeline deals grouped by Kanban stage with column totals."""
    init_pipeline_db(seed_demo=False)
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)

    stages = [
        "New Lead",
        "Contacted",
        "Bill Received",
        "Analysis Completed",
        "Proposal Sent",
        "Negotiation",
        "Won",
        "Lost",
    ]

    result = {s: {"deals": [], "total_val": 0, "total_formatted": "$0", "count": 0} for s in stages}

    try:
        cur = conn.cursor()
        cur.execute("SELECT id, company_name, category, value_numeric, stage, time_ago FROM pipeline_deals ORDER BY created_at DESC;")
        rows = cur.fetchall()

        for r in rows:
            stage_name = r["stage"]
            if stage_name not in result:
                result[stage_name] = {"deals": [], "total_val": 0, "total_formatted": "$0", "count": 0}

            val = float(r["value_numeric"] or 0)
            result[stage_name]["deals"].append({
                "id": r["id"],
                "company_name": r["company_name"],
                "category": r["category"],
                "value_numeric": val,
                "value_formatted": _format_value_display(val),
                "stage": stage_name,
                "time_ago": r["time_ago"] or "Recently",
            })
            result[stage_name]["total_val"] += val
            result[stage_name]["count"] += 1

        for s in result:
            result[s]["total_formatted"] = _format_value_display(result[s]["total_val"])

        return result
    except Exception as e:
        print(f"Error fetching pipeline deals: {e}")
        return result
    finally:
        conn.close()


def get_pipeline_total_value() -> str:
    """Return total formatted value of all active pipeline deals."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(value_numeric), 0) FROM pipeline_deals WHERE stage != 'Lost';")
        r = cur.fetchone()
        tot = float(r[0]) if is_sqlite else float(r['coalesce'] if isinstance(r, dict) else r[0])
        return _format_value_display(tot)
    except Exception as e:
        print(f"Error calculating pipeline total: {e}")
        return "$0"
    finally:
        conn.close()


def create_pipeline_deal(data: Dict[str, Any]) -> bool:
    """Create a new deal in the pipeline."""
    init_pipeline_db(seed_demo=False)
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM pipeline_deals;")
        cnt = cur.fetchone()[0]
        deal_id = f"deal_{cnt + 1}"

        query = """
            INSERT INTO pipeline_deals (id, company_name, category, value_numeric, stage, time_ago)
            VALUES (?, ?, ?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO pipeline_deals (id, company_name, category, value_numeric, stage, time_ago)
            VALUES (%s, %s, %s, %s, %s, %s);
        """
        cur.execute(query, (
            deal_id,
            data.get("company_name", "New Prospect"),
            data.get("category", "COMMERCIAL").upper(),
            float(data.get("value_numeric", 100000)),
            data.get("stage", "New Lead"),
            "Just now",
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating deal: {e}")
        return False
    finally:
        conn.close()


def update_deal_stage(deal_id: str, new_stage: str) -> bool:
    """Move deal to a new pipeline stage."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = "UPDATE pipeline_deals SET stage = ? WHERE id = ?;" if is_sqlite else "UPDATE pipeline_deals SET stage = %s WHERE id = %s;"
        cur.execute(query, (new_stage, deal_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating deal stage: {e}")
        return False
    finally:
        conn.close()


def delete_pipeline_deal(deal_id: str) -> bool:
    """Delete a deal from pipeline."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = "DELETE FROM pipeline_deals WHERE id = ?;" if is_sqlite else "DELETE FROM pipeline_deals WHERE id = %s;"
        cur.execute(query, (deal_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting deal: {e}")
        return False
    finally:
        conn.close()
