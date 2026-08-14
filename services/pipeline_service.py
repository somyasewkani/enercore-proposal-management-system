"""
Enercore AI Solar Proposal Generator
services/pipeline_service.py

Service layer for CRM Kanban pipeline deals, stage movement, and pipeline metrics.
"""

import uuid
import sqlite3
import logging
from typing import Dict, List, Any, Tuple, Optional
from database.connection import get_connection

# Define valid Kanban stages in progression order
PIPELINE_STAGES = [
    "New Lead",
    "Contacted",
    "Bill Received",
    "Analysis Completed",
    "Proposal Sent",
    "Negotiation",
    "Won",
    "Lost"
]

def get_allowed_transitions(current_stage: str) -> List[str]:
    """Calculate allowed CRM stage transitions to enforce lifecycle rules.
    
    Progression sequence:
    New Lead -> Contacted -> Bill Received -> Analysis Completed -> Proposal Sent -> Negotiation -> Won
    
    Rules:
    - Active stages can transition to any other active stage (New Lead, Contacted, Bill Received, Analysis Completed, Proposal Sent, Negotiation) and Lost.
    - Transitions to 'Won' are only allowed from 'Proposal Sent' or 'Negotiation'.
    - Won/Lost deals can transition back to 'New Lead' or 'Negotiation' to re-open them.
    """
    if current_stage not in PIPELINE_STAGES:
        return []
        
    if current_stage in ("Won", "Lost"):
        return ["New Lead", "Negotiation"]
        
    allowed = []
    # Can transition to any other stage except Won
    for stage in PIPELINE_STAGES:
        if stage != "Won" and stage != current_stage:
            allowed.append(stage)
            
    # Can transition to Won from Proposal Sent or Negotiation
    if current_stage in ("Proposal Sent", "Negotiation"):
        allowed.append("Won")
        
    return allowed

def is_valid_transition(current_stage: str, new_stage: str) -> bool:
    """Verify if a stage transition is valid under lifecycle constraints."""
    return new_stage in get_allowed_transitions(current_stage)

def init_pipeline_db(seed_demo: bool = False):
    """Ensure pipeline_deals table exists in database cleanly with normalized schema."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # Check table schema and drop if legacy format is found
        table_exists = False
        has_customer_id = False
        
        if is_sqlite:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pipeline_deals';")
            table_exists = len(cur.fetchall()) > 0
            if table_exists:
                cur.execute("PRAGMA table_info(pipeline_deals);")
                cols = [row[1] for row in cur.fetchall()]
                has_customer_id = "customer_id" in cols
        else:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pipeline_deals'
                );
            """)
            table_exists = cur.fetchone()[0]
            if table_exists:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'pipeline_deals';
                """)
                cols = [r[0] if not isinstance(r, dict) else r['column_name'] for r in cur.fetchall()]
                has_customer_id = "customer_id" in cols

        if table_exists and not has_customer_id:
            logging.info("Legacy pipeline_deals format detected. Yielding schema migration to connection.py...")
            return
            
        if not table_exists:
            logging.info("Creating normalized pipeline_deals database table...")
            if is_sqlite:
                cur.execute("""
                    CREATE TABLE pipeline_deals (
                        id TEXT PRIMARY KEY,
                        customer_id TEXT NOT NULL,
                        category TEXT NOT NULL,
                        value_numeric REAL DEFAULT 0,
                        stage TEXT NOT NULL,
                        contact_person TEXT,
                        is_archived INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'Active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_deals_stage ON pipeline_deals (stage);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_deals_customer ON pipeline_deals (customer_id);")
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
                cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_deals_stage ON pipeline_deals (stage);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_deals_customer ON pipeline_deals (customer_id);")
                
            if seed_demo:
                seed_pipeline_deals(cur, is_sqlite)
                
        conn.commit()
    except Exception as e:
        logging.error(f"Error initializing pipeline db schema: {e}", exc_info=True)
    finally:
        conn.close()

def seed_pipeline_deals(cur, is_sqlite: bool):
    """Seed initial demo pipeline deals and customers."""
    cust_id = "cus_caparo_maruti"
    cur.execute("SELECT COUNT(*) FROM customers WHERE id = ?;" if is_sqlite else "SELECT COUNT(*) FROM customers WHERE id = %s;", (cust_id,))
    row = cur.fetchone()
    count = row[0] if is_sqlite else (row['count'] if isinstance(row, dict) else row[0])
    
    if count == 0:
        cur.execute("""
            INSERT INTO customers (id, name, category, status, tone, value_numeric, capacity_mw, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO customers (id, name, category, status, tone, value_numeric, capacity_mw, is_deleted)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (cust_id, "M/S CAPARO MARUTI LTD", "Industrial", "New Lead", "neutral", 75000000.0, 1.5, 0))
        
    cur.execute("""
        INSERT INTO pipeline_deals (id, customer_id, category, value_numeric, stage, contact_person, is_archived, status)
        VALUES (?, ?, ?, ?, ?, ?, 0, 'Active');
    """ if is_sqlite else """
        INSERT INTO pipeline_deals (id, customer_id, category, value_numeric, stage, contact_person, is_archived, status)
        VALUES (%s, %s, %s, %s, %s, %s, 0, 'Active');
    """, ("deal_1", cust_id, "Industrial", 75000000.0, "New Lead", "Senior QA Lead"))

def get_pipeline_summary(date_range: str = "all") -> Dict[str, Any]:
    """Compiles top-level metrics from live database data in a single optimized aggregate query within date range."""
    init_pipeline_db(seed_demo=False)
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        from services.dashboard_service import get_date_filter
        _, _, date_clause, date_params = get_date_filter(date_range, "d.created_at", "?" if is_sqlite else "%s")
        
        query = f"""
            SELECT 
                COUNT(d.id) as total_leads,
                COALESCE(SUM(CASE WHEN d.stage NOT IN ('Won', 'Lost') THEN 1 ELSE 0 END), 0) as active_leads,
                COALESCE(SUM(CASE WHEN d.stage NOT IN ('Won', 'Lost') THEN d.value_numeric ELSE 0 END), 0) as pipeline_value,
                COALESCE(SUM(CASE WHEN d.stage = 'Won' THEN 1 ELSE 0 END), 0) as won_deals,
                COALESCE(AVG(CASE WHEN d.stage NOT IN ('Won', 'Lost') THEN d.value_numeric END), 0) as average_deal_size
            FROM pipeline_deals d
            JOIN customers c ON d.customer_id = c.id
            WHERE d.is_archived = 0 AND c.is_deleted = 0 AND {date_clause};
        """
        cur.execute(query, date_params)
        row = cur.fetchone()
        
        if not row:
            return {
                "total_leads": 0,
                "active_leads": 0,
                "pipeline_value": 0.0,
                "won_deals": 0,
                "conversion_rate": 0.0,
                "average_deal_size": 0.0
            }
            
        if isinstance(row, dict):
            total_leads = int(row.get("total_leads", 0) or 0)
            active_leads = int(row.get("active_leads", 0) or 0)
            pipeline_value = float(row.get("pipeline_value", 0.0) or 0.0)
            won_deals = int(row.get("won_deals", 0) or 0)
            average_deal_size = float(row.get("average_deal_size", 0.0) or 0.0)
        else:
            total_leads = int(row[0] or 0)
            active_leads = int(row[1] or 0)
            pipeline_value = float(row[2] or 0.0)
            won_deals = int(row[3] or 0)
            average_deal_size = float(row[4] or 0.0)
            
          
        conversion_rate = round((won_deals / total_leads * 100), 1) if total_leads > 0 else 0.0
        
        return {
            "total_leads": total_leads,
            "active_leads": active_leads,
            "pipeline_value": pipeline_value,
            "won_deals": won_deals,
            "conversion_rate": conversion_rate,
            "average_deal_size": average_deal_size
        }
    except Exception as e:
        logging.error(f"Error computing pipeline summary: {e}", exc_info=True)
        return {
            "total_leads": 0,
            "active_leads": 0,
            "pipeline_value": 0.0,
            "won_deals": 0,
            "conversion_rate": 0.0,
            "average_deal_size": 0.0
        }
    finally:
        conn.close()

def get_pipeline_stage_counts() -> Dict[str, Dict[str, Any]]:
    """Compiles counts and total values grouped by stage using database aggregation."""
    init_pipeline_db(seed_demo=False)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT d.stage, COUNT(d.id), COALESCE(SUM(d.value_numeric), 0)
            FROM pipeline_deals d
            JOIN customers c ON d.customer_id = c.id
            WHERE d.is_archived = 0 AND c.is_deleted = 0
            GROUP BY d.stage;
        """)
        rows = cur.fetchall()
        result = {s: {"count": 0, "total_value": 0.0} for s in PIPELINE_STAGES}
        for r in rows:
            stage = r[0]
            count = int(r[1] or 0)
            total_val = float(r[2] or 0.0)
            if stage in result:
                result[stage] = {"count": count, "total_value": total_val}
        return result
    except Exception as e:
        logging.error(f"Error computing stage counts: {e}", exc_info=True)
        return {}
    finally:
        conn.close()

def get_pipeline_cards() -> Dict[str, Dict[str, Any]]:
    """Fetches and groups Kanban board cards by pipeline stage with normalized values and latest proposal status."""
    init_pipeline_db(seed_demo=False)
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    result = {s: {"deals": [], "total_val": 0.0, "total_formatted": "$0.00", "count": 0} for s in PIPELINE_STAGES}
    try:
        cur = conn.cursor()
        query = """
            SELECT 
                d.id, 
                c.name as company_name, 
                d.category, 
                d.value_numeric, 
                d.stage, 
                d.created_at, 
                c.id as customer_id
            FROM pipeline_deals d
            JOIN customers c ON d.customer_id = c.id
            WHERE d.is_archived = 0 AND c.is_deleted = 0
            ORDER BY d.created_at DESC;
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        # Load all latest active proposals in one batch to prevent N+1 query
        prop_query = """
            SELECT customer_id, id, status, system_cost
            FROM proposals
            WHERE is_active = 1;
        """
        cur.execute(prop_query)
        prop_rows = cur.fetchall()
        latest_proposals = {}
        for pr in prop_rows:
            cust_id = pr[0] if is_sqlite else (pr['customer_id'] if isinstance(pr, dict) else pr[0])
            latest_proposals[cust_id] = {
                "id": pr[1] if is_sqlite else (pr['id'] if isinstance(pr, dict) else pr[1]),
                "status": pr[2] if is_sqlite else (pr['status'] if isinstance(pr, dict) else pr[2]),
                "value": float(pr[3] if is_sqlite else (pr['system_cost'] if isinstance(pr, dict) else pr[3]) or 0.0)
            }
            
        from services.project_service import format_currency
        for r in rows:
            deal_id = r[0] if is_sqlite else (r['id'] if isinstance(r, dict) else r[0])
            comp_name = r[1] if is_sqlite else (r['company_name'] if isinstance(r, dict) else r[1])
            category = r[2] if is_sqlite else (r['category'] if isinstance(r, dict) else r[2])
            val = float(r[3] if is_sqlite else (r['value_numeric'] if isinstance(r, dict) else r[3]) or 0.0)
            stage_name = r[4] if is_sqlite else (r['stage'] if isinstance(r, dict) else r[4])
            cust_id = r[6] if is_sqlite else (r['customer_id'] if isinstance(r, dict) else r[6])
            
            if stage_name not in result:
                continue
                
            proposal_info = latest_proposals.get(cust_id, {"id": None, "status": "No Proposal", "value": 0.0})
            
            result[stage_name]["deals"].append({
                "id": deal_id,
                "company_name": comp_name,
                "category": category,
                "value_numeric": val,
                "value_formatted": format_currency(val),
                "stage": stage_name,
                "time_ago": "Just now",
                "customer_id": cust_id,
                "latest_proposal_id": proposal_info["id"],
                "latest_proposal_status": proposal_info["status"],
                "latest_proposal_value": format_currency(proposal_info["value"]),
                "allowed_transitions": get_allowed_transitions(stage_name)
            })
            result[stage_name]["total_val"] += val
            result[stage_name]["count"] += 1
            
        for s in result:
            result[s]["total_formatted"] = format_currency(result[s]["total_val"])
            
        return result
    except Exception as e:
        logging.error(f"Error fetching pipeline cards: {e}", exc_info=True)
        return result
    finally:
        conn.close()

def get_all_deals_by_stage() -> Dict[str, Dict[str, Any]]:
    """Legacy compatibility alias for get_pipeline_cards() to keep existing QA tests operational."""
    return get_pipeline_cards()

def get_pipeline_total_value() -> str:
    """Return total formatted value of all active pipeline deals."""
    summary = get_pipeline_summary()
    from services.project_service import format_currency
    return format_currency(summary["pipeline_value"])

def create_pipeline_deal(data: Dict[str, Any]) -> bool:
    """Create a new deal in the pipeline, creating the backing customer if necessary."""
    init_pipeline_db(seed_demo=False)
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        company_name = data.get("company_name", "").strip()
        if not company_name:
            return False
            
        # 1. Look up existing active customer by name
        cur.execute(
            "SELECT id FROM customers WHERE name = ? AND is_deleted = 0 LIMIT 1;" 
            if is_sqlite else 
            "SELECT id FROM customers WHERE name = %s AND is_deleted = 0 LIMIT 1;", 
            (company_name,)
        )
        row = cur.fetchone()
        if row:
            customer_id = row[0] if is_sqlite else (row['id'] if isinstance(row, dict) else row[0])
        else:
            # Create a backing customer
            customer_id = f"cus_{uuid.uuid4().hex[:8]}"
            cur.execute("""
                INSERT INTO customers (id, name, category, status, is_deleted)
                VALUES (?, ?, ?, ?, 0);
            """ if is_sqlite else """
                INSERT INTO customers (id, name, category, status, is_deleted)
                VALUES (%s, %s, %s, %s, 0);
            """, (
                customer_id,
                company_name,
                data.get("category", "COMMERCIAL").upper(),
                data.get("stage", "New Lead")
            ))
            
        # 2. Insert pipeline deal
        deal_id = f"deal_{uuid.uuid4().hex[:8]}"
        query = """
            INSERT INTO pipeline_deals (id, customer_id, category, value_numeric, stage, contact_person, is_archived, status)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'Active');
        """ if is_sqlite else """
            INSERT INTO pipeline_deals (id, customer_id, category, value_numeric, stage, contact_person, is_archived, status)
            VALUES (%s, %s, %s, %s, %s, %s, 0, 'Active');
        """
        cur.execute(query, (
            deal_id,
            customer_id,
            data.get("category", "COMMERCIAL").upper(),
            float(data.get("value_numeric", 0)),
            data.get("stage", "New Lead"),
            data.get("contact_person", "")
        ))
        
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error in create_pipeline_deal: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def update_deal_stage(deal_id: str, new_stage: str) -> bool:
    """Move deal to a new stage if the transition is allowed by lifecycle rules."""
    init_pipeline_db(seed_demo=False)
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # 1. Fetch current deal stage
        cur.execute(
            "SELECT stage, customer_id FROM pipeline_deals WHERE id = ?;" 
            if is_sqlite else 
            "SELECT stage, customer_id FROM pipeline_deals WHERE id = %s;", 
            (deal_id,)
        )
        row = cur.fetchone()
        if not row:
            return False
            
        current_stage = row[0] if is_sqlite else (row['stage'] if isinstance(row, dict) else row[0])
        customer_id = row[1] if is_sqlite else (row['customer_id'] if isinstance(row, dict) else row[1])
        
        # 2. Validate transition
        if not is_valid_transition(current_stage, new_stage):
            logging.warning(f"Invalid stage transition attempted: '{current_stage}' -> '{new_stage}'")
            return False
            
        # 3. Update deal stage
        query = (
            "UPDATE pipeline_deals SET stage = ? WHERE id = ?;" 
            if is_sqlite else 
            "UPDATE pipeline_deals SET stage = %s WHERE id = %s;"
        )
        cur.execute(query, (new_stage, deal_id))
        
        # 4. Sync status with backing customer
        cust_status = new_stage
        if new_stage == "Won":
            cust_status = "Contract Signed"
        elif new_stage == "Lost":
            cust_status = "Archived"
            
        cur.execute(
            "UPDATE customers SET status = ? WHERE id = ?;" 
            if is_sqlite else 
            "UPDATE customers SET status = %s WHERE id = %s;", 
            (cust_status, customer_id)
        )
        
        # 5. Project Integration:
        if new_stage == "Won":
            cur.execute("""
                SELECT id FROM proposals 
                WHERE customer_id = ? AND status = 'Approved' AND is_active = 1
                ORDER BY version DESC LIMIT 1;
            """ if is_sqlite else """
                SELECT id FROM proposals 
                WHERE customer_id = %s AND status = 'Approved' AND is_active = 1
                ORDER BY version DESC LIMIT 1;
            """, (customer_id,))
            prop_row = cur.fetchone()
            if prop_row:
                prop_id = prop_row[0] if is_sqlite else (prop_row['id'] if isinstance(prop_row, dict) else prop_row[0])
                
                cur.execute(
                    "SELECT COUNT(*) FROM projects WHERE proposal_id = ? AND status != 'Cancelled';" 
                    if is_sqlite else 
                    "SELECT COUNT(*) FROM projects WHERE proposal_id = %s AND status != 'Cancelled';", 
                    (prop_id,)
                )
                proj_row = cur.fetchone()
                proj_exists = proj_row[0] if is_sqlite else (proj_row['count'] if isinstance(proj_row, dict) else proj_row[0])
                
                if proj_exists == 0:
                    from services.project_service import convert_proposal_to_project
                    conn.commit()
                    convert_proposal_to_project(prop_id, actor="System CRM")
                    conn = get_connection()
                    cur = conn.cursor()
                    
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error in update_deal_stage: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def move_pipeline_stage(deal_id: str, new_stage: str) -> bool:
    """Move deal to a new stage wrapping update_deal_stage."""
    return update_deal_stage(deal_id, new_stage)

def update_pipeline_deal(deal_id: str, data: Dict[str, Any]) -> bool:
    """Update pipeline deal category, value, contact person and sync customer name."""
    init_pipeline_db(seed_demo=False)
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT customer_id FROM pipeline_deals WHERE id = ?;" 
            if is_sqlite else 
            "SELECT customer_id FROM pipeline_deals WHERE id = %s;", 
            (deal_id,)
        )
        row = cur.fetchone()
        if not row:
            return False
        cust_id = row[0] if is_sqlite else (row['customer_id'] if isinstance(row, dict) else row[0])
        
        query = """
            UPDATE pipeline_deals 
            SET category = ?, value_numeric = ?, contact_person = ?
            WHERE id = ?;
        """ if is_sqlite else """
            UPDATE pipeline_deals 
            SET category = %s, value_numeric = %s, contact_person = %s
            WHERE id = %s;
        """
        cur.execute(query, (
            data.get("category", "COMMERCIAL").upper(),
            float(data.get("value_numeric", 0.0)),
            data.get("contact_person", ""),
            deal_id
        ))
        
        if "company_name" in data:
            comp_name = data["company_name"].strip()
            if comp_name:
                cur.execute(
                    "UPDATE customers SET name = ? WHERE id = ?;" 
                    if is_sqlite else 
                    "UPDATE customers SET name = %s WHERE id = %s;", 
                    (comp_name, cust_id)
                )
                
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error in update_pipeline_deal: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def delete_pipeline_deal(deal_id: str) -> bool:
    """Permanently delete a deal from pipeline."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = "DELETE FROM pipeline_deals WHERE id = ?;" if is_sqlite else "DELETE FROM pipeline_deals WHERE id = %s;"
        cur.execute(query, (deal_id,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error in delete_pipeline_deal: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def archive_pipeline_deal(deal_id: str) -> bool:
    """Soft-delete/archive a pipeline deal and also marks the customer as archived."""
    init_pipeline_db(seed_demo=False)
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT customer_id FROM pipeline_deals WHERE id = ?;" 
            if is_sqlite else 
            "SELECT customer_id FROM pipeline_deals WHERE id = %s;", 
            (deal_id,)
        )
        row = cur.fetchone()
        if not row:
            return False
        cust_id = row[0] if is_sqlite else (row['customer_id'] if isinstance(row, dict) else row[0])
        
        cur.execute(
            "UPDATE pipeline_deals SET is_archived = 1 WHERE id = ?;" 
            if is_sqlite else 
            "UPDATE pipeline_deals SET is_archived = 1 WHERE id = %s;", 
            (deal_id,)
        )
        cur.execute(
            "UPDATE customers SET is_deleted = 1, status = 'Archived' WHERE id = ?;" 
            if is_sqlite else 
            "UPDATE customers SET is_deleted = 1, status = 'Archived' WHERE id = %s;", 
            (cust_id,)
        )
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error in archive_pipeline_deal: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def restore_pipeline_deal(deal_id: str) -> bool:
    """Restore an archived pipeline deal and active status of its customer."""
    init_pipeline_db(seed_demo=False)
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT customer_id FROM pipeline_deals WHERE id = ?;" 
            if is_sqlite else 
            "SELECT customer_id FROM pipeline_deals WHERE id = %s;", 
            (deal_id,)
        )
        row = cur.fetchone()
        if not row:
            return False
        cust_id = row[0] if is_sqlite else (row['customer_id'] if isinstance(row, dict) else row[0])
        
        cur.execute(
            "UPDATE pipeline_deals SET is_archived = 0 WHERE id = ?;" 
            if is_sqlite else 
            "UPDATE pipeline_deals SET is_archived = 0 WHERE id = %s;", 
            (deal_id,)
        )
        cur.execute(
            "UPDATE customers SET is_deleted = 0, status = 'New Lead' WHERE id = ?;" 
            if is_sqlite else 
            "UPDATE customers SET is_deleted = 0, status = 'New Lead' WHERE id = %s;", 
            (cust_id,)
        )
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error in restore_pipeline_deal: {e}", exc_info=True)
        return False
    finally:
        conn.close()
