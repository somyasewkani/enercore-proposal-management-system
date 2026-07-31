import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from database.connection import get_connection
from services.proposal_service import get_bill_details, log_site_activity

def generate_proposal_record(bill_id: str, actor: str = "System", remarks: str = "") -> Tuple[bool, List[str], str]:
    """Validates bill state and generates a proposal record or new version for a client."""
    bill = get_bill_details(bill_id)
    if not bill:
        return False, ["Utility bill statement not found."], ""
        
    site_id = bill["site_id"]
    customer_id = bill["customer_id"]

    # 1. Validation Checks
    if bill.get("ocr_status") != "Completed":
        return False, ["OCR extraction must be completed before generating a proposal."], ""
        
    if not bill.get("latest_calculation_id"):
        return False, ["Solar feasibility calculations must be performed before generating a proposal."], ""
        
    # Check customer details
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # Load Customer fields
        cur.execute("SELECT name, contact, phone FROM customers WHERE id = ?;" if is_sqlite else "SELECT name, contact, phone FROM customers WHERE id = %s;", (customer_id,))
        cust_row = cur.fetchone()
        if not cust_row:
            return False, ["Client record not found."], ""
            
        cust_name = cust_row[0] if is_sqlite else (cust_row["name"] if isinstance(cust_row, dict) else cust_row[0])
        cust_contact = cust_row[1] if is_sqlite else (cust_row["contact"] if isinstance(cust_row, dict) else cust_row[1])
        
        if not cust_name or not cust_contact:
            return False, ["Client name and primary contact person must be configured."], ""

        # Load Site details
        cur.execute("SELECT name, address_street, address_city, address_state, address_zip FROM sites WHERE id = ?;" if is_sqlite else "SELECT name, address_street, address_city, address_state, address_zip FROM sites WHERE id = %s;", (site_id,))
        site_row = cur.fetchone()
        if not site_row:
            return False, ["Site record not found."], ""
            
        site_name = site_row[0] if is_sqlite else (site_row["name"] if isinstance(site_row, dict) else site_row[0])
        site_street = site_row[1] if is_sqlite else (site_row["address_street"] if isinstance(site_row, dict) else site_row[1])
        site_city = site_row[2] if is_sqlite else (site_row["address_city"] if isinstance(site_row, dict) else site_row[2])
        site_state = site_row[3] if is_sqlite else (site_row["address_state"] if isinstance(site_row, dict) else site_row[3])
        site_zip = site_row[4] if is_sqlite else (site_row["address_zip"] if isinstance(site_row, dict) else site_row[4])
        
        if not site_name or not site_street or not site_city or not site_state or not site_zip:
            return False, ["Complete site address (street, city, state, zip) is required to generate a proposal."], ""

        # 2. Number Sequence & Version Control
        # Check if a proposal already exists for this site
        cur.execute("SELECT proposal_number FROM proposals WHERE site_id = ? LIMIT 1;" if is_sqlite else "SELECT proposal_number FROM proposals WHERE site_id = %s LIMIT 1;", (site_id,))
        exist_prop = cur.fetchone()
        
        if exist_prop:
            prop_num = exist_prop[0] if is_sqlite else (exist_prop["proposal_number"] if isinstance(exist_prop, dict) else exist_prop[0])
            # Fetch latest version
            cur.execute("SELECT MAX(version) FROM proposals WHERE proposal_number = ?;" if is_sqlite else "SELECT MAX(version) FROM proposals WHERE proposal_number = %s;", (prop_num,))
            max_ver = cur.fetchone()[0] or 0
            version = max_ver + 1
            
            # Deactivate older versions
            deact_query = "UPDATE proposals SET is_active = 0 WHERE proposal_number = ?;" if is_sqlite else "UPDATE proposals SET is_active = 0 WHERE proposal_number = %s;"
            cur.execute(deact_query, (prop_num,))
        else:
            # Generate new proposal number ENR-2026-XXXX
            current_year = datetime.now().year
            prefix = f"ENR-{current_year}-"
            
            # Find highest sequence
            cur.execute("SELECT proposal_number FROM proposals WHERE proposal_number LIKE ? ORDER BY proposal_number DESC LIMIT 1;" if is_sqlite else "SELECT proposal_number FROM proposals WHERE proposal_number LIKE %s ORDER BY proposal_number DESC LIMIT 1;", (prefix + "%",))
            last_row = cur.fetchone()
            
            if last_row:
                last_num = last_row[0] if is_sqlite else (last_row["proposal_number"] if isinstance(last_row, dict) else last_row[0])
                try:
                    seq = int(last_num.split("-")[-1])
                    next_seq = seq + 1
                except Exception:
                    next_seq = 1
            else:
                next_seq = 1
                
            prop_num = f"{prefix}{next_seq:04d}"
            version = 1

        # 3. Create proposal record
        proposal_id = f"prop_{uuid.uuid4().hex[:12]}"
        proposal_name = f"Solar Proposal - {site_name}"
        prepared_date = datetime.now().strftime("%Y-%m-%d")
        
        insert_query = """
            INSERT INTO proposals (
                id, proposal_number, customer_id, site_id, bill_id, calculation_id,
                proposal_name, version, status, plant_size_kw, recommended_inverter_kw,
                annual_generation, annual_savings, system_cost, payback_years,
                prepared_by, prepared_date, remarks, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
        """ if is_sqlite else """
            INSERT INTO proposals (
                id, proposal_number, customer_id, site_id, bill_id, calculation_id,
                proposal_name, version, status, plant_size_kw, recommended_inverter_kw,
                annual_generation, annual_savings, system_cost, payback_years,
                prepared_by, prepared_date, remarks, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1);
        """
        
        cur.execute(insert_query, (
            proposal_id,
            prop_num,
            customer_id,
            site_id,
            bill_id,
            bill["latest_calculation_id"],
            proposal_name,
            version,
            "Draft",
            bill["plant_size_kw"],
            bill["recommended_inverter_kw"],
            bill["estimated_annual_generation"],
            bill["annual_savings"],
            bill["system_cost"],
            bill["payback_years"],
            actor,
            prepared_date,
            remarks
        ))
        
        # Update site status
        site_upd = "UPDATE sites SET status = 'Proposal Generated' WHERE id = ?;" if is_sqlite else "UPDATE sites SET status = 'Proposal Generated' WHERE id = %s;"
        cur.execute(site_upd, (site_id,))
        
        # Update bill status
        bill_upd = "UPDATE electricity_bills SET bill_status = 'Used in Proposal' WHERE id = ?;" if is_sqlite else "UPDATE electricity_bills SET bill_status = 'Used in Proposal' WHERE id = %s;"
        cur.execute(bill_upd, (bill_id,))
        
        conn.commit()

        # Log timeline action
        log_site_activity(
            site_id,
            "Proposal Generated",
            f"Official proposal {prop_num} V{version} compiled and generated.",
            actor
        )
        return True, [], proposal_id
        
    except Exception as e:
        conn.rollback()
        print(f"Error compiling proposal: {e}")
        return False, [str(e)], ""
    finally:
        conn.close()
