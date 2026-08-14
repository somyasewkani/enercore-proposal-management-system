"""
Enercore AI Solar Proposal Generator
services/customer_service.py

Service layer for client/customer data, backed by database connection.
Supports customer profile updates, soft delete archiving, and safety checks.
"""

from __future__ import annotations
import sqlite3
import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from database.connection import get_connection
from services.dashboard_service import _format_value_display


def validate_customer_data(data: Dict[str, Any], exclude_customer_id: Optional[str] = None):
    """Performs strict backend validation of email, phone, GSTIN formats and duplicate emails."""
    # 1. Required fields
    name = data.get("name", "").strip()
    contact = data.get("contact", "").strip()
    if not name:
        raise ValueError("Company Name is required.")
    if not contact:
        raise ValueError("Contact Person is required.")

    # 2. Email validation
    email = data.get("email", "").strip()
    if email:
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError(f"Invalid email format: '{email}'.")
            
        # Duplicate email check
        conn = get_connection()
        is_sqlite = isinstance(conn, sqlite3.Connection)
        try:
            cur = conn.cursor()
            if exclude_customer_id:
                query = ("SELECT COUNT(*) FROM customers WHERE email = ? AND id != ? AND is_deleted = 0;" 
                         if is_sqlite else 
                         "SELECT COUNT(*) FROM customers WHERE email = %s AND id != %s AND is_deleted = 0;")
                cur.execute(query, (email, exclude_customer_id))
            else:
                query = ("SELECT COUNT(*) FROM customers WHERE email = ? AND is_deleted = 0;" 
                         if is_sqlite else 
                         "SELECT COUNT(*) FROM customers WHERE email = %s AND is_deleted = 0;")
                cur.execute(query, (email,))
            count = cur.fetchone()[0]
            if count > 0:
                raise ValueError(f"Email '{email}' is already registered for another client.")
        finally:
            conn.close()

    # 3. Phone validation
    phone = data.get("phone", "").strip()
    if phone:
        if not re.match(r"^[0-9\+\-\s\(\)]+$", phone):
            raise ValueError(f"Invalid phone number format: '{phone}'. Only numbers and symbols like +, -, (, ) are allowed.")

    # 4. GSTIN validation
    gstin = data.get("gstin", "").strip()
    if gstin:
        # Standard Indian 15-character GSTIN format check
        if not re.match(r"^[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[0-9a-zA-Z]{1}[zZ][0-9a-zA-Z]{1}$", gstin):
            raise ValueError(f"Invalid GSTIN format: '{gstin}'. Expected a standard 15-character alphanumeric GSTIN (e.g. 22AAAAA0000A1Z5).")


def list_customers(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    include_deleted: bool = False,
    archive_filter: str = "active"
) -> List[Dict[str, Any]]:
    """Return active customers matching filters directly from the database."""
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    results = []

    try:
        cur = conn.cursor()
        where_clauses = []
        params = []

        if include_deleted or archive_filter == "all":
            pass
        elif archive_filter == "archived":
            where_clauses.append("is_deleted = 1")
        else:
            where_clauses.append("is_deleted = 0")

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
            r_dict = dict(r) if is_sqlite else r
            val_num = r_dict["value_numeric"] or 0
            # Fetch counts dynamically
            c_id = r_dict["id"]
            cur.execute("SELECT COUNT(*) FROM sites WHERE customer_id = ? AND is_deleted = 0;" if is_sqlite else "SELECT COUNT(*) FROM sites WHERE customer_id = %s AND is_deleted = 0;", (c_id,))
            total_sites = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*) FROM electricity_bills b
                JOIN sites s ON b.site_id = s.id
                WHERE s.customer_id = ? AND s.is_deleted = 0;
            """ if is_sqlite else """
                SELECT COUNT(*) FROM electricity_bills b
                JOIN sites s ON b.site_id = s.id
                WHERE s.customer_id = %s AND s.is_deleted = 0;
            """, (c_id,))
            total_bills = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM proposals WHERE customer_id = ?;" if is_sqlite else "SELECT COUNT(*) FROM proposals WHERE customer_id = %s;", (c_id,))
            total_proposals = cur.fetchone()[0]

            # Latest Activity Log
            cur.execute("""
                SELECT activity_type, sa.created_at FROM site_activities sa
                JOIN sites s ON sa.site_id = s.id
                WHERE s.customer_id = ? AND s.is_deleted = 0
                ORDER BY sa.created_at DESC LIMIT 1;
            """ if is_sqlite else """
                SELECT activity_type, sa.created_at FROM site_activities sa
                JOIN sites s ON sa.site_id = s.id
                WHERE s.customer_id = %s AND s.is_deleted = 0
                ORDER BY sa.created_at DESC LIMIT 1;
            """, (c_id,))
            act = cur.fetchone()
            latest_activity = "Account Created"
            if act:
                latest_activity = act["activity_type"] if is_sqlite else (act[0] if not isinstance(act, dict) else act["activity_type"])

            results.append({
                "id": r_dict["id"],
                "name": r_dict["name"],
                "category": r_dict["category"],
                "segment": r_dict["segment"] or f"{r_dict['category']} · {r_dict['capacity_mw']}MW",
                "value": _format_value_display(val_num),
                "value_numeric": val_num,
                "status": r_dict["status"],
                "tone": r_dict["tone"] or "neutral",
                "contact": r_dict["contact"] or "",
                "phone": r_dict["phone"] or "",
                "email": r_dict.get("email") or "",
                "address": r_dict.get("address") or "",
                "gstin": r_dict.get("gstin") or "",
                "total_sites": total_sites,
                "total_bills": total_bills,
                "total_proposals": total_proposals,
                "capacity_mw": r_dict["capacity_mw"] or 0,
                "latest_activity": latest_activity,
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

        r_dict = dict(r) if is_sqlite else r
        val_num = r_dict["value_numeric"] or 0
        return {
            "id": r_dict["id"],
            "name": r_dict["name"],
            "category": r_dict["category"],
            "segment": r_dict["segment"],
            "value": _format_value_display(val_num),
            "value_numeric": val_num,
            "status": r_dict["status"],
            "tone": r_dict["tone"] or "neutral",
            "contact": r_dict["contact"] or "",
            "phone": r_dict["phone"] or "",
            "email": r_dict.get("email") or "",
            "address": r_dict.get("address") or "",
            "gstin": r_dict.get("gstin") or "",
            "capacity_mw": r_dict["capacity_mw"] or 0,
            "updated": r_dict["updated_at"] or "",
            "is_deleted": r_dict.get("is_deleted") or 0,
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
        cur.execute("SELECT COUNT(*) FROM customers WHERE is_deleted = 0;")
        total_clients = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM customers WHERE status = 'Contract Signed' AND is_deleted = 0;"
        )
        active_contracts = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(value_numeric), 0) FROM customers WHERE is_deleted = 0;")
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
    """Create a new customer record in database with validation."""
    validate_customer_data(data)
    
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM customers;")
        cnt = cur.fetchone()[0]
        new_id = f"cus_{1000 + cnt + 1}"

        name = data.get("name", "Unnamed Client").strip()
        category = data.get("category", "Commercial")
        capacity_mw = float(data.get("capacity_mw", 0.5))
        segment = data.get("segment") or f"{category} · {capacity_mw}MW"
        contact = data.get("contact", "").strip()
        phone = data.get("phone", "").strip()
        email = data.get("email", "").strip()
        address = data.get("address", "").strip()
        gstin = data.get("gstin", "").strip()
        status = data.get("status", "New Lead")
        tone = data.get("tone", "neutral")
        value_numeric = float(data.get("value_numeric", 0))
        updated_at = data.get("updated", "Just now")

        query = """
            INSERT INTO customers (id, name, category, segment, contact, phone, email, address, gstin, status, tone, value_numeric, capacity_mw, is_deleted, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?);
        """ if is_sqlite else """
            INSERT INTO customers (id, name, category, segment, contact, phone, email, address, gstin, status, tone, value_numeric, capacity_mw, is_deleted, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s);
        """

        cur.execute(query, (new_id, name, category, segment, contact, phone, email, address, gstin, status, tone, value_numeric, capacity_mw, updated_at))
        conn.commit()
        logging.info(f"[database] Successfully created customer: {new_id} ({name}) - Category: {category}, Status: {status}")

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
            "email": email,
            "address": address,
            "gstin": gstin,
            "updated": updated_at,
        }
    except Exception as e:
        print(f"Error creating customer: {e}")
        raise e
    finally:
        conn.close()


def update_customer_profile(customer_id: str, data: Dict[str, Any]) -> bool:
    """Updates customer demographic profile in the database with strict checks."""
    validate_customer_data(data, exclude_customer_id=customer_id)
    
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        name = data.get("name", "").strip()
        category = data.get("category", "Commercial")
        capacity_mw = float(data.get("capacity_mw", 0.5))
        segment = f"{category} · {capacity_mw}MW"
        contact = data.get("contact", "").strip()
        phone = data.get("phone", "").strip()
        email = data.get("email", "").strip()
        address = data.get("address", "").strip()
        gstin = data.get("gstin", "").strip()
        value_numeric = float(data.get("value_numeric", 0))

        query = """
            UPDATE customers
            SET name = ?, category = ?, segment = ?, contact = ?, phone = ?, email = ?, address = ?, gstin = ?,
                value_numeric = ?, capacity_mw = ?, updated_at = 'Just now'
            WHERE id = ?;
        """ if is_sqlite else """
            UPDATE customers
            SET name = %s, category = %s, segment = %s, contact = %s, phone = %s, email = %s, address = %s, gstin = %s,
                value_numeric = %s, capacity_mw = %s, updated_at = 'Just now'
            WHERE id = %s;
        """
        cur.execute(query, (name, category, segment, contact, phone, email, address, gstin, value_numeric, capacity_mw, customer_id))
        conn.commit()
        logging.info(f"[database] Successfully updated customer profile: {customer_id} ({name}) - Category: {category}")
        return True
    except Exception as e:
        print(f"Error updating customer profile {customer_id}: {e}")
        raise e
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
        logging.info(f"[database] Successfully updated status to '{new_status}' for customer: {customer_id}")
        return get_customer(customer_id)
    except Exception as e:
        print(f"Error updating customer status: {e}")
        return None
    finally:
        conn.close()


def delete_customer(customer_id: str, permanent: bool = False) -> Tuple[bool, str]:
    """
    Deletes customer from database. Soft delete (is_deleted=1) is the default.
    Only allows permanent hard delete if no active sites, bills, proposals, or projects reference the client.
    """
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        if permanent:
            # Check active related sites
            cur.execute("SELECT COUNT(*) FROM sites WHERE customer_id = ? AND is_deleted = 0;" if is_sqlite else "SELECT COUNT(*) FROM sites WHERE customer_id = %s AND is_deleted = 0;", (customer_id,))
            site_cnt = cur.fetchone()[0]
            
            # Check proposals
            cur.execute("SELECT COUNT(*) FROM proposals WHERE customer_id = ?;" if is_sqlite else "SELECT COUNT(*) FROM proposals WHERE customer_id = %s;", (customer_id,))
            prop_cnt = cur.fetchone()[0]
            
            # Check projects
            cur.execute("SELECT COUNT(*) FROM projects WHERE customer_id = ?;" if is_sqlite else "SELECT COUNT(*) FROM projects WHERE customer_id = %s;", (customer_id,))
            proj_cnt = cur.fetchone()[0]
            
            # Check bills
            cur.execute("""
                SELECT COUNT(*) FROM electricity_bills b
                JOIN sites s ON b.site_id = s.id
                WHERE s.customer_id = ? AND s.is_deleted = 0;
            """ if is_sqlite else """
                SELECT COUNT(*) FROM electricity_bills b
                JOIN sites s ON b.site_id = s.id
                WHERE s.customer_id = %s AND s.is_deleted = 0;
            """, (customer_id,))
            bill_cnt = cur.fetchone()[0]

            # Safe checking for permanent hard delete
            if site_cnt > 0 or prop_cnt > 0 or proj_cnt > 0 or bill_cnt > 0:
                return False, "Cannot permanently delete customer: associated project sites, bills, proposals, or projects exist."
            
            cur.execute("DELETE FROM customers WHERE id = ?;" if is_sqlite else "DELETE FROM customers WHERE id = %s;", (customer_id,))
            conn.commit()
            logging.info(f"[database] Successfully permanently deleted customer: {customer_id}")
            return True, "Customer permanently deleted successfully."
        else:
            # Soft Delete (marks as is_deleted = 1, status = 'Archived')
            cur.execute("""
                UPDATE customers
                SET is_deleted = 1, status = 'Archived', tone = 'neutral', updated_at = 'Just now'
                WHERE id = ?;
            """ if is_sqlite else """
                UPDATE customers
                SET is_deleted = 1, status = 'Archived', tone = 'neutral', updated_at = 'Just now'
                WHERE id = %s;
            """, (customer_id,))
            conn.commit()
            logging.info(f"[database] Successfully soft-deleted/archived customer: {customer_id}")
            return True, "Customer successfully archived (soft deleted)."
            
    except Exception as e:
        print(f"[customer_service] Error during deletion of client {customer_id}: {e}")
        return False, str(e)
    finally:
        conn.close()


def restore_customer(customer_id: str) -> Tuple[bool, str]:
    """
    Restore an archived customer to active status.
    Infers and restores the previous lifecycle stage (Contract Signed, Proposal Sent, New Lead).
    """
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # 1. Validate customer exists
        cur.execute(
            "SELECT COUNT(*), name FROM customers WHERE id = ?;" 
            if is_sqlite else 
            "SELECT COUNT(*), name FROM customers WHERE id = %s;", 
            (customer_id,)
        )
        row = cur.fetchone()
        count = row[0]
        name = row[1] if count > 0 else ""
        if count == 0:
            return False, f"Customer with ID '{customer_id}' does not exist."
            
        # 2. Check duplicate customer name (must not conflict with another active customer of the same name)
        cur.execute(
            "SELECT COUNT(*) FROM customers WHERE name = ? AND is_deleted = 0 AND id != ?;"
            if is_sqlite else
            "SELECT COUNT(*) FROM customers WHERE name = %s AND is_deleted = 0 AND id != %s;",
            (name, customer_id)
        )
        dup_count = cur.fetchone()[0]
        if dup_count > 0:
            return False, f"Cannot restore customer '{name}'. Another active customer with the same name already exists."
            
        # 3. Infer previous lifecycle stage
        # Check projects first
        cur.execute(
            "SELECT COUNT(*) FROM projects WHERE customer_id = ?;"
            if is_sqlite else
            "SELECT COUNT(*) FROM projects WHERE customer_id = %s;",
            (customer_id,)
        )
        has_projects = cur.fetchone()[0] > 0
        
        # Check proposals
        cur.execute(
            "SELECT COUNT(*) FROM proposals WHERE customer_id = ?;"
            if is_sqlite else
            "SELECT COUNT(*) FROM proposals WHERE customer_id = %s;",
            (customer_id,)
        )
        has_proposals = cur.fetchone()[0] > 0
        
        # Check pipeline_deals stage
        cur.execute(
            "SELECT stage FROM pipeline_deals WHERE customer_id = ?;"
            if is_sqlite else
            "SELECT stage FROM pipeline_deals WHERE customer_id = %s;",
            (customer_id,)
        )
        deal_row = cur.fetchone()
        deal_stage = deal_row[0] if deal_row else None
        
        # Determine status
        if has_projects:
            status = "Contract Signed"
        elif has_proposals:
            status = "Proposal Sent"
        elif deal_stage:
            status = deal_stage
        else:
            status = "New Lead"
            
        # 4. Perform update (is_deleted = 0)
        cur.execute("""
            UPDATE customers
            SET is_deleted = 0, status = ?, tone = 'neutral', updated_at = 'Just now'
            WHERE id = ?;
        """ if is_sqlite else """
            UPDATE customers
            SET is_deleted = 0, status = %s, tone = 'neutral', updated_at = 'Just now'
            WHERE id = %s;
        """, (status, customer_id))
        
        # Also restore associated pipeline deal if archived
        if deal_row:
            cur.execute("""
                UPDATE pipeline_deals
                SET is_archived = 0
                WHERE customer_id = ?;
            """ if is_sqlite else """
                UPDATE pipeline_deals
                SET is_archived = 0
                WHERE customer_id = %s;
            """, (customer_id,))
            
        conn.commit()
        logging.info(f"[database] Successfully restored customer: {customer_id} (status set to '{status}')")
        return True, f"Customer '{name}' restored successfully to stage '{status}'."
        
    except Exception as e:
        print(f"[customer_service] Error during restoration of client {customer_id}: {e}")
        return False, str(e)
    finally:
        conn.close()