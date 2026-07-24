"""
Enercore AI Solar Proposal Generator
services/dashboard_service.py

Service layer for executive dashboard metrics, activity feed,
follow-ups, and data exports backed by the database connection.
"""

import io
import csv
import sqlite3
from typing import Dict, List, Any, Tuple
from database.connection import get_connection


def get_dashboard_kpis(date_range: str = "30") -> List[Dict[str, Any]]:
    """Compute top-level KPI metrics dynamically from database."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM customers;")
        row = cur.fetchone()
        total_leads_val = row[0] if is_sqlite else (row['count'] if isinstance(row, dict) else row[0])

        if is_sqlite:
            cur.execute("SELECT COUNT(*) FROM customers WHERE status IN ('Proposal Sent', 'Analysis Phase');")
            row = cur.fetchone()
            active_proposals_val = row[0]
        else:
            cur.execute("SELECT COUNT(*) FROM customers WHERE status IN ('Proposal Sent', 'Analysis Phase');")
            row = cur.fetchone()
            active_proposals_val = row[0] if is_sqlite else (row['count'] if isinstance(row, dict) else row[0])

        if total_leads_val > 0:
            if is_sqlite:
                cur.execute("SELECT COUNT(*) FROM customers WHERE status = 'Contract Signed';")
                signed_val = cur.fetchone()[0]
            else:
                cur.execute("SELECT COUNT(*) FROM customers WHERE status = 'Contract Signed';")
                row = cur.fetchone()
                signed_val = row[0] if is_sqlite else (row['count'] if isinstance(row, dict) else row[0])
            conversion_rate_val = round((signed_val / total_leads_val) * 100)
        else:
            conversion_rate_val = 0

        if is_sqlite:
            cur.execute("SELECT COALESCE(SUM(capacity_mw), 0) FROM customers;")
            capacity_val = round(cur.fetchone()[0], 1)
        else:
            cur.execute("SELECT COALESCE(SUM(capacity_mw), 0) FROM customers;")
            row = cur.fetchone()
            capacity_val = round(float(row[0] if is_sqlite else (row['sum'] if isinstance(row, dict) else row[0])), 1)

        return [
            {
                "label": "Total Leads",
                "value": f"{total_leads_val:,}",
                "delta": "+0%",
                "tone": "up" if total_leads_val > 0 else "neutral",
                "icon": "leaderboard",
            },
            {
                "label": "Active Proposals",
                "value": f"{active_proposals_val:,}",
                "delta": "Live",
                "tone": "neutral",
                "icon": "description",
            },
            {
                "label": "Conversion Rate",
                "value": f"{conversion_rate_val}%",
                "delta": "Live",
                "tone": "neutral",
                "icon": "analytics",
            },
            {
                "label": "Proposed Capacity",
                "value": f"{capacity_val} MW",
                "delta": "+0 MW",
                "tone": "up" if capacity_val > 0 else "neutral",
                "icon": "solar_power",
            },
        ]
    except Exception as e:
        print(f"Error fetching dashboard KPIs: {e}")
        return [
            {"label": "Total Leads", "value": "0", "delta": "+0%", "tone": "neutral", "icon": "leaderboard"},
            {"label": "Active Proposals", "value": "0", "delta": "Live", "tone": "neutral", "icon": "description"},
            {"label": "Conversion Rate", "value": "0%", "delta": "Live", "tone": "neutral", "icon": "analytics"},
            {"label": "Proposed Capacity", "value": "0.0 MW", "delta": "+0 MW", "tone": "neutral", "icon": "solar_power"},
        ]
    finally:
        conn.close()


def get_pipeline_chart_data() -> Dict[str, List[Any]]:
    """Return pipeline chart monthly values."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    months = []
    residential = []
    commercial = []

    try:
        cur = conn.cursor()
        cur.execute("SELECT month_name, residential_mw, commercial_mw FROM pipeline_monthly ORDER BY month_order ASC;")
        rows = cur.fetchall()

        for r in rows:
            if is_sqlite:
                months.append(r["month_name"])
                residential.append(r["residential_mw"])
                commercial.append(r["commercial_mw"])
            else:
                months.append(r["month_name"])
                residential.append(float(r["residential_mw"]))
                commercial.append(float(r["commercial_mw"]))

        if not months:
            months = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"]
            residential = [0, 0, 0, 0, 0, 0]
            commercial = [0, 0, 0, 0, 0, 0]

        return {
            "months": months,
            "residential": residential,
            "commercial": commercial,
        }
    except Exception as e:
        print(f"Error fetching pipeline chart data: {e}")
        return {
            "months": ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"],
            "residential": [0, 0, 0, 0, 0, 0],
            "commercial": [0, 0, 0, 0, 0, 0],
        }
    finally:
        conn.close()


def get_followups() -> List[Dict[str, Any]]:
    """Return list of follow-up reminder items."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    result = []

    try:
        cur = conn.cursor()
        cur.execute("SELECT due_when, title, note, icon, tone FROM followups ORDER BY due_order ASC;")
        rows = cur.fetchall()

        for r in rows:
            result.append({
                "when": r["due_when"],
                "title": r["title"],
                "note": r["note"],
                "icon": r["icon"],
                "tone": r["tone"],
            })
        return result
    except Exception as e:
        print(f"Error fetching followups: {e}")
        return []
    finally:
        conn.close()


def _format_value_display(val: float) -> str:
    """Format numeric value into compact currency string ($2.4M, $850k, etc.)."""
    if val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M".replace(".0M", "M")
    elif val >= 1_000:
        return f"${val / 1_000:.0f}k"
    else:
        return f"${val:,.0f}"


def get_recent_activity(
    search: str = "",
    category: str = "",
    status: str = "",
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    page: int = 1,
    per_page: int = 5
) -> Tuple[List[Dict[str, Any]], int]:
    """Fetch paginated, filtered, sorted recent client activity from database."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    items = []
    total_count = 0

    try:
        cur = conn.cursor()

        where_clauses = []
        params = []

        if search and search.strip():
            q = f"%{search.strip()}%"
            where_clauses.append("(name LIKE ? OR contact LIKE ? OR segment LIKE ?)" if is_sqlite else "(name ILIKE %s OR contact ILIKE %s OR segment ILIKE %s)")
            params.extend([q, q, q])

        if category and category.lower() != "all":
            where_clauses.append("category = ?" if is_sqlite else "category = %s")
            params.append(category)

        if status and status.lower() != "all":
            where_clauses.append("status = ?" if is_sqlite else "status = %s")
            params.append(status)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Security Whitelist: Map parameter keys strictly to hardcoded column identifiers
        valid_sorts = {
            "name": "name",
            "updated_at": "updated_at",
            "status": "status",
            "value": "value_numeric",
        }
        # Whitelisting prevents dynamic query injection since sort_column is verified against standard fields
        sort_column = valid_sorts.get(sort_by.lower(), "updated_at")
        # Strict fallback to ASC or DESC blocks direction injection vectors
        direction = "ASC" if sort_order.lower() == "asc" else "DESC"

        count_sql = f"SELECT COUNT(*) FROM customers{where_sql};"
        cur.execute(count_sql, params)
        count_row = cur.fetchone()
        total_count = count_row[0] if is_sqlite else (count_row['count'] if isinstance(count_row, dict) else count_row[0])

        offset = (page - 1) * per_page
        query_sql = f"""
            SELECT id, name, category, segment, status, tone, value_numeric, capacity_mw, updated_at
            FROM customers
            {where_sql}
            ORDER BY {sort_column} {direction}
            LIMIT {per_page} OFFSET {offset};
        """
        cur.execute(query_sql, params)
        rows = cur.fetchall()

        for r in rows:
            val_num = r["value_numeric"] or 0
            parts = (r["name"] or "CL").split()
            initials = (parts[0][0] + parts[1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()

            items.append({
                "id": r["id"],
                "name": r["name"],
                "initials": initials,
                "category": r["category"],
                "segment": r["segment"] or f"{r['category']} · {r['capacity_mw']}MW",
                "updated_at": r["updated_at"],
                "status": r["status"],
                "tone": r["tone"] or "neutral",
                "value_numeric": val_num,
                "value_formatted": _format_value_display(val_num),
            })

        return items, total_count
    except Exception as e:
        print(f"Error fetching recent activity: {e}")
        return [], 0
    finally:
        conn.close()


def export_recent_activity_csv(search: str = "", category: str = "", status: str = "") -> str:
    """Generate CSV string of customer activity for export."""
    items, _ = get_recent_activity(search=search, category=category, status=status, per_page=1000)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["ID", "Client / Company", "Category", "Segment", "Updated Date", "Project Status", "Contract Value"])

    for item in items:
        writer.writerow([
            item["id"],
            item["name"],
            item["category"],
            item["segment"],
            item["updated_at"],
            item["status"],
            item["value_formatted"],
        ])

    return output.getvalue()
