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

        # Check duplicate billing month/year for this site (is_deleted = 0)
        check_query = """
            SELECT COUNT(*) FROM electricity_bills 
            WHERE site_id = ? AND billing_month = ? AND billing_year = ? AND is_deleted = 0;
        """ if is_sqlite else """
            SELECT COUNT(*) FROM electricity_bills 
            WHERE site_id = %s AND billing_month = %s AND billing_year = %s AND is_deleted = 0;
        """
        cur.execute(check_query, (data["site_id"], int(data["billing_month"]), int(data["billing_year"])))
        if cur.fetchone()[0] > 0:
            raise ValueError(f"A bill for {data['billing_month']}/{data['billing_year']} has already been uploaded for this site.")

        cur.execute("SELECT COUNT(*) FROM electricity_bills;")
        count = cur.fetchone()[0]
        bill_id = f"bill_{count + 1}"

        query = """
            INSERT INTO electricity_bills (
                id, site_id, billing_month, billing_year, billing_period_start, billing_period_end, 
                original_filename, stored_filename, file_path, file_type, file_size, bill_status, 
                ocr_status, notes, is_deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0);
        """ if is_sqlite else """
            INSERT INTO electricity_bills (
                id, site_id, billing_month, billing_year, billing_period_start, billing_period_end, 
                original_filename, stored_filename, file_path, file_type, file_size, bill_status, 
                ocr_status, notes, is_deleted
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0);
        """
        cur.execute(query, (
            bill_id,
            data["site_id"],
            int(data["billing_month"]),
            int(data["billing_year"]),
            data.get("billing_period_start"),
            data.get("billing_period_end"),
            data.get("original_filename"),
            data.get("stored_filename"),
            data.get("file_path"),
            data.get("file_type"),
            data.get("file_size"),
            data.get("bill_status", "Uploaded"),
            data.get("ocr_status", "Not Started"),
            data.get("notes")
        ))
        
        # Log timeline event
        log_query = """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (?, 'Bill Uploaded', ?, ?);
        """ if is_sqlite else """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (%s, 'Bill Uploaded', %s, %s);
        """
        cur.execute(log_query, (
            data["site_id"], 
            f"Electricity bill uploaded: {data.get('original_filename')} for {data['billing_month']}/{data['billing_year']}.", 
            data.get('user', 'System')
        ))

        # Transition site status to 'Bill Uploaded' if currently New
        status_query = "UPDATE sites SET status = 'Bill Uploaded' WHERE id = ? AND status = 'New';" if is_sqlite else "UPDATE sites SET status = 'Bill Uploaded' WHERE id = %s AND status = 'New';"
        cur.execute(status_query, (data["site_id"],))

        conn.commit()
        return bill_id
    except Exception as e:
        conn.rollback()
        print(f"Error creating bill, rolled back: {e}")
        raise e
    finally:
        conn.close()


def update_electricity_bill(bill_id: str, data: Dict[str, Any]) -> bool:
    """Update electricity bill attributes and log updated activity."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # Fetch current details to check if month/year are changing
        get_q = "SELECT site_id, billing_month, billing_year, original_filename FROM electricity_bills WHERE id = ?;" if is_sqlite else "SELECT site_id, billing_month, billing_year, original_filename FROM electricity_bills WHERE id = %s;"
        cur.execute(get_q, (bill_id,))
        current = cur.fetchone()
        if not current:
            raise ValueError("Bill not found.")
            
        site_id = current[0] if is_sqlite else (current['site_id'] if isinstance(current, dict) else current[0])
        old_month = current[1] if is_sqlite else (current['billing_month'] if isinstance(current, dict) else current[1])
        old_year = current[2] if is_sqlite else (current['billing_year'] if isinstance(current, dict) else current[2])

        new_month = int(data.get("billing_month", old_month))
        new_year = int(data.get("billing_year", old_year))

        if new_month != old_month or new_year != old_year:
            # Validate duplicate
            check_query = """
                SELECT COUNT(*) FROM electricity_bills 
                WHERE site_id = ? AND billing_month = ? AND billing_year = ? AND id != ? AND is_deleted = 0;
            """ if is_sqlite else """
                SELECT COUNT(*) FROM electricity_bills 
                WHERE site_id = %s AND billing_month = %s AND billing_year = %s AND id != %s AND is_deleted = 0;
            """
            cur.execute(check_query, (site_id, new_month, new_year, bill_id))
            if cur.fetchone()[0] > 0:
                raise ValueError(f"A bill for {new_month}/{new_year} already exists for this site.")

        query = """
            UPDATE electricity_bills
            SET billing_month = ?, billing_year = ?, billing_period_start = ?, billing_period_end = ?, 
                bill_status = ?, ocr_status = ?, ocr_started_at = ?, ocr_completed_at = ?, 
                latest_ocr_result_id = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """ if is_sqlite else """
            UPDATE electricity_bills
            SET billing_month = %s, billing_year = %s, billing_period_start = %s, billing_period_end = %s, 
                bill_status = %s, ocr_status = %s, ocr_started_at = %s, ocr_completed_at = %s, 
                latest_ocr_result_id = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """
        cur.execute(query, (
            new_month,
            new_year,
            data.get("billing_period_start"),
            data.get("billing_period_end"),
            data.get("bill_status", "Uploaded"),
            data.get("ocr_status", "Not Started"),
            data.get("ocr_started_at"),
            data.get("ocr_completed_at"),
            data.get("latest_ocr_result_id"),
            data.get("notes"),
            bill_id
        ))

        # Log timeline event
        log_query = """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (?, 'Bill Updated', ?, ?);
        """ if is_sqlite else """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (%s, 'Bill Updated', %s, %s);
        """
        cur.execute(log_query, (
            site_id,
            f"Electricity bill details updated for {new_month}/{new_year}.",
            data.get("user", "System")
        ))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating bill: {e}")
        raise e
    finally:
        conn.close()


def delete_electricity_bill(bill_id: str, user: str = 'System') -> bool:
    """Soft delete an electricity bill (is_deleted = 1) and log activity."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # Get bill details for logging
        get_q = "SELECT site_id, billing_month, billing_year FROM electricity_bills WHERE id = ?;" if is_sqlite else "SELECT site_id, billing_month, billing_year FROM electricity_bills WHERE id = %s;"
        cur.execute(get_q, (bill_id,))
        current = cur.fetchone()
        if not current:
            return False

        site_id = current[0] if is_sqlite else (current['site_id'] if isinstance(current, dict) else current[0])
        month = current[1] if is_sqlite else (current['billing_month'] if isinstance(current, dict) else current[1])
        year = current[2] if is_sqlite else (current['billing_year'] if isinstance(current, dict) else current[2])

        query = "UPDATE electricity_bills SET is_deleted = 1 WHERE id = ?;" if is_sqlite else "UPDATE electricity_bills SET is_deleted = 1 WHERE id = %s;"
        cur.execute(query, (bill_id,))

        log_query = """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (?, 'Bill Deleted', ?, ?);
        """ if is_sqlite else """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (%s, 'Bill Deleted', %s, %s);
        """
        cur.execute(log_query, (
            site_id,
            f"Electricity bill deleted for {month}/{year}.",
            user
        ))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error deleting bill: {e}")
        return False
    finally:
        conn.close()


def restore_electricity_bill(bill_id: str, user: str = 'System') -> bool:
    """Restore a soft-deleted electricity bill after verifying duplicate naming check."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()

        # Get bill details for validation and logging
        get_q = "SELECT site_id, billing_month, billing_year FROM electricity_bills WHERE id = ?;" if is_sqlite else "SELECT site_id, billing_month, billing_year FROM electricity_bills WHERE id = %s;"
        cur.execute(get_q, (bill_id,))
        current = cur.fetchone()
        if not current:
            raise ValueError("Bill not found.")

        site_id = current[0] if is_sqlite else (current['site_id'] if isinstance(current, dict) else current[0])
        month = current[1] if is_sqlite else (current['billing_month'] if isinstance(current, dict) else current[1])
        year = current[2] if is_sqlite else (current['billing_year'] if isinstance(current, dict) else current[2])

        # Validate duplicate
        check_query = """
            SELECT COUNT(*) FROM electricity_bills 
            WHERE site_id = ? AND billing_month = ? AND billing_year = ? AND id != ? AND is_deleted = 0;
        """ if is_sqlite else """
            SELECT COUNT(*) FROM electricity_bills 
            WHERE site_id = %s AND billing_month = %s AND billing_year = %s AND id != %s AND is_deleted = 0;
        """
        cur.execute(check_query, (site_id, month, year, bill_id))
        if cur.fetchone()[0] > 0:
            raise ValueError(f"Cannot restore. An active bill for {month}/{year} already exists for this site.")

        query = "UPDATE electricity_bills SET is_deleted = 0 WHERE id = ?;" if is_sqlite else "UPDATE electricity_bills SET is_deleted = 0 WHERE id = %s;"
        cur.execute(query, (bill_id,))

        log_query = """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (?, 'Bill Restored', ?, ?);
        """ if is_sqlite else """
            INSERT INTO site_activities (site_id, activity_type, description, created_by)
            VALUES (%s, 'Bill Restored', %s, %s);
        """
        cur.execute(log_query, (
            site_id,
            f"Electricity bill restored for {month}/{year}.",
            user
        ))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error restoring bill: {e}")
        raise e
    finally:
        conn.close()


def get_bill_details(bill_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve metadata and association attributes for a single electricity bill."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = """
            SELECT b.*, s.name as site_name, c.name as customer_name, c.id as customer_id,
                   o.normalized_json, o.ocr_provider, o.ocr_version, o.ocr_confidence, o.duration_ms, o.warnings, o.raw_response,
                   cal.plant_size_kw, cal.recommended_inverter_kw, cal.estimated_monthly_generation, cal.estimated_annual_generation,
                   cal.monthly_savings, cal.annual_savings, cal.system_cost, cal.payback_years, cal.co2_offset, cal.trees_equivalent,
                   cal.calculation_status, cal.warnings as calc_warnings
            FROM electricity_bills b
            JOIN sites s ON b.site_id = s.id
            JOIN customers c ON s.customer_id = c.id
            LEFT JOIN ocr_results o ON b.latest_ocr_result_id = o.id
            LEFT JOIN calculation_results cal ON b.latest_calculation_id = cal.id
            WHERE b.id = ?;
        """ if is_sqlite else """
            SELECT b.*, s.name as site_name, c.name as customer_name, c.id as customer_id,
                   o.normalized_json, o.ocr_provider, o.ocr_version, o.ocr_confidence, o.duration_ms, o.warnings, o.raw_response,
                   cal.plant_size_kw, cal.recommended_inverter_kw, cal.estimated_monthly_generation, cal.estimated_annual_generation,
                   cal.monthly_savings, cal.annual_savings, cal.system_cost, cal.payback_years, cal.co2_offset, cal.trees_equivalent,
                   cal.calculation_status, cal.warnings as calc_warnings
            FROM electricity_bills b
            JOIN sites s ON b.site_id = s.id
            JOIN customers c ON s.customer_id = c.id
            LEFT JOIN ocr_results o ON b.latest_ocr_result_id = o.id
            LEFT JOIN calculation_results cal ON b.latest_calculation_id = cal.id
            WHERE b.id = %s;
        """
        cur.execute(query, (bill_id,))
        r = cur.fetchone()
        if not r:
            return None
        return {
            "id": r["id"],
            "site_id": r["site_id"],
            "customer_id": r["customer_id"],
            "customer_name": r["customer_name"],
            "site_name": r["site_name"],
            "billing_month": r["billing_month"],
            "billing_year": r["billing_year"],
            "billing_period_start": r["billing_period_start"] or "",
            "billing_period_end": r["billing_period_end"] or "",
            "upload_date": r["upload_date"],
            "original_filename": r["original_filename"] or "",
            "stored_filename": r["stored_filename"] or "",
            "file_path": r["file_path"] or "",
            "file_type": r["file_type"] or "",
            "file_size": r["file_size"] or 0,
            "bill_status": r["bill_status"] or "Uploaded",
            "ocr_status": r["ocr_status"] or "Not Started",
            "ocr_started_at": r["ocr_started_at"],
            "ocr_completed_at": r["ocr_completed_at"],
            "latest_ocr_result_id": r["latest_ocr_result_id"],
            "latest_calculation_id": r["latest_calculation_id"],
            "notes": r["notes"] or "",
            "is_deleted": r["is_deleted"] or 0,
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "normalized_json": r["normalized_json"],
            "ocr_provider": r["ocr_provider"] or "",
            "ocr_version": r["ocr_version"] or "",
            "ocr_confidence": r["ocr_confidence"],
            "duration_ms": r["duration_ms"],
            "warnings": r["warnings"],
            "raw_response": r["raw_response"],
            "plant_size_kw": r["plant_size_kw"],
            "recommended_inverter_kw": r["recommended_inverter_kw"],
            "estimated_monthly_generation": r["estimated_monthly_generation"],
            "estimated_annual_generation": r["estimated_annual_generation"],
            "monthly_savings": r["monthly_savings"],
            "annual_savings": r["annual_savings"],
            "system_cost": r["system_cost"],
            "payback_years": r["payback_years"],
            "co2_offset": r["co2_offset"],
            "trees_equivalent": r["trees_equivalent"],
            "calculation_status": r["calculation_status"],
            "calc_warnings": r["calc_warnings"]
        }
    except Exception as e:
        print(f"Error getting bill details: {e}")
        return None
    finally:
        conn.close()


def get_bills_by_site(site_id: str) -> List[Dict[str, Any]]:
    """Fetch all active bills belonging to a site, newest first."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    results = []
    try:
        cur = conn.cursor()
        query = """
            SELECT * FROM electricity_bills 
            WHERE site_id = ? AND is_deleted = 0 
            ORDER BY billing_year DESC, billing_month DESC;
        """ if is_sqlite else """
            SELECT * FROM electricity_bills 
            WHERE site_id = %s AND is_deleted = 0 
            ORDER BY billing_year DESC, billing_month DESC;
        """
        cur.execute(query, (site_id,))
        rows = cur.fetchall()
        for r in rows:
            results.append({
                "id": r["id"],
                "site_id": r["site_id"],
                "billing_month": r["billing_month"],
                "billing_year": r["billing_year"],
                "billing_period_start": r["billing_period_start"] or "",
                "billing_period_end": r["billing_period_end"] or "",
                "upload_date": r["upload_date"],
                "original_filename": r["original_filename"] or "",
                "stored_filename": r["stored_filename"] or "",
                "file_path": r["file_path"] or "",
                "file_type": r["file_type"] or "",
                "file_size": r["file_size"] or 0,
                "bill_status": r["bill_status"] or "Uploaded",
                "ocr_status": r["ocr_status"] or "Not Started",
                "notes": r["notes"] or ""
            })
        return results
    except Exception as e:
        print(f"Error getting bills: {e}")
        return []
    finally:
        conn.close()


def search_bills_db(search_q: str = None, customer_id: str = None, site_id: str = None, month: str = None, year: str = None, status: str = None) -> List[Dict[str, Any]]:
    """Query, search, and filter electricity bills dynamically."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    results = []
    try:
        cur = conn.cursor()
        where_clauses = ["b.is_deleted = 0"]
        params = []

        if search_q and search_q.strip():
            q = f"%{search_q.strip()}%"
            where_clauses.append("(b.original_filename LIKE ? OR s.name LIKE ? OR c.name LIKE ?)" if is_sqlite else "(b.original_filename ILIKE %s OR s.name ILIKE %s OR c.name ILIKE %s)")
            params.extend([q, q, q])

        if customer_id and customer_id != "all":
            where_clauses.append("s.customer_id = ?" if is_sqlite else "s.customer_id = %s")
            params.append(customer_id)

        if site_id and site_id != "all":
            where_clauses.append("b.site_id = ?" if is_sqlite else "b.site_id = %s")
            params.append(site_id)

        if month and month != "all":
            where_clauses.append("b.billing_month = ?" if is_sqlite else "b.billing_month = %s")
            params.append(int(month))

        if year and year != "all":
            where_clauses.append("b.billing_year = ?" if is_sqlite else "b.billing_year = %s")
            params.append(int(year))

        if status and status != "all":
            where_clauses.append("b.bill_status = ?" if is_sqlite else "b.bill_status = %s")
            params.append(status)

        query = f"""
            SELECT b.*, s.name as site_name, c.name as customer_name
            FROM electricity_bills b
            JOIN sites s ON b.site_id = s.id
            JOIN customers c ON s.customer_id = c.id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY b.billing_year DESC, b.billing_month DESC;
        """
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        for r in rows:
            results.append({
                "id": r["id"],
                "site_id": r["site_id"],
                "customer_name": r["customer_name"],
                "site_name": r["site_name"],
                "billing_month": r["billing_month"],
                "billing_year": r["billing_year"],
                "billing_period_start": r["billing_period_start"] or "",
                "billing_period_end": r["billing_period_end"] or "",
                "upload_date": r["upload_date"],
                "original_filename": r["original_filename"] or "",
                "stored_filename": r["stored_filename"] or "",
                "file_path": r["file_path"] or "",
                "file_type": r["file_type"] or "",
                "file_size": r["file_size"] or 0,
                "bill_status": r["bill_status"] or "Uploaded",
                "ocr_status": r["ocr_status"] or "Not Started"
            })
        return results
    except Exception as e:
        print(f"Error filtering bills: {e}")
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
            INSERT INTO ocr_results (bill_id, raw_response, normalized_json, ocr_provider, ocr_version)
            VALUES (?, ?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO ocr_results (bill_id, raw_response, normalized_json, ocr_provider, ocr_version)
            VALUES (%s, %s, %s, %s, %s);
        """
        cur.execute(query, (bill_id, extracted_text, json_data, "Demo", "1.0"))
        
        # Get result id
        res_id = cur.lastrowid
        if not is_sqlite:
            cur.execute("SELECT currval(pg_get_serial_sequence('ocr_results','id'));")
            res_id = cur.fetchone()[0]

        # Update parent record
        upd = """
            UPDATE electricity_bills
            SET latest_ocr_result_id = ?, ocr_status = 'Completed', bill_status = 'OCR Completed', ocr_completed_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """ if is_sqlite else """
            UPDATE electricity_bills
            SET latest_ocr_result_id = %s, ocr_status = 'Completed', bill_status = 'OCR Completed', ocr_completed_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """
        cur.execute(upd, (res_id, bill_id))
        
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
        query = """
            SELECT o.* FROM ocr_results o
            JOIN electricity_bills b ON b.latest_ocr_result_id = o.id
            WHERE b.id = ?;
        """ if is_sqlite else """
            SELECT o.* FROM ocr_results o
            JOIN electricity_bills b ON b.latest_ocr_result_id = o.id
            WHERE b.id = %s;
        """
        cur.execute(query, (bill_id,))
        r = cur.fetchone()
        if not r:
            query_fb = "SELECT * FROM ocr_results WHERE bill_id = ? ORDER BY id DESC LIMIT 1;" if is_sqlite else "SELECT * FROM ocr_results WHERE bill_id = %s ORDER BY id DESC LIMIT 1;"
            cur.execute(query_fb, (bill_id,))
            r = cur.fetchone()

        if not r:
            return None
        return {
            "id": r["id"],
            "bill_id": r["bill_id"],
            "extracted_text": r["raw_response"],
            "json_data": r["normalized_json"],
            "processed_at": r["created_at"],
            "raw_response": r["raw_response"],
            "normalized_json": r["normalized_json"],
            "ocr_provider": r["ocr_provider"],
            "ocr_version": r["ocr_version"],
            "ocr_confidence": r["ocr_confidence"],
            "duration_ms": r["duration_ms"],
            "warnings": r["warnings"]
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


def get_system_settings() -> Dict[str, str]:
    """Retrieves all solar assumptions and system configurations from database settings table."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM system_settings;")
        rows = cur.fetchall()
        settings = {}
        for r in rows:
            k = r[0] if is_sqlite else (r['key'] if isinstance(r, dict) else r[0])
            v = r[1] if is_sqlite else (r['value'] if isinstance(r, dict) else r[1])
            settings[k] = v
        return settings
    except Exception as e:
        print(f"Error fetching system settings: {e}")
        return {}
    finally:
        conn.close()


def save_system_settings(settings: Dict[str, str]) -> None:
    """Updates key-value solar config values in the database in a transaction."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = "UPDATE system_settings SET value = ? WHERE key = ?;" if is_sqlite else "UPDATE system_settings SET value = %s WHERE key = %s;"
        for k, v in settings.items():
            cur.execute(query, (str(v), k))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error saving system settings: {e}")
    finally:
        conn.close()


def get_proposal_details(proposal_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve metadata and sizing outputs for a single proposal version."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = """
            SELECT p.*, c.name as customer_name, c.contact as customer_contact, c.phone as customer_phone, c.category as customer_category,
                   s.name as site_name, s.address_street, s.address_city, s.address_state, s.address_zip,
                   b.billing_period_start, b.billing_period_end, b.billing_month, b.billing_year,
                   o.normalized_json, cal.co2_offset, cal.trees_equivalent
            FROM proposals p
            JOIN customers c ON p.customer_id = c.id
            JOIN sites s ON p.site_id = s.id
            LEFT JOIN electricity_bills b ON p.bill_id = b.id
            LEFT JOIN ocr_results o ON b.latest_ocr_result_id = o.id
            LEFT JOIN calculation_results cal ON p.calculation_id = cal.id
            WHERE p.id = ?;
        """ if is_sqlite else """
            SELECT p.*, c.name as customer_name, c.contact as customer_contact, c.phone as customer_phone, c.category as customer_category,
                   s.name as site_name, s.address_street, s.address_city, s.address_state, s.address_zip,
                   b.billing_period_start, b.billing_period_end, b.billing_month, b.billing_year,
                   o.normalized_json, cal.co2_offset, cal.trees_equivalent
            FROM proposals p
            JOIN customers c ON p.customer_id = c.id
            JOIN sites s ON p.site_id = s.id
            LEFT JOIN electricity_bills b ON p.bill_id = b.id
            LEFT JOIN ocr_results o ON b.latest_ocr_result_id = o.id
            LEFT JOIN calculation_results cal ON p.calculation_id = cal.id
            WHERE p.id = %s;
        """
        cur.execute(query, (proposal_id,))
        r = cur.fetchone()
        if not r:
            return None
            
        return {
            "id": r["id"],
            "proposal_number": r["proposal_number"],
            "customer_id": r["customer_id"],
            "site_id": r["site_id"],
            "bill_id": r["bill_id"],
            "calculation_id": r["calculation_id"],
            "proposal_name": r["proposal_name"],
            "version": r["version"],
            "status": r["status"],
            "plant_size_kw": r["plant_size_kw"],
            "recommended_inverter_kw": r["recommended_inverter_kw"],
            "annual_generation": r["annual_generation"],
            "annual_savings": r["annual_savings"],
            "system_cost": r["system_cost"],
            "payback_years": r["payback_years"],
            "prepared_by": r["prepared_by"],
            "prepared_date": r["prepared_date"],
            "remarks": r["remarks"] or "",
            "is_active": r["is_active"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "customer_name": r["customer_name"],
            "customer_contact": r["customer_contact"],
            "customer_phone": r["customer_phone"],
            "customer_category": r["customer_category"],
            "site_name": r["site_name"],
            "site_street": r["address_street"],
            "site_city": r["address_city"],
            "site_state": r["address_state"],
            "site_zip": r["address_zip"],
            "billing_period_start": r["billing_period_start"] or "",
            "billing_period_end": r["billing_period_end"] or "",
            "billing_month": r["billing_month"],
            "billing_year": r["billing_year"],
            "normalized_json": r["normalized_json"],
            "co2_offset": r["co2_offset"] if is_sqlite else (r["co2_offset"] if isinstance(r, dict) else r[34]),
            "trees_equivalent": r["trees_equivalent"] if is_sqlite else (r["trees_equivalent"] if isinstance(r, dict) else r[35]),
            "pdf_filename": r["pdf_filename"],
            "pdf_path": r["pdf_path"],
            "pdf_generated_at": r["pdf_generated_at"],
            "pdf_generated_by": r["pdf_generated_by"]
        }
    except Exception as e:
        print(f"Error fetching proposal details: {e}")
        return None
    finally:
        conn.close()


def list_proposals(search_q: str = "", status_f: str = "all", customer_f: str = "all", sort_order: str = "newest") -> List[Dict[str, Any]]:
    """Query, filter, search, and sort system proposals."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        query = """
            SELECT p.*, c.name as customer_name, s.name as site_name
            FROM proposals p
            JOIN customers c ON p.customer_id = c.id
            JOIN sites s ON p.site_id = s.id
            WHERE 1=1
        """
        params = []
        
        if search_q:
            query += " AND (p.proposal_number LIKE ? OR c.name LIKE ? OR s.name LIKE ?)" if is_sqlite else " AND (p.proposal_number ILIKE %s OR c.name ILIKE %s OR s.name ILIKE %s)"
            q = f"%{search_q}%"
            params.extend([q, q, q])
            
        if status_f and status_f != "all":
            query += " AND p.status = ?" if is_sqlite else " AND p.status = %s"
            params.append(status_f)
            
        if customer_f and customer_f != "all":
            query += " AND p.customer_id = ?" if is_sqlite else " AND p.customer_id = %s"
            params.append(customer_f)
            
        if sort_order == "oldest":
            query += " ORDER BY p.created_at ASC, p.version ASC"
        else:
            query += " ORDER BY p.created_at DESC, p.version DESC"
            
        cur.execute(query, params)
        rows = cur.fetchall()
        
        results = []
        for r in rows:
            results.append({
                "id": r["id"] if is_sqlite else (r["id"] if isinstance(r, dict) else r[0]),
                "proposal_number": r["proposal_number"] if is_sqlite else (r["proposal_number"] if isinstance(r, dict) else r[1]),
                "customer_id": r["customer_id"] if is_sqlite else (r["customer_id"] if isinstance(r, dict) else r[2]),
                "site_id": r["site_id"] if is_sqlite else (r["site_id"] if isinstance(r, dict) else r[3]),
                "bill_id": r["bill_id"] if is_sqlite else (r["bill_id"] if isinstance(r, dict) else r[4]),
                "proposal_name": r["proposal_name"] if is_sqlite else (r["proposal_name"] if isinstance(r, dict) else r[6]),
                "version": r["version"] if is_sqlite else (r["version"] if isinstance(r, dict) else r[7]),
                "status": r["status"] if is_sqlite else (r["status"] if isinstance(r, dict) else r[8]),
                "plant_size_kw": r["plant_size_kw"] if is_sqlite else (r["plant_size_kw"] if isinstance(r, dict) else r[9]),
                "annual_generation": r["annual_generation"] if is_sqlite else (r["annual_generation"] if isinstance(r, dict) else r[11]),
                "annual_savings": r["annual_savings"] if is_sqlite else (r["annual_savings"] if isinstance(r, dict) else r[12]),
                "system_cost": r["system_cost"] if is_sqlite else (r["system_cost"] if isinstance(r, dict) else r[13]),
                "payback_years": r["payback_years"] if is_sqlite else (r["payback_years"] if isinstance(r, dict) else r[14]),
                "prepared_by": r["prepared_by"] if is_sqlite else (r["prepared_by"] if isinstance(r, dict) else r[15]),
                "prepared_date": r["prepared_date"] if is_sqlite else (r["prepared_date"] if isinstance(r, dict) else r[16]),
                "created_at": r["created_at"] if is_sqlite else (r["created_at"] if isinstance(r, dict) else r[18]),
                "updated_at": r["updated_at"] if is_sqlite else (r["updated_at"] if isinstance(r, dict) else r[19]),
                "is_active": r["is_active"] if is_sqlite else (r["is_active"] if isinstance(r, dict) else r[17]),
                "customer_name": r["customer_name"] if is_sqlite else (r["customer_name"] if isinstance(r, dict) else r[20]),
                "site_name": r["site_name"] if is_sqlite else (r["site_name"] if isinstance(r, dict) else r[21])
            })
        return results
    except Exception as e:
        print(f"Error listing proposals: {e}")
        return []
    finally:
        conn.close()


def get_proposal_versions(proposal_number: str) -> List[Dict[str, Any]]:
    """Retrieve all generated versions for a given proposal ID sequence."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, version, status, is_active FROM proposals WHERE proposal_number = ? ORDER BY version DESC;" if is_sqlite else "SELECT id, version, status, is_active FROM proposals WHERE proposal_number = %s ORDER BY version DESC;", (proposal_number,))
        rows = cur.fetchall()
        return [{
            "id": r[0] if is_sqlite else (r["id"] if isinstance(r, dict) else r[0]),
            "version": r[1] if is_sqlite else (r["version"] if isinstance(r, dict) else r[1]),
            "status": r[2] if is_sqlite else (r["status"] if isinstance(r, dict) else r[2]),
            "is_active": r[3] if is_sqlite else (r["is_active"] if isinstance(r, dict) else r[3])
        } for r in rows]
    except Exception as e:
        print(f"Error fetching proposal versions: {e}")
        return []
    finally:
        conn.close()


def update_proposal_status(proposal_id: str, new_status: str, actor: str = "System") -> bool:
    """Updates the status column of the specific proposal ID, updates updated_at column, and logs activity."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        valid_statuses = ["Draft", "Under Review", "Approved", "Rejected", "Expired"]
        if new_status not in valid_statuses:
            return False
            
        cur.execute("SELECT site_id, proposal_number, version FROM proposals WHERE id = ?;" if is_sqlite else "SELECT site_id, proposal_number, version FROM proposals WHERE id = %s;", (proposal_id,))
        p_row = cur.fetchone()
        if not p_row:
            return False
            
        site_id = p_row[0] if is_sqlite else (p_row["site_id"] if isinstance(p_row, dict) else p_row[0])
        prop_num = p_row[1] if is_sqlite else (p_row["proposal_number"] if isinstance(p_row, dict) else p_row[1])
        ver = p_row[2] if is_sqlite else (p_row["version"] if isinstance(p_row, dict) else p_row[2])
        
        query = """
            UPDATE proposals
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """ if is_sqlite else """
            UPDATE proposals
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """
        cur.execute(query, (new_status, proposal_id))
        conn.commit()
        
        log_site_activity(
            site_id,
            "Proposal Status Updated",
            f"Proposal {prop_num} V{ver} marked as {new_status}.",
            actor
        )
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating proposal status: {e}")
        return False
    finally:
        conn.close()
