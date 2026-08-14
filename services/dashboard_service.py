"""
Enercore AI Solar Proposal Generator
services/dashboard_service.py

Service layer for executive dashboard metrics, activity feed,
follow-ups, and data exports backed by the database connection.
"""

import io
import csv
import sqlite3
import datetime
from typing import Dict, List, Any, Tuple, Optional
from database.connection import get_connection

def normalize_date_range(range_str: str) -> str:
    """Normalize range string from query params or UI options."""
    range_str = str(range_str).strip().lower()
    if range_str in ("30", "30d"):
        return "30"
    elif range_str in ("90", "90d"):
        return "90"
    elif range_str in ("365", "year", "this year"):
        return "year"
    else:
        return "all"

def get_date_filter(range_val: str, column_name: str = "created_at", param_placeholder: str = "?") -> Tuple[Optional[datetime.date], Optional[datetime.date], str, List[Any]]:
    """Generate SQL date range WHERE clause snippet and params.
    
    Ranges:
    - Last 30 Days: TODAY - 30 days
    - Last 90 Days: TODAY - 90 days
    - This Year: Jan 1 of current year until today
    - All Time: No restrictions
    """
    normalized = normalize_date_range(range_val)
    today = datetime.date.today()
    
    if normalized == "30":
        start_date = today - datetime.timedelta(days=30)
        end_date = today
        clause = f"{column_name} >= {param_placeholder} AND {column_name} <= {param_placeholder}"
        params = [start_date.strftime("%Y-%m-%d 00:00:00"), end_date.strftime("%Y-%m-%d 23:59:59")]
    elif normalized == "90":
        start_date = today - datetime.timedelta(days=90)
        end_date = today
        clause = f"{column_name} >= {param_placeholder} AND {column_name} <= {param_placeholder}"
        params = [start_date.strftime("%Y-%m-%d 00:00:00"), end_date.strftime("%Y-%m-%d 23:59:59")]
    elif normalized == "year":
        start_date = datetime.date(today.year, 1, 1)
        end_date = today
        clause = f"{column_name} >= {param_placeholder} AND {column_name} <= {param_placeholder}"
        params = [start_date.strftime("%Y-%m-%d 00:00:00"), end_date.strftime("%Y-%m-%d 23:59:59")]
    else:
        start_date = None
        end_date = None
        clause = "1=1"
        params = []
        
    return start_date, end_date, clause, params

def get_dashboard_kpis(date_range: str = "30") -> List[Dict[str, Any]]:
    """Compute top-level KPI metrics dynamically from CRM pipeline data using date filtering."""
    try:
        from services.pipeline_service import get_pipeline_summary
        from services.project_service import format_currency
        
        summary = get_pipeline_summary(date_range=date_range)
        
        total_leads_val = summary["total_leads"]
        active_leads_val = summary["active_leads"]
        pipeline_value_val = summary["pipeline_value"]
        won_deals_val = summary["won_deals"]
        conversion_rate_val = summary["conversion_rate"]
        average_deal_size_val = summary["average_deal_size"]
        
        return [
            {
                "label": "Total Leads",
                "value": f"{total_leads_val:,}",
                "delta": "+0%",
                "tone": "up" if total_leads_val > 0 else "neutral",
                "icon": "leaderboard",
            },
            {
                "label": "Active Leads",
                "value": f"{active_leads_val:,}",
                "delta": "In Pipeline",
                "tone": "neutral",
                "icon": "analytics",
            },
            {
                "label": "Pipeline Value",
                "value": format_currency(pipeline_value_val),
                "delta": "Live",
                "tone": "up" if pipeline_value_val > 0 else "neutral",
                "icon": "monetization_on",
            },
            {
                "label": "Won Deals",
                "value": f"{won_deals_val:,}",
                "delta": "Closed Won",
                "tone": "up" if won_deals_val > 0 else "neutral",
                "icon": "task_alt",
            },
            {
                "label": "Conversion Rate",
                "value": f"{conversion_rate_val}%",
                "delta": "Win Rate",
                "tone": "up" if conversion_rate_val > 0 else "neutral",
                "icon": "percent",
            },
            {
                "label": "Average Deal Size",
                "value": format_currency(average_deal_size_val),
                "delta": "Avg Value",
                "tone": "neutral",
                "icon": "payments",
            },
        ]
    except Exception as e:
        import logging
        logging.error(f"Error fetching dashboard KPIs: {e}", exc_info=True)
        return [
            {"label": "Total Leads", "value": "0", "delta": "+0%", "tone": "neutral", "icon": "leaderboard"},
            {"label": "Active Leads", "value": "0", "delta": "In Pipeline", "tone": "neutral", "icon": "analytics"},
            {"label": "Pipeline Value", "value": "$0.00", "delta": "Live", "tone": "neutral", "icon": "monetization_on"},
            {"label": "Won Deals", "value": "0", "delta": "Closed Won", "tone": "neutral", "icon": "task_alt"},
            {"label": "Conversion Rate", "value": "0%", "delta": "Win Rate", "tone": "neutral", "icon": "percent"},
            {"label": "Average Deal Size", "value": "$0.00", "delta": "Avg Value", "tone": "neutral", "icon": "payments"},
        ]

def get_pipeline_chart_data(date_range: str = "30") -> Dict[str, List[Any]]:
    """Return pipeline chart monthly values based on selected date range."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # Get start/end dates
        _, _, date_clause, date_params = get_date_filter(date_range, "d.created_at", "?" if is_sqlite else "%s")
        
        if is_sqlite:
            query = f"""
                SELECT 
                    strftime('%Y-%m', d.created_at) as yr_mo,
                    d.category,
                    COALESCE(SUM(c.capacity_mw), 0) as capacity
                FROM pipeline_deals d
                JOIN customers c ON d.customer_id = c.id
                WHERE {date_clause} AND d.is_archived = 0 AND c.is_deleted = 0
                GROUP BY yr_mo, d.category
                ORDER BY yr_mo ASC;
            """
        else:
            query = f"""
                SELECT 
                    TO_CHAR(d.created_at, 'YYYY-MM') as yr_mo,
                    d.category,
                    COALESCE(SUM(c.capacity_mw), 0) as capacity
                FROM pipeline_deals d
                JOIN customers c ON d.customer_id = c.id
                WHERE {date_clause} AND d.is_archived = 0 AND c.is_deleted = 0
                GROUP BY yr_mo, d.category
                ORDER BY yr_mo ASC;
            """
            
        cur.execute(query, date_params)
        rows = cur.fetchall()
        
        month_names = {
            "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
            "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
        }
        
        data_by_month = {}
        for r in rows:
            yr_mo = r[0] if is_sqlite else (r['yr_mo'] if isinstance(r, dict) else r[0])
            cat = r[1] if is_sqlite else (r['category'] if isinstance(r, dict) else r[1])
            cap = float(r[2] if is_sqlite else (r['capacity'] if isinstance(r, dict) else r[2]) or 0.0)
            
            if yr_mo not in data_by_month:
                parts = yr_mo.split("-")
                mo_label = month_names.get(parts[1], parts[1]) if len(parts) > 1 else yr_mo
                if len(parts) > 0:
                    mo_label = f"{mo_label} '{parts[0][2:]}"
                data_by_month[yr_mo] = {"label": mo_label, "Residential": 0.0, "Commercial": 0.0}
                
            category_normalized = "Commercial" if str(cat).upper() in ("COMMERCIAL", "INDUSTRIAL") else "Residential"
            data_by_month[yr_mo][category_normalized] += cap

        if not data_by_month:
            months = []
            res_list = []
            com_list = []
            today = datetime.date.today()
            for i in range(5, -1, -1):
                d = today - datetime.timedelta(days=i*30)
                months.append(d.strftime("%b '%y"))
                res_list.append(0.0)
                com_list.append(0.0)
        else:
            sorted_months = sorted(data_by_month.keys())
            months = [data_by_month[m]["label"] for m in sorted_months]
            res_list = [data_by_month[m]["Residential"] for m in sorted_months]
            com_list = [data_by_month[m]["Commercial"] for m in sorted_months]
            
        return {
            "months": months,
            "residential": res_list,
            "commercial": com_list,
        }
        
    except Exception as e:
        import logging
        logging.error(f"Error fetching pipeline chart data: {e}", exc_info=True)
        return {
            "months": ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"],
            "residential": [0, 0, 0, 0, 0, 0],
            "commercial": [0, 0, 0, 0, 0, 0],
        }
    finally:
        conn.close()

def get_followups(date_range: str = "30") -> List[Dict[str, Any]]:
    """Return list of follow-up reminder items within the selected date range."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    result = []
    try:
        cur = conn.cursor()
        _, _, date_clause, date_params = get_date_filter(date_range, "created_at", "?" if is_sqlite else "%s")
        
        query = f"SELECT due_when, title, note, icon, tone FROM followups WHERE {date_clause} ORDER BY due_order ASC;"
        cur.execute(query, date_params)
        rows = cur.fetchall()
        for r in rows:
            try:
                when = r["due_when"]
                title = r["title"]
                note = r["note"]
                icon = r["icon"]
                tone = r["tone"]
            except (TypeError, IndexError, KeyError):
                when = r[0]
                title = r[1]
                note = r[2]
                icon = r[3]
                tone = r[4]
            result.append({
                "when": when,
                "title": title,
                "note": note,
                "icon": icon,
                "tone": tone,
            })
        return result
    except Exception as e:
        import logging
        logging.error(f"Error fetching followups: {e}", exc_info=True)
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
    per_page: int = 5,
    date_range: str = "30"
) -> Tuple[List[Dict[str, Any]], int]:
    """Fetch paginated, filtered, sorted recent client activity from database within date range."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    items = []
    total_count = 0

    try:
        cur = conn.cursor()

        where_clauses = ["is_deleted = 0"]
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

        # Date range filter
        _, _, date_clause, date_params = get_date_filter(date_range, "created_at", "?" if is_sqlite else "%s")
        where_clauses.append(date_clause)
        params.extend(date_params)

        where_sql = " WHERE " + " AND ".join(where_clauses)

        # Security Whitelist: Map parameter keys strictly to hardcoded column identifiers
        valid_sorts = {
            "name": "name",
            "updated_at": "updated_at",
            "status": "status",
            "value": "value_numeric",
        }
        sort_column = valid_sorts.get(sort_by.lower(), "updated_at")
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
        import logging
        logging.error(f"Error fetching recent activity: {e}", exc_info=True)
        return [], 0
    finally:
        conn.close()

def export_recent_activity_csv(search: str = "", category: str = "", status: str = "", date_range: str = "30") -> str:
    """Generate CSV string of customer activity for export within date range."""
    items, _ = get_recent_activity(search=search, category=category, status=status, date_range=date_range, per_page=1000)

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


def get_capacity_pipeline() -> Dict[str, Any]:
    """
    Computes upcoming solar capacity deployment pipeline for the next 6 months.
    Aggregates capacity (MW) from Projects (Planning/Execution/On Hold) and Accepted (Approved) Proposals.
    Groups results by month and splits Residential vs Commercial segments.
    """
    import logging
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    
    # 1. Generate next 6 months starting from current month
    today = datetime.date.today()
    labels = []
    month_keys = []
    
    for i in range(6):
        m = (today.month - 1 + i) % 12 + 1
        y = today.year + (today.month - 1 + i) // 12
        d = datetime.date(y, m, 1)
        labels.append(d.strftime("%b"))
        month_keys.append(f"{y:04d}-{m:02d}")
        
    res_mw = {key: 0.0 for key in month_keys}
    com_mw = {key: 0.0 for key in month_keys}
    
    def extract_year_month(date_str):
        if not date_str:
            return None
        date_str = str(date_str).strip()
        if len(date_str) >= 7 and date_str[4] == '-':
            return date_str[:7]
        return None

    try:
        cur = conn.cursor()
        
        # 2. Fetch Projects (exclude 'Completed' and soft-deleted customer records)
        projects_query = """
            SELECT p.capacity_kw, p.start_date, p.expected_completion, p.created_at, c.category
            FROM projects p
            JOIN customers c ON p.customer_id = c.id
            WHERE p.status != 'Completed' AND c.is_deleted = 0;
        """
        cur.execute(projects_query)
        project_rows = cur.fetchall()
        
        for r in project_rows:
            try:
                cap_kw = r["capacity_kw"]
                start_dt = r["start_date"]
                exp_comp = r["expected_completion"]
                created_at = r["created_at"]
                category = r["category"]
            except (TypeError, IndexError, KeyError):
                cap_kw = r[0]
                start_dt = r[1]
                exp_comp = r[2]
                created_at = r[3]
                category = r[4]
                
            ym = extract_year_month(start_dt) or extract_year_month(exp_comp) or extract_year_month(created_at)
            if ym in month_keys:
                mw = float(cap_kw or 0.0) / 1000.0
                if str(category).lower() == "residential":
                    res_mw[ym] += mw
                else:
                    com_mw[ym] += mw
                    
        # 3. Fetch Approved Proposals (exclude if already converted to project or customer is deleted)
        proposals_query = """
            SELECT prop.plant_size_kw, prop.prepared_date, prop.created_at, c.category
            FROM proposals prop
            JOIN customers c ON prop.customer_id = c.id
            WHERE prop.status = 'Approved' 
              AND prop.is_active = 1
              AND c.is_deleted = 0
              AND prop.id NOT IN (
                  SELECT DISTINCT proposal_id FROM projects WHERE proposal_id IS NOT NULL
              );
        """
        cur.execute(proposals_query)
        proposal_rows = cur.fetchall()
        
        for r in proposal_rows:
            try:
                plant_kw = r["plant_size_kw"]
                prep_dt = r["prepared_date"]
                created_at = r["created_at"]
                category = r["category"]
            except (TypeError, IndexError, KeyError):
                plant_kw = r[0]
                prep_dt = r[1]
                created_at = r[2]
                category = r[3]
                
            ym = extract_year_month(prep_dt) or extract_year_month(created_at)
            if ym in month_keys:
                mw = float(plant_kw or 0.0) / 1000.0
                if str(category).lower() == "residential":
                    res_mw[ym] += mw
                else:
                    com_mw[ym] += mw
                    
    except Exception as e:
        logging.error(f"Error computing capacity pipeline chart: {e}", exc_info=True)
    finally:
        conn.close()
        
    return {
        "labels": labels,
        "residential": [round(res_mw[key], 2) for key in month_keys],
        "commercial": [round(com_mw[key], 2) for key in month_keys]
    }
