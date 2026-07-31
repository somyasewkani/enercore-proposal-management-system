"""
Enercore AI Solar Proposal Generator
services/project_service.py

Service layer for managing projects, converting proposals, tracking lifecycles,
handling document uploads, logging timeline activities, and compiling stats.
"""

import os
import uuid
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from database.connection import get_connection


def convert_proposal_to_project(
    proposal_id: str,
    actor: str = "System",
    start_date: str = None,
    expected_completion: str = None,
    manager: str = None,
    execution_model: str = "EPC"
) -> Tuple[bool, str]:
    """Validate and convert an approved proposal into an executable project."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # 1. Fetch proposal details
        query_prop = """
            SELECT p.*, c.name as customer_name
            FROM proposals p
            JOIN customers c ON p.customer_id = c.id
            WHERE p.id = ?;
        """ if is_sqlite else """
            SELECT p.*, c.name as customer_name
            FROM proposals p
            JOIN customers c ON p.customer_id = c.id
            WHERE p.id = %s;
        """
        cur.execute(query_prop, (proposal_id,))
        prop = cur.fetchone()
        
        if not prop:
            return False, "Proposal does not exist."
            
        p_status = prop["status"] if is_sqlite else (prop["status"] if isinstance(prop, dict) else prop[8])
        if p_status != "Approved":
            return False, f"Proposal must be Approved before converting to project (current status: {p_status})."
            
        # 2. Check for active projects referencing this proposal
        # Status 'Cancelled' projects are not considered active.
        query_proj = """
            SELECT COUNT(*) FROM projects
            WHERE proposal_id = ? AND status != 'Cancelled';
        """ if is_sqlite else """
            SELECT COUNT(*) FROM projects
            WHERE proposal_id = %s AND status != 'Cancelled';
        """
        cur.execute(query_proj, (proposal_id,))
        count_proj = cur.fetchone()[0] if is_sqlite else (cur.fetchone()['count'] if isinstance(cur.fetchone(), dict) else cur.fetchone()[0])
        
        if count_proj > 0:
            return False, "An active project already exists for this approved proposal."

        # 3. Generate Project Number (PRJ-YYYY-XXXX)
        current_year = datetime.now().year
        year_prefix = f"PRJ-{current_year}-"
        
        query_num = """
            SELECT project_number FROM projects
            WHERE project_number LIKE ?
            ORDER BY project_number DESC LIMIT 1;
        """ if is_sqlite else """
            SELECT project_number FROM projects
            WHERE project_number LIKE %s
            ORDER BY project_number DESC LIMIT 1;
        """
        cur.execute(query_num, (f"{year_prefix}%",))
        last_row = cur.fetchone()
        
        next_seq = 1
        if last_row:
            last_num = last_row[0] if is_sqlite else (last_row["project_number"] if isinstance(last_row, dict) else last_row[0])
            try:
                last_seq = int(last_num.split("-")[-1])
                next_seq = last_seq + 1
            except ValueError:
                pass
                
        proj_number = f"{year_prefix}{next_seq:04d}"
        
        # 4. Insert new project record
        proj_id = f"prj_{uuid.uuid4().hex[:12]}"
        
        prop_num = prop["proposal_number"] if is_sqlite else (prop["proposal_number"] if isinstance(prop, dict) else prop[1])
        c_id = prop["customer_id"] if is_sqlite else (prop["customer_id"] if isinstance(prop, dict) else prop[2])
        s_id = prop["site_id"] if is_sqlite else (prop["site_id"] if isinstance(prop, dict) else prop[3])
        prop_name = prop["proposal_name"] if is_sqlite else (prop["proposal_name"] if isinstance(prop, dict) else prop[6])
        cap = prop["plant_size_kw"] if is_sqlite else (prop["plant_size_kw"] if isinstance(prop, dict) else prop[9])
        cost = prop["system_cost"] if is_sqlite else (prop["system_cost"] if isinstance(prop, dict) else prop[13])
        
        project_name = f"Solar Integration - {prop_name}"
        
        insert_query = """
            INSERT INTO projects (
                id, project_number, proposal_id, customer_id, site_id, project_name,
                status, execution_model, capacity_kw, contract_value, project_manager,
                start_date, expected_completion, progress_percentage, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        """ if is_sqlite else """
            INSERT INTO projects (
                id, project_number, proposal_id, customer_id, site_id, project_name,
                status, execution_model, capacity_kw, contract_value, project_manager,
                start_date, expected_completion, progress_percentage, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        """
        
        cur.execute(insert_query, (
            proj_id,
            proj_number,
            proposal_id,
            c_id,
            s_id,
            project_name,
            "Planning",
            execution_model,
            cap or 0.0,
            cost or 0.0,
            manager or actor,
            start_date or datetime.now().strftime("%Y-%m-%d"),
            expected_completion or ""
        ))
        
        # 5. Log project activities
        activity_query = """
            INSERT INTO project_activities (project_id, activity_type, description, created_by, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);
        """ if is_sqlite else """
            INSERT INTO project_activities (project_id, activity_type, description, created_by, created_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP);
        """
        cur.execute(activity_query, (
            proj_id,
            "Project Created",
            f"Project converted from approved proposal {prop_num}.",
            actor
        ))
        
        # 6. Log site activities timeline log
        if s_id:
            site_log_query = """
                INSERT INTO site_activities (site_id, activity_type, description, created_by, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);
            """ if is_sqlite else """
                INSERT INTO site_activities (site_id, activity_type, description, created_by, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP);
            """
            cur.execute(site_log_query, (
                s_id,
                "Project Launched",
                f"Solar execution project created: {proj_number} ({execution_model}).",
                actor
            ))

        # Update customer pipeline status to 'Contract Signed'
        cust_update = "UPDATE customers SET status = 'Contract Signed' WHERE id = ?;" if is_sqlite else "UPDATE customers SET status = 'Contract Signed' WHERE id = %s;"
        cur.execute(cust_update, (c_id,))
        
        conn.commit()
        return True, proj_id
        
    except Exception as e:
        conn.rollback()
        print(f"Error converting proposal to project: {e}")
        return False, str(e)
    finally:
        conn.close()


def get_project_details(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full project details, customer info, and site specs."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = """
            SELECT p.*, 
                   c.name as customer_name, c.contact as customer_contact, c.phone as customer_phone,
                   s.name as site_name, s.address_street as site_street, s.address_city as site_city,
                   s.address_state as site_state, s.address_zip as site_zip,
                   prop.proposal_number
            FROM projects p
            JOIN customers c ON p.customer_id = c.id
            LEFT JOIN sites s ON p.site_id = s.id
            LEFT JOIN proposals prop ON p.proposal_id = prop.id
            WHERE p.id = ?;
        """ if is_sqlite else """
            SELECT p.*, 
                   c.name as customer_name, c.contact as customer_contact, c.phone as customer_phone,
                   s.name as site_name, s.address_street as site_street, s.address_city as site_city,
                   s.address_state as site_state, s.address_zip as site_zip,
                   prop.proposal_number
            FROM projects p
            JOIN customers c ON p.customer_id = c.id
            LEFT JOIN sites s ON p.site_id = s.id
            LEFT JOIN proposals prop ON p.proposal_id = prop.id
            WHERE p.id = %s;
        """
        cur.execute(query, (project_id,))
        r = cur.fetchone()
        if not r:
            return None
            
        return {
            "id": r["id"],
            "project_number": r["project_number"],
            "proposal_id": r["proposal_id"],
            "customer_id": r["customer_id"],
            "site_id": r["site_id"],
            "project_name": r["project_name"],
            "status": r["status"],
            "execution_model": r["execution_model"],
            "capacity_kw": r["capacity_kw"],
            "contract_value": r["contract_value"],
            "project_manager": r["project_manager"],
            "start_date": r["start_date"],
            "expected_completion": r["expected_completion"],
            "actual_completion": r["actual_completion"],
            "progress_percentage": r["progress_percentage"],
            "remarks": r["remarks"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "customer_name": r["customer_name"],
            "customer_contact": r["customer_contact"],
            "customer_phone": r["customer_phone"],
            "site_name": r["site_name"],
            "site_street": r["site_street"],
            "site_city": r["site_city"],
            "site_state": r["site_state"],
            "site_zip": r["site_zip"],
            "proposal_number": r["proposal_number"]
        }
    except Exception as e:
        print(f"Error fetching project details: {e}")
        return None
    finally:
        conn.close()


def list_projects(
    search_q: str = None,
    status_filter: str = None,
    manager_filter: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> List[Dict[str, Any]]:
    """Query, filter, and sort projects list."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    results = []
    try:
        cur = conn.cursor()
        where_clauses = []
        params = []
        
        if search_q and search_q.strip():
            q = f"%{search_q.strip()}%"
            where_clauses.append("(p.project_number LIKE ? OR p.project_name LIKE ? OR c.name LIKE ?)")
            params.extend([q, q, q])
            
        if status_filter and status_filter != "all":
            where_clauses.append("p.status = ?")
            params.append(status_filter)
            
        if manager_filter and manager_filter != "all":
            where_clauses.append("p.project_manager = ?")
            params.append(manager_filter)
            
        # Validate sort fields to avoid injection
        valid_sorts = {"project_number", "capacity_kw", "contract_value", "progress_percentage", "created_at", "status"}
        if sort_by not in valid_sorts:
            sort_by = "created_at"
            
        order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"
        
        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # In SQLite/Postgres we match placeholder bindings
        if not is_sqlite:
            where_str = where_str.replace("?", "%s")
            
        query = f"""
            SELECT p.*, c.name as customer_name
            FROM projects p
            JOIN customers c ON p.customer_id = c.id
            {where_str}
            ORDER BY p.{sort_by} {order_dir};
        """
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        
        for r in rows:
            results.append({
                "id": r["id"],
                "project_number": r["project_number"],
                "proposal_id": r["proposal_id"],
                "customer_id": r["customer_id"],
                "site_id": r["site_id"],
                "project_name": r["project_name"],
                "status": r["status"],
                "execution_model": r["execution_model"],
                "capacity_kw": r["capacity_kw"],
                "contract_value": r["contract_value"],
                "project_manager": r["project_manager"],
                "start_date": r["start_date"],
                "expected_completion": r["expected_completion"],
                "actual_completion": r["actual_completion"],
                "progress_percentage": r["progress_percentage"],
                "created_at": r["created_at"],
                "customer_name": r["customer_name"]
            })
        return results
    except Exception as e:
        print(f"Error listing projects: {e}")
        return []
    finally:
        conn.close()


def get_project_managers() -> List[str]:
    """Retrieve distinct list of project managers currently assigned."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT project_manager FROM projects WHERE project_manager IS NOT NULL AND project_manager != '';")
        rows = cur.fetchall()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"Error fetching project managers: {e}")
        return []
    finally:
        conn.close()


def update_project_status(
    project_id: str,
    new_status: str,
    progress: int,
    actor: str = "System",
    remarks: str = None,
    manager: str = None,
    expected_completion: str = None
) -> bool:
    """Updates a project's execution details and status, logging an audit activity."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # Get current status to check for state updates
        query_current = "SELECT status, progress_percentage, site_id FROM projects WHERE id = ?;" if is_sqlite else "SELECT status, progress_percentage, site_id FROM projects WHERE id = %s;"
        cur.execute(query_current, (project_id,))
        row = cur.fetchone()
        if not row:
            return False
            
        old_status = row["status"] if is_sqlite else (row["status"] if isinstance(row, dict) else row[0])
        old_progress = row["progress_percentage"] if is_sqlite else (row["progress_percentage"] if isinstance(row, dict) else row[1])
        s_id = row["site_id"] if is_sqlite else (row["site_id"] if isinstance(row, dict) else row[2])
        
        actual_comp = None
        if new_status == "Completed":
            actual_comp = datetime.now().strftime("%Y-%m-%d")
            
        update_query = """
            UPDATE projects
            SET status = ?, progress_percentage = ?, remarks = ?, project_manager = ?, 
                expected_completion = ?, actual_completion = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """ if is_sqlite else """
            UPDATE projects
            SET status = %s, progress_percentage = %s, remarks = %s, project_manager = %s, 
                expected_completion = %s, actual_completion = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """
        cur.execute(update_query, (new_status, progress, remarks, manager, expected_completion, actual_comp, project_id))
        
        # Log Timeline Activity if status or progress changed
        if old_status != new_status or old_progress != progress:
            activity_type = "Status Changed"
            desc = f"Project status updated from '{old_status}' ({int(old_progress)}%) to '{new_status}' ({progress}%)."
            if new_status == "Completed":
                activity_type = "Completed"
                desc = "Project execution completed and commissioned successfully."
            elif new_status == "Site Survey" and old_status != "Site Survey":
                activity_type = "Survey Scheduled"
                desc = "Technical site survey execution scheduled."
            elif new_status == "Engineering" and old_status != "Engineering":
                activity_type = "Engineering Started"
                desc = "Detailed layout design and electrical coupling blueprints started."
            elif new_status == "Procurement" and old_status != "Procurement":
                activity_type = "Procurement Started"
                desc = "Procurement phase initiated for modules, inverters, and BOS."
            elif new_status == "Installation" and old_status != "Installation":
                activity_type = "Installation Started"
                desc = "Rooftop structures and solar array electrical wiring installation started."
            elif new_status == "Testing & Commissioning" and old_status != "Testing & Commissioning":
                activity_type = "Commissioning Started"
                desc = "Grid coupling synchronization tests and testing started."
                
            activity_query = """
                INSERT INTO project_activities (project_id, activity_type, description, created_by, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);
            """ if is_sqlite else """
                INSERT INTO project_activities (project_id, activity_type, description, created_by, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP);
            """
            cur.execute(activity_query, (project_id, activity_type, desc, actor))
            
            # Log on site activities
            if s_id:
                site_log = """
                    INSERT INTO site_activities (site_id, activity_type, description, created_by, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);
                """ if is_sqlite else """
                    INSERT INTO site_activities (site_id, activity_type, description, created_by, created_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP);
                """
                cur.execute(site_log, (s_id, "Project Update", f"Project state: {new_status} ({progress}% progress).", actor))
                
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating project status: {e}")
        return False
    finally:
        conn.close()


def add_project_document(
    project_id: str,
    document_type: str,
    original_filename: str,
    stored_filename: str,
    file_path: str,
    file_size: int,
    uploaded_by: str = "System"
) -> bool:
    """Register uploaded file metadata inside the database and log activity."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        insert_query = """
            INSERT INTO project_documents (
                project_id, document_type, original_filename, stored_filename, file_path, file_size, uploaded_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
        """ if is_sqlite else """
            INSERT INTO project_documents (
                project_id, document_type, original_filename, stored_filename, file_path, file_size, uploaded_by, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
        """
        cur.execute(insert_query, (project_id, document_type, original_filename, stored_filename, file_path, file_size, uploaded_by))
        
        # Log timeline activity
        activity_query = """
            INSERT INTO project_activities (project_id, activity_type, description, created_by, created_at)
            VALUES (?, 'Document Uploaded', ?, ?, CURRENT_TIMESTAMP);
        """ if is_sqlite else """
            INSERT INTO project_activities (project_id, activity_type, description, created_by, created_at)
            VALUES (%s, 'Document Uploaded', %s, %s, CURRENT_TIMESTAMP);
        """
        cur.execute(activity_query, (
            project_id,
            f"{document_type} file uploaded: {original_filename}",
            uploaded_by
        ))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error registering project document: {e}")
        return False
    finally:
        conn.close()


def get_project_activities(project_id: str) -> List[Dict[str, Any]]:
    """Retrieve chronological activity log for a specific project."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    result = []
    try:
        cur = conn.cursor()
        query = """
            SELECT * FROM project_activities
            WHERE project_id = ?
            ORDER BY created_at DESC, id DESC;
        """ if is_sqlite else """
            SELECT * FROM project_activities
            WHERE project_id = %s
            ORDER BY created_at DESC, id DESC;
        """
        cur.execute(query, (project_id,))
        rows = cur.fetchall()
        for r in rows:
            result.append({
                "id": r["id"],
                "activity_type": r["activity_type"],
                "description": r["description"],
                "created_by": r["created_by"],
                "created_at": r["created_at"]
            })
        return result
    except Exception as e:
        print(f"Error fetching project activities: {e}")
        return []
    finally:
        conn.close()


def get_project_documents(project_id: str) -> List[Dict[str, Any]]:
    """Retrieve list of files uploaded for this project."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    result = []
    try:
        cur = conn.cursor()
        query = """
            SELECT * FROM project_documents
            WHERE project_id = ?
            ORDER BY created_at DESC;
        """ if is_sqlite else """
            SELECT * FROM project_documents
            WHERE project_id = %s
            ORDER BY created_at DESC;
        """
        cur.execute(query, (project_id,))
        rows = cur.fetchall()
        for r in rows:
            result.append({
                "id": r["id"],
                "document_type": r["document_type"],
                "original_filename": r["original_filename"],
                "stored_filename": r["stored_filename"],
                "file_path": r["file_path"],
                "file_size": r["file_size"],
                "uploaded_by": r["uploaded_by"],
                "created_at": r["created_at"]
            })
        return result
    except Exception as e:
        print(f"Error fetching project documents: {e}")
        return []
    finally:
        conn.close()


def get_project_dashboard_kpis() -> List[Dict[str, Any]]:
    """Compiles operational project metrics for the main executive insights feed."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # Active Projects (status not Completed or Cancelled)
        cur.execute("SELECT COUNT(*) FROM projects WHERE status NOT IN ('Completed', 'Cancelled');")
        active_cnt = cur.fetchone()[0] if is_sqlite else (cur.fetchone()['count'] if isinstance(cur.fetchone(), dict) else cur.fetchone()[0])
        
        # Completed Projects
        cur.execute("SELECT COUNT(*) FROM projects WHERE status = 'Completed';")
        comp_cnt = cur.fetchone()[0] if is_sqlite else (cur.fetchone()['count'] if isinstance(cur.fetchone(), dict) else cur.fetchone()[0])
        
        # Projects on Hold
        cur.execute("SELECT COUNT(*) FROM projects WHERE status = 'On Hold';")
        hold_cnt = cur.fetchone()[0] if is_sqlite else (cur.fetchone()['count'] if isinstance(cur.fetchone(), dict) else cur.fetchone()[0])
        
        # Installed Capacity (Completed project MW capacity)
        # Convert capacity_kw to MW
        cur.execute("SELECT COALESCE(SUM(capacity_kw), 0) FROM projects WHERE status = 'Completed';")
        inst_kw = cur.fetchone()[0] if is_sqlite else (cur.fetchone()['sum'] if isinstance(cur.fetchone(), dict) else cur.fetchone()[0])
        inst_mw = round(float(inst_kw) / 1000.0, 2)
        
        # Pipeline Capacity (Active projects capacity in MW)
        cur.execute("SELECT COALESCE(SUM(capacity_kw), 0) FROM projects WHERE status NOT IN ('Completed', 'Cancelled', 'On Hold');")
        pipe_kw = cur.fetchone()[0] if is_sqlite else (cur.fetchone()['sum'] if isinstance(cur.fetchone(), dict) else cur.fetchone()[0])
        pipe_mw = round(float(pipe_kw) / 1000.0, 2)
        
        # Project Revenue (Total contract values of active & completed projects)
        cur.execute("SELECT COALESCE(SUM(contract_value), 0) FROM projects WHERE status != 'Cancelled';")
        rev_val = cur.fetchone()[0] if is_sqlite else (cur.fetchone()['sum'] if isinstance(cur.fetchone(), dict) else cur.fetchone()[0])
        
        return [
            {
                "label": "Active Projects",
                "value": str(active_cnt),
                "delta": "In Progress",
                "tone": "up" if active_cnt > 0 else "neutral",
                "icon": "construction",
            },
            {
                "label": "Completed Projects",
                "value": str(comp_cnt),
                "delta": "Commissioned",
                "tone": "up" if comp_cnt > 0 else "neutral",
                "icon": "task_alt",
            },
            {
                "label": "Projects On Hold",
                "value": str(hold_cnt),
                "delta": "Attention Needed",
                "tone": "down" if hold_cnt > 0 else "neutral",
                "icon": "pause_circle",
            },
            {
                "label": "Installed Capacity",
                "value": f"{inst_mw} MW",
                "delta": "Online Grid",
                "tone": "up" if inst_mw > 0 else "neutral",
                "icon": "electric_bolt",
            },
            {
                "label": "Pipeline Capacity",
                "value": f"{pipe_mw} MW",
                "delta": "Active Builds",
                "tone": "up" if pipe_mw > 0 else "neutral",
                "icon": "pending_actions",
            },
            {
                "label": "Project Revenue",
                "value": f"${float(rev_val):,.2f}" if rev_val else "$0.00",
                "delta": "Contract Value",
                "tone": "up" if rev_val > 0 else "neutral",
                "icon": "monetization_on",
            }
        ]
    except Exception as e:
        print(f"Error compiling project dashboard KPIs: {e}")
        return []
    finally:
        conn.close()


def get_project_reports_stats() -> Dict[str, Any]:
    """Compiles statistics for reports charts by grouping parameters by status."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # 1. Projects by Status, Capacity by Status, Revenue by Status
        status_query = """
            SELECT status, 
                   COUNT(*) as project_count, 
                   COALESCE(SUM(capacity_kw), 0) as total_capacity,
                   COALESCE(SUM(contract_value), 0) as total_revenue
            FROM projects
            GROUP BY status;
        """
        cur.execute(status_query)
        rows = cur.fetchall()
        
        by_status = []
        for r in rows:
            cap_kw = r["total_capacity"] if is_sqlite else (r["total_capacity"] if isinstance(r, dict) else r[2])
            by_status.append({
                "status": r["status"] if is_sqlite else (r["status"] if isinstance(r, dict) else r[0]),
                "count": r["project_count"] if is_sqlite else (r["project_count"] if isinstance(r, dict) else r[1]),
                "capacity_mw": round(float(cap_kw) / 1000.0, 2),
                "revenue": float(r["total_revenue"] if is_sqlite else (r["total_revenue"] if isinstance(r, dict) else r[3]))
            })
            
        # 2. Monthly Project Creation
        # SQLite
        monthly_query = """
            SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
            FROM projects
            GROUP BY month
            ORDER BY month ASC LIMIT 6;
        """ if is_sqlite else """
            SELECT to_char(created_at, 'YYYY-MM') as month, COUNT(*) as count
            FROM projects
            GROUP BY month
            ORDER BY month ASC LIMIT 6;
        """
        cur.execute(monthly_query)
        m_rows = cur.fetchall()
        
        monthly_creation = []
        for r in m_rows:
            monthly_creation.append({
                "month": r["month"] if is_sqlite else (r["month"] if isinstance(r, dict) else r[0]),
                "count": r["count"] if is_sqlite else (r["count"] if isinstance(r, dict) else r[1])
            })
            
        # Default if empty
        if not monthly_creation:
            current_month = datetime.now().strftime("%Y-%m")
            monthly_creation = [{"month": current_month, "count": 0}]

        # 3. Monthly Proposal/Lead conversion
        lead_query = """
            SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
            FROM proposals
            GROUP BY month
            ORDER BY month ASC LIMIT 6;
        """ if is_sqlite else """
            SELECT to_char(created_at, 'YYYY-MM') as month, COUNT(*) as count
            FROM proposals
            GROUP BY month
            ORDER BY month ASC LIMIT 6;
        """
        cur.execute(lead_query)
        l_rows = cur.fetchall()
        
        lead_conversion = []
        for r in l_rows:
            lead_conversion.append({
                "month": r["month"] if is_sqlite else (r["month"] if isinstance(r, dict) else r[0]),
                "count": r["count"] if is_sqlite else (r["count"] if isinstance(r, dict) else r[1])
            })
            
        if not lead_conversion:
            lead_conversion = [{"month": datetime.now().strftime("%Y-%m"), "count": 0}]

        # 4. Capacity by Sector Grouping
        sector_query = """
            SELECT category, COALESCE(SUM(capacity_mw), 0) as total_capacity
            FROM customers
            WHERE is_deleted = 0
            GROUP BY category;
        """
        cur.execute(sector_query)
        s_rows = cur.fetchall()
        
        sector_capacity = []
        for r in s_rows:
            sector_capacity.append({
                "category": r["category"] if is_sqlite else (r["category"] if isinstance(r, dict) else r[0]),
                "capacity": float(r["total_capacity"] if is_sqlite else (r["total_capacity"] if isinstance(r, dict) else r[1]))
            })
            
        return {
            "by_status": by_status,
            "monthly_creation": monthly_creation,
            "lead_conversion": lead_conversion,
            "sector_capacity": sector_capacity
        }
    except Exception as e:
        print(f"Error fetching project reports stats: {e}")
        return {"by_status": [], "monthly_creation": [], "lead_conversion": [], "sector_capacity": []}
    finally:
        conn.close()


def has_active_project_for_proposal(proposal_id: str) -> Tuple[bool, Optional[str]]:
    """Helper checks if an active project exists referencing this proposal and returns (has_active, project_id)."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = "SELECT id FROM projects WHERE proposal_id = ? AND status != 'Cancelled' LIMIT 1;" if is_sqlite else "SELECT id FROM projects WHERE proposal_id = %s AND status != 'Cancelled' LIMIT 1;"
        cur.execute(query, (proposal_id,))
        row = cur.fetchone()
        if row:
            p_id = row[0] if is_sqlite else (row["id"] if isinstance(row, dict) else row[0])
            return True, p_id
        return False, None
    except Exception as e:
        print(f"Error checking project status for proposal: {e}")
        return False, None
    finally:
        conn.close()
