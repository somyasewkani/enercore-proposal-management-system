"""
Enercore AI Solar Proposal Generator
services/proposal_service.py

Service layer for managing database persistence of sites, electricity bills,
OCR results, proposals, proposal versions, and accepted projects.
"""

import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from database.connection import get_connection


def create_site(data: Dict[str, Any]) -> str:
    """Create a new site for a customer within a transaction block."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # Check duplicate name under customer_id
        check_query = "SELECT COUNT(*) FROM sites WHERE customer_id = ? AND name = ? AND is_deleted = 0;" if is_sqlite else "SELECT COUNT(*) FROM sites WHERE customer_id = %s AND name = %s AND is_deleted = 0;"
        cur.execute(check_query, (data["customer_id"], data["name"]))
        if cur.fetchone()[0] > 0:
            raise ValueError(f"A site named '{data['name']}' already exists for this client.")

        cur.execute("SELECT COUNT(*) FROM sites;")
        count = cur.fetchone()[0]
        site_id = f"site_{count + 1}"

        query = """
            INSERT INTO sites (id, customer_id, name, address_street, address_city, address_state, address_zip, contact_person, contact_number, status, is_archived, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0);
        """ if is_sqlite else """
            INSERT INTO sites (id, customer_id, name, address_street, address_city, address_state, address_zip, contact_person, contact_number, status, is_archived, is_deleted)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0);
        """
        cur.execute(query, (
            site_id,
            data["customer_id"],
            data["name"],
            data.get("address_street"),
            data.get("address_city"),
            data.get("address_state"),
            data.get("address_zip"),
            data.get("contact_person"),
            data.get("contact_number"),
            data.get("status", "New")
        ))
        
        # Log Site Created activity inside the transaction
        log_query = """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (%s, %s, %s, %s);
        """
        cur.execute(log_query, (site_id, 'Site Created', f"Site '{data['name']}' was created.", data.get('user', 'System')))

        conn.commit()
        return site_id
    except Exception as e:
        conn.rollback()
        print(f"Error creating site, rolled back: {e}")
        raise e
    finally:
        conn.close()


def update_site(site_id: str, data: Dict[str, Any]) -> bool:
    """Update site attributes and log site updated activity."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()

        # Check duplicate name under customer_id (excluding self)
        check_query = """
            SELECT COUNT(*) FROM sites 
            WHERE customer_id = (SELECT customer_id FROM sites WHERE id = ?) 
              AND name = ? AND id != ? AND is_deleted = 0;
        """ if is_sqlite else """
            SELECT COUNT(*) FROM sites 
            WHERE customer_id = (SELECT customer_id FROM sites WHERE id = %s) 
              AND name = %s AND id != %s AND is_deleted = 0;
        """
        cur.execute(check_query, (site_id, data["name"], site_id))
        if cur.fetchone()[0] > 0:
            raise ValueError(f"A site named '{data['name']}' already exists for this client.")

        query = """
            UPDATE sites
            SET name = ?, address_street = ?, address_city = ?, address_state = ?, address_zip = ?, 
                contact_person = ?, contact_number = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """ if is_sqlite else """
            UPDATE sites
            SET name = %s, address_street = %s, address_city = %s, address_state = %s, address_zip = %s, 
                contact_person = %s, contact_number = %s, status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """
        cur.execute(query, (
            data["name"],
            data.get("address_street"),
            data.get("address_city"),
            data.get("address_state"),
            data.get("address_zip"),
            data.get("contact_person"),
            data.get("contact_number"),
            data.get("status", "New"),
            site_id
        ))

        # Log Activity
        log_query = """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (%s, %s, %s, %s);
        """
        cur.execute(log_query, (site_id, 'Site Updated', f"Site details were updated: name='{data['name']}', status='{data.get('status')}'", data.get('user', 'System')))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating site, rolled back: {e}")
        raise e
    finally:
        conn.close()


def archive_site(site_id: str, user: str = 'System') -> bool:
    """Archive a site (is_archived = 1) and log activity."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = "UPDATE sites SET is_archived = 1 WHERE id = ?;" if is_sqlite else "UPDATE sites SET is_archived = 1 WHERE id = %s;"
        cur.execute(query, (site_id,))

        log_query = """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (?, 'Site Archived', 'Site was archived.', ?);
        """ if is_sqlite else """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (%s, 'Site Archived', 'Site was archived.', %s);
        """
        cur.execute(log_query, (site_id, user))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error archiving site: {e}")
        return False
    finally:
        conn.close()


def restore_site(site_id: str, user: str = 'System') -> bool:
    """Restore a site from archive or soft delete status."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = "UPDATE sites SET is_archived = 0, is_deleted = 0 WHERE id = ?;" if is_sqlite else "UPDATE sites SET is_archived = 0, is_deleted = 0 WHERE id = %s;"
        cur.execute(query, (site_id,))

        log_query = """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (?, 'Site Restored', 'Site was restored to active status.', ?);
        """ if is_sqlite else """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (%s, 'Site Restored', 'Site was restored to active status.', %s);
        """
        cur.execute(log_query, (site_id, user))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error restoring site: {e}")
        return False
    finally:
        conn.close()


def delete_site(site_id: str, user: str = 'System') -> bool:
    """Soft delete a site (is_deleted = 1) and log activity."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = "UPDATE sites SET is_deleted = 1 WHERE id = ?;" if is_sqlite else "UPDATE sites SET is_deleted = 1 WHERE id = %s;"
        cur.execute(query, (site_id,))

        log_query = """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (?, 'Site Deleted', 'Site was soft-deleted.', ?);
        """ if is_sqlite else """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (%s, 'Site Deleted', 'Site was soft-deleted.', %s);
        """
        cur.execute(log_query, (site_id, user))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error soft deleting site: {e}")
        return False
    finally:
        conn.close()


def get_site_details(site_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve details for a single site."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = """
            SELECT s.*, c.name as customer_name
            FROM sites s
            JOIN customers c ON s.customer_id = c.id
            WHERE s.id = ?;
        """ if is_sqlite else """
            SELECT s.*, c.name as customer_name
            FROM sites s
            JOIN customers c ON s.customer_id = c.id
            WHERE s.id = %s;
        """
        cur.execute(query, (site_id,))
        r = cur.fetchone()
        if not r:
            return None
        return {
            "id": r["id"],
            "customer_id": r["customer_id"],
            "customer_name": r["customer_name"],
            "name": r["name"],
            "address_street": r["address_street"] or "",
            "address_city": r["address_city"] or "",
            "address_state": r["address_state"] or "",
            "address_zip": r["address_zip"] or "",
            "contact_person": r["contact_person"] or "",
            "contact_number": r["contact_number"] or "",
            "status": r["status"] or "New",
            "is_archived": r["is_archived"] or 0,
            "is_deleted": r["is_deleted"] or 0,
            "created_at": r["created_at"],
            "updated_at": r["updated_at"]
        }
    except Exception as e:
        print(f"Error getting site details: {e}")
        return None
    finally:
        conn.close()


def get_sites_by_customer(customer_id: str, include_deleted: bool = False, include_archived: bool = True) -> List[Dict[str, Any]]:
    """Fetch all sites belonging to a customer."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    results = []
    try:
        cur = conn.cursor()
        
        where_clauses = ["customer_id = ?"] if is_sqlite else ["customer_id = %s"]
        params = [customer_id]

        if not include_deleted:
            where_clauses.append("is_deleted = 0")
        if not include_archived:
            where_clauses.append("is_archived = 0")

        query = f"SELECT * FROM sites WHERE {' AND '.join(where_clauses)} ORDER BY created_at DESC;"
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        for r in rows:
            results.append({
                "id": r["id"],
                "customer_id": r["customer_id"],
                "name": r["name"],
                "address_street": r["address_street"] or "",
                "address_city": r["address_city"] or "",
                "address_state": r["address_state"] or "",
                "address_zip": r["address_zip"] or "",
                "contact_person": r["contact_person"] or "",
                "contact_number": r["contact_number"] or "",
                "status": r["status"] or "New",
                "is_archived": r["is_archived"] or 0,
                "is_deleted": r["is_deleted"] or 0,
                "created_at": r["created_at"]
            })
        return results
    except Exception as e:
        print(f"Error getting sites: {e}")
        return []
    finally:
        conn.close()


def log_site_activity(site_id: str, activity_type: str, description: str, created_by: str = 'System') -> bool:
    """Insert a new timeline activity record for a site."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (%s, %s, %s, %s);
        """
        cur.execute(query, (site_id, activity_type, description, created_by))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error logging site activity: {e}")
        return False
    finally:
        conn.close()


def get_site_activities(site_id: str) -> List[Dict[str, Any]]:
    """Retrieve all timeline activities for a site sorted by timestamp."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    results = []
    try:
        cur = conn.cursor()
        query = "SELECT * FROM site_activities WHERE site_id = ? ORDER BY id DESC;" if is_sqlite else "SELECT * FROM site_activities WHERE site_id = %s ORDER BY id DESC;"
        cur.execute(query, (site_id,))
        rows = cur.fetchall()
        for r in rows:
            results.append({
                "id": r["id"],
                "site_id": r["site_id"],
                "activity_type": r["activity_type"],
                "description": r["description"] or "",
                "created_by": r["created_by"] or "System",
                "created_at": r["created_at"]
            })
        return results
    except Exception as e:
        print(f"Error getting site activities: {e}")
        return []
    finally:
        conn.close()


def search_sites_db(search_q: str = None, customer_id: str = None, state: str = None, status: str = None) -> List[Dict[str, Any]]:
    """Query, search, and filter sites dynamically."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    results = []
    try:
        cur = conn.cursor()
        where_clauses = ["s.is_deleted = 0"]
        params = []

        if search_q and search_q.strip():
            q = f"%{search_q.strip()}%"
            where_clauses.append("(s.name LIKE ? OR c.name LIKE ?)" if is_sqlite else "(s.name ILIKE %s OR c.name ILIKE %s)")
            params.extend([q, q])

        if customer_id and customer_id != "all":
            where_clauses.append("s.customer_id = ?" if is_sqlite else "s.customer_id = %s")
            params.append(customer_id)

        if state and state != "all":
            where_clauses.append("s.address_state = ?" if is_sqlite else "s.address_state = %s")
            params.append(state)

        if status and status != "all":
            where_clauses.append("s.status = ?" if is_sqlite else "s.status = %s")
            params.append(status)

        query = f"""
            SELECT s.*, c.name as customer_name
            FROM sites s
            JOIN customers c ON s.customer_id = c.id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY s.created_at DESC;
        """
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        for r in rows:
            results.append({
                "id": r["id"],
                "customer_id": r["customer_id"],
                "customer_name": r["customer_name"],
                "name": r["name"],
                "address_street": r["address_street"] or "",
                "address_city": r["address_city"] or "",
                "address_state": r["address_state"] or "",
                "address_zip": r["address_zip"] or "",
                "status": r["status"] or "New",
                "is_archived": r["is_archived"] or 0,
                "created_at": r["created_at"]
            })
        return results
    except Exception as e:
        print(f"Error searching sites: {e}")
        return []
    finally:
        conn.close()


def get_customer_stats(customer_id: str) -> Dict[str, Any]:
    """Retrieve aggregated customer statistics (Total Sites, Bills, Proposals, Installed Capacity, Latest Activity)."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # 1. Total Sites
        q1 = "SELECT COUNT(*) FROM sites WHERE customer_id = ? AND is_deleted = 0;" if is_sqlite else "SELECT COUNT(*) FROM sites WHERE customer_id = %s AND is_deleted = 0;"
        cur.execute(q1, (customer_id,))
        total_sites = cur.fetchone()[0]

        # 2. Total Bills
        q2 = """
            SELECT COUNT(*) FROM electricity_bills b
            JOIN sites s ON b.site_id = s.id
            WHERE s.customer_id = ? AND s.is_deleted = 0;
        """ if is_sqlite else """
            SELECT COUNT(*) FROM electricity_bills b
            JOIN sites s ON b.site_id = s.id
            WHERE s.customer_id = %s AND s.is_deleted = 0;
        """
        cur.execute(q2, (customer_id,))
        total_bills = cur.fetchone()[0]

        # 3. Total Proposals
        q3 = "SELECT COUNT(*) FROM proposals WHERE customer_id = ?;" if is_sqlite else "SELECT COUNT(*) FROM proposals WHERE customer_id = %s;"
        cur.execute(q3, (customer_id,))
        total_proposals = cur.fetchone()[0]

        # 4. Total Capacity (Installed/Won)
        q4 = """
            SELECT COALESCE(SUM(v.system_size_kwp), 0)
            FROM proposals p
            JOIN proposal_versions v ON p.id = v.proposal_id AND v.version_number = 1
            WHERE p.customer_id = ? AND p.status = 'Won';
        """ if is_sqlite else """
            SELECT COALESCE(SUM(v.system_size_kwp), 0)
            FROM proposals p
            JOIN proposal_versions v ON p.id = v.proposal_id AND v.version_number = 1
            WHERE p.customer_id = %s AND p.status = 'Won';
        """
        cur.execute(q4, (customer_id,))
        total_capacity_kwp = cur.fetchone()[0]
        total_capacity_mw = round(float(total_capacity_kwp) / 1000.0, 2)

        # 5. Latest Activity
        q5 = """
            SELECT a.activity_type, a.created_at FROM site_activities a
            JOIN sites s ON a.site_id = s.id
            WHERE s.customer_id = ?
            ORDER BY a.created_at DESC LIMIT 1;
        """ if is_sqlite else """
            SELECT a.activity_type, a.created_at FROM site_activities a
            JOIN sites s ON a.site_id = s.id
            WHERE s.customer_id = %s
            ORDER BY a.created_at DESC LIMIT 1;
        """
        cur.execute(q5, (customer_id,))
        act_row = cur.fetchone()
        latest_activity = "No activity logged"
        if act_row:
            latest_activity = f"{act_row[0]} ({act_row[1][:10]})" if is_sqlite else (f"{act_row['activity_type']} ({act_row['created_at'].strftime('%Y-%m-%d')})" if isinstance(act_row, dict) else f"{act_row[0]} ({act_row[1][:10]})")

        return {
            "total_sites": total_sites,
            "total_bills": total_bills,
            "total_proposals": total_proposals,
            "total_capacity_mw": total_capacity_mw,
            "latest_activity": latest_activity
        }
    except Exception as e:
        print(f"Error fetching customer stats: {e}")
        return {
            "total_sites": 0,
            "total_bills": 0,
            "total_proposals": 0,
            "total_capacity_mw": 0.0,
            "latest_activity": "No activity logged"
        }
    finally:
        conn.close()


def create_electricity_bill(data: Dict[str, Any]) -> str:
    """Create a new electricity bill record for a site within a transaction block."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM electricity_bills;")
        count = cur.fetchone()[0]
        bill_id = f"bill_{count + 1}"

        query = """
            INSERT INTO electricity_bills (id, site_id, billing_period_start, billing_period_end, energy_consumption_kwh, total_cost, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO electricity_bills (id, site_id, billing_period_start, billing_period_end, energy_consumption_kwh, total_cost, file_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        cur.execute(query, (
            bill_id,
            data["site_id"],
            data.get("billing_period_start"),
            data.get("billing_period_end"),
            float(data.get("energy_consumption_kwh", 0)),
            float(data.get("total_cost", 0)),
            data.get("file_path")
        ))
        
        # Log timeline event
        log_query = """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (?, 'Bill Uploaded', ?, ?);
        """ if is_sqlite else """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (%s, 'Bill Uploaded', %s, %s);
        """
        cur.execute(log_query, (data["site_id"], f"Electricity bill uploaded: {os.path.basename(data.get('file_path','statement.pdf'))}", data.get('user', 'System')))

        # Automatically transition site status to 'Bill Uploaded'
        status_query = "UPDATE sites SET status = 'Bill Uploaded' WHERE id = ?;" if is_sqlite else "UPDATE sites SET status = 'Bill Uploaded' WHERE id = %s;"
        cur.execute(status_query, (data["site_id"],))

        conn.commit()
        return bill_id
    except Exception as e:
        conn.rollback()
        print(f"Error creating bill, rolled back: {e}")
        return ""
    finally:
        conn.close()


def get_bills_by_site(site_id: str) -> List[Dict[str, Any]]:
    """Fetch all bills belonging to a site."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    results = []
    try:
        cur = conn.cursor()
        query = "SELECT * FROM electricity_bills WHERE site_id = ? ORDER BY created_at DESC;" if is_sqlite else "SELECT * FROM electricity_bills WHERE site_id = %s ORDER BY created_at DESC;"
        cur.execute(query, (site_id,))
        rows = cur.fetchall()
        for r in rows:
            results.append({
                "id": r["id"],
                "site_id": r["site_id"],
                "billing_period_start": r["billing_period_start"],
                "billing_period_end": r["billing_period_end"],
                "energy_consumption_kwh": r["energy_consumption_kwh"],
                "total_cost": r["total_cost"],
                "file_path": r["file_path"],
                "created_at": r["created_at"]
            })
        return results
    except Exception as e:
        print(f"Error getting bills: {e}")
        return []
    finally:
        conn.close()


def save_ocr_result(bill_id: str, extracted_text: str, json_data: str) -> bool:
    """Save parsed OCR metrics for a specific bill within a transaction block."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = """
            INSERT INTO ocr_results (bill_id, extracted_text, json_data)
            VALUES (?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO ocr_results (bill_id, extracted_text, json_data)
            VALUES (%s, %s, %s);
        """
        cur.execute(query, (bill_id, extracted_text, json_data))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error saving OCR result, rolled back: {e}")
        return False
    finally:
        conn.close()


def get_ocr_result(bill_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve OCR results for a specific bill."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = "SELECT * FROM ocr_results WHERE bill_id = ?;" if is_sqlite else "SELECT * FROM ocr_results WHERE bill_id = %s;"
        cur.execute(query, (bill_id,))
        r = cur.fetchone()
        if not r:
            return None
        return {
            "id": r["id"],
            "bill_id": r["bill_id"],
            "extracted_text": r["extracted_text"],
            "json_data": r["json_data"],
            "processed_at": r["processed_at"]
        }
    except Exception as e:
        print(f"Error getting OCR result: {e}")
        return None
    finally:
        conn.close()


def create_proposal(data: Dict[str, Any]) -> str:
    """Create a new proposal and its initial version records within a single transaction block."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM proposals;")
        count = cur.fetchone()[0]
        proposal_id = f"EC-{1000 + count + 1}-X"

        # Step 1: Insert core proposal record
        query = """
            INSERT INTO proposals (id, customer_id, site_id, name, status)
            VALUES (?, ?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO proposals (id, customer_id, site_id, name, status)
            VALUES (%s, %s, %s, %s, %s);
        """
        cur.execute(query, (
            proposal_id,
            data["customer_id"],
            data.get("site_id"),
            data["name"],
            data.get("status", "Draft")
        ))

        # Step 2: Insert initial proposal version record
        version_query = """
            INSERT INTO proposal_versions (proposal_id, version_number, system_size_kwp, annual_yield_kwh, project_cost, payback_years, irr)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO proposal_versions (proposal_id, version_number, system_size_kwp, annual_yield_kwh, project_cost, payback_years, irr)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        cur.execute(version_query, (
            proposal_id,
            1,
            float(data.get("system_size_kwp", 0)),
            float(data.get("annual_yield_kwh", 0)),
            float(data.get("project_cost", 0)),
            float(data.get("payback_years", 0)),
            float(data.get("irr", 0))
        ))

        # Log timeline event if site is specified
        if data.get("site_id"):
            log_query = """
                INSERT INTO site_activities (site_id, activity_type, description, created_by)
                VALUES (?, 'Proposal Generated', ?, ?);
            """ if is_sqlite else """
                INSERT INTO site_activities (site_id, activity_type, description, created_by)
                VALUES (%s, 'Proposal Generated', %s, %s);
            """
            cur.execute(log_query, (data["site_id"], f"Solar Proposal generated: {proposal_id} ({data['name']})", data.get('user', 'System')))

            # Update site status
            status_query = "UPDATE sites SET status = 'Proposal Generated' WHERE id = ?;" if is_sqlite else "UPDATE sites SET status = 'Proposal Generated' WHERE id = %s;"
            cur.execute(status_query, (data["site_id"],))

        # Commit both statements atomically
        conn.commit()
        return proposal_id
    except Exception as e:
        conn.rollback()
        print(f"Error creating proposal, rolled back transaction: {e}")
        return ""
    finally:
        conn.close()


def get_all_proposals() -> List[Dict[str, Any]]:
    """Retrieve all generated client proposals."""
    conn = get_connection()
    results = []
    try:
        cur = conn.cursor()
        query = """
            SELECT p.id, p.name, p.status, p.created_at, c.name as client_name, v.system_size_kwp, v.project_cost
            FROM proposals p
            JOIN customers c ON p.customer_id = c.id
            LEFT JOIN proposal_versions v ON p.id = v.proposal_id AND v.version_number = 1
            ORDER BY p.created_at DESC;
        """
        cur.execute(query)
        rows = cur.fetchall()
        for r in rows:
            results.append({
                "id": r["id"],
                "name": r["name"],
                "client_name": r["client_name"],
                "status": r["status"],
                "capacity": r["system_size_kwp"] or 0.0,
                "total_cost": f"${r['project_cost']:,.2f}" if r["project_cost"] else "$0.00",
                "date_created": r["created_at"]
            })
        return results
    except Exception as e:
        print(f"Error getting proposals: {e}")
        return []
    finally:
        conn.close()


def get_bill_analysis_data(bill_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve electricity bill and its corresponding OCR results."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = """
            SELECT b.id, b.file_path, o.extracted_text, o.json_data
            FROM electricity_bills b
            LEFT JOIN ocr_results o ON b.id = o.bill_id
            WHERE b.id = ?;
        """ if is_sqlite else """
            SELECT b.id, b.file_path, o.extracted_text, o.json_data
            FROM electricity_bills b
            LEFT JOIN ocr_results o ON b.id = o.bill_id
            WHERE b.id = %s;
        """
        cur.execute(query, (bill_id,))
        r = cur.fetchone()
        if not r:
            return None

        ocr_json = {}
        if r["json_data"]:
            try:
                ocr_json = json.loads(r["json_data"])
            except Exception:
                pass

        filename = os.path.basename(r["file_path"] or "statement.pdf")
        return {
            'filename': filename,
            'bill_id': r["id"],
            'plant_size': ocr_json.get('plant_size', '250'),
            'daily_yield': ocr_json.get('daily_yield', '1,125'),
            'annual_savings': ocr_json.get('annual_savings', '42,500'),
            'payback': ocr_json.get('payback', '3.8'),
            'irr': ocr_json.get('irr', '24.6%')
        }
    except Exception as e:
        print(f"Error getting bill analysis data: {e}")
        return None
    finally:
        conn.close()


def get_latest_electricity_bill() -> Optional[str]:
    """Return bill_id of the latest utility statement in the database."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM electricity_bills ORDER BY created_at DESC LIMIT 1;")
        r = cur.fetchone()
        if r:
            return r[0] if is_sqlite else (r['id'] if isinstance(r, dict) else r[0])
        return None
    except Exception as e:
        print(f"Error getting latest bill: {e}")
        return None
    finally:
        conn.close()
