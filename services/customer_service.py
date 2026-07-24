"""
Enercore AI Solar Proposal Generator
services/customer_service.py

Service layer for client/customer data, backed by database connection.
"""

from __future__ import annotations
import sqlite3
from typing import Optional, List, Dict, Any
from database.connection import get_connection
from services.dashboard_service import _format_value_display


def list_customers(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return customers matching the given filters directly from the database."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    results = []

    try:
        cur = conn.cursor()
        where_clauses = []
        params = []

        if search and search.strip():
            q = f"%{search.strip()}%"
            where_clauses.append("(name LIKE ? OR contact LIKE ? OR segment LIKE ?)" if is_sqlite else "(name ILIKE %s OR contact ILIKE %s OR segment ILIKE %s)")
            params.extend([q, q, q])

        if category and category != "All Segments" and category.lower() != "all":
            where_clauses.append("category = ?" if is_sqlite else "category = %s")
            params.append(category)

        if status and status != "All Statuses" and status.lower() != "all":
            where_clauses.append("status = ?" if is_sqlite else "status = %s")
            params.append(status)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        query = f"SELECT * FROM customers{where_sql} ORDER BY created_at DESC;"

        cur.execute(query, params)
        rows = cur.fetchall()

        for r in rows:
            val_num = r["value_numeric"] or 0
            results.append({
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "segment": r["segment"] or f"{r['category']} · {r['capacity_mw']}MW",
                "value": _format_value_display(val_num),
                "value_numeric": val_num,
                "status": r["status"],
                "tone": r["tone"] or "neutral",
                "contact": r["contact"] or "",
                "phone": r["phone"] or "",
                "updated": r["updated_at"] or "",
            })
        return results
    except Exception as e:
        print(f"Error listing customers: {e}")
        return []
    finally:
        conn.close()


def get_customer(customer_id: str) -> Optional[Dict[str, Any]]:
    """Return a single customer record by id, or None if not found."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM customers WHERE id = ?;" if is_sqlite else "SELECT * FROM customers WHERE id = %s;",
            (customer_id,)
        )
        r = cur.fetchone()
        if not r:
            return None

        val_num = r["value_numeric"] or 0
        return {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "segment": r["segment"],
            "value": _format_value_display(val_num),
            "value_numeric": val_num,
            "status": r["status"],
            "tone": r["tone"] or "neutral",
            "contact": r["contact"] or "",
            "phone": r["phone"] or "",
            "updated": r["updated_at"] or "",
        }
    except Exception as e:
        print(f"Error fetching customer {customer_id}: {e}")
        return None
    finally:
        conn.close()


def get_customer_kpis() -> Dict[str, Any]:
    """Return top-level KPI snapshot for the Clients page."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM customers;")
        total_clients = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM customers WHERE status = 'Contract Signed';" if is_sqlite
            else "SELECT COUNT(*) FROM customers WHERE status = 'Contract Signed';"
        )
        active_contracts = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(value_numeric), 0) FROM customers;")
        sum_row = cur.fetchone()
        total_val = float(sum_row[0]) if is_sqlite else float(sum_row['coalesce'] if isinstance(sum_row, dict) else sum_row[0])

        avg_val = (total_val / total_clients) if total_clients > 0 else 0

        return {
            "total_clients": total_clients,
            "total_clients_delta": "+9 this month",
            "active_contracts": active_contracts,
            "active_contracts_delta": "Stable",
            "total_contract_value": _format_value_display(total_val),
            "total_contract_value_delta": "+6.2%",
            "avg_deal_size": _format_value_display(avg_val),
            "avg_deal_size_delta": "Stable",
        }
    except Exception as e:
        print(f"Error fetching customer KPIs: {e}")
        return {
            "total_clients": 0,
            "total_clients_delta": "Stable",
            "active_contracts": 0,
            "active_contracts_delta": "Stable",
            "total_contract_value": "$0",
            "total_contract_value_delta": "Stable",
            "avg_deal_size": "$0",
            "avg_deal_size_delta": "Stable",
        }
    finally:
        conn.close()


def create_customer(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new customer record in database."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM customers;")
        cnt = cur.fetchone()[0]
        new_id = f"cus_{1000 + cnt + 1}"

        name = data.get("name", "Unnamed Client")
        category = data.get("category", "Commercial")
        segment = data.get("segment") or f"{category} · {data.get('capacity_mw', 0.5)}MW"
        contact = data.get("contact", "")
        phone = data.get("phone", "")
        status = data.get("status", "New Lead")
        tone = data.get("tone", "neutral")
        value_numeric = float(data.get("value_numeric", 0))
        capacity_mw = float(data.get("capacity_mw", 0.5))
        updated_at = data.get("updated", "Just now")

        query = """
            INSERT INTO customers (id, name, category, segment, contact, phone, status, tone, value_numeric, capacity_mw, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO customers (id, name, category, segment, contact, phone, status, tone, value_numeric, capacity_mw, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """

        cur.execute(query, (new_id, name, category, segment, contact, phone, status, tone, value_numeric, capacity_mw, updated_at))
        conn.commit()

        return {
            "id": new_id,
            "name": name,
            "category": category,
            "segment": segment,
            "value": _format_value_display(value_numeric),
            "value_numeric": value_numeric,
            "status": status,
            "tone": tone,
            "contact": contact,
            "phone": phone,
            "updated": updated_at,
        }
    except Exception as e:
        print(f"Error creating customer: {e}")
        return data
    finally:
        conn.close()


def update_customer_status(customer_id: str, new_status: str) -> Optional[Dict[str, Any]]:
    """Update a customer's pipeline status in database."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        tone_map = {
            "Proposal Sent": "warning",
            "Analysis Phase": "info",
            "Contract Signed": "success",
            "New Lead": "neutral",
        }
        tone = tone_map.get(new_status, "neutral")

        query = """
            UPDATE customers SET status = ?, tone = ?, updated_at = 'Just now' WHERE id = ?;
        """ if is_sqlite else """
            UPDATE customers SET status = %s, tone = %s, updated_at = 'Just now' WHERE id = %s;
        """
        cur.execute(query, (new_status, tone, customer_id))
        conn.commit()
        return get_customer(customer_id)
    except Exception as e:
        print(f"Error updating customer status: {e}")
        return None
    finally:
        conn.close()