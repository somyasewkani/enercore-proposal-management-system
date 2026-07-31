"""
Enercore QA Verification Script
test_priority_fixes.py

Validates database migrations, customer profile edits, phone/email/GSTIN formatting validations,
and soft-delete archiving vs hard-delete dependency safety blocks.
"""

import sys
import os
import sqlite3
from pathlib import Path

# Add project root to sys path
sys.path.append(str(Path(__file__).parent))

from database.connection import get_connection, init_db
import services.customer_service as cs
import services.project_service as prjs
import services.proposal_service as ps

def run_priority_fixes_tests():
    print("==========================================================")
    print("RUNNING AUTOMATED CHECKS FOR QA PRIORITY FIXES")
    print("==========================================================")

    # 1. Reset database to test clean schema & migrations
    db_path = Path("database/enercore.db")
    if db_path.exists():
        try:
            db_path.unlink()
            print("[ok] Database reset cleanly for migration tests.")
        except PermissionError:
            pass

    init_db(seed_demo=False)
    print("[ok] Database initialized. Running migrations check.")

    # Verify column existence in sqlite table
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(customers);")
    columns = [row[1] for row in cur.fetchall()]
    conn.close()

    assert "email" in columns, "email column must exist"
    assert "address" in columns, "address column must exist"
    assert "gstin" in columns, "gstin column must exist"
    assert "is_deleted" in columns, "is_deleted column must exist"
    print("[ok] Idempotent migrations check: verified all new columns exist in database.")

    # 2. Test customer creation with email/phone/GSTIN
    cust_data = {
        "name": "QA Enterprise India Ltd",
        "contact": "Pranav Shah",
        "phone": "+91 98765 43210",
        "email": "pranav@qa-enterprise.in",
        "address": "452, Cyber City, Phase III, Gurugram, HR",
        "gstin": "06AAAAA0000A1Z2",  # Valid Indian GSTIN format
        "category": "Industrial",
        "value_numeric": 50000000.0,
        "capacity_mw": 2.5
    }
    
    cust_res = cs.create_customer(cust_data)
    cust_id = cust_res["id"]
    print(f"[ok] Customer created successfully with ID: {cust_id}")

    # 3. Verify format validations
    # Check duplicate email validation
    try:
        cs.create_customer({
            "name": "Duplicate Email Inc",
            "contact": "Tester",
            "email": "pranav@qa-enterprise.in", # same email
            "category": "Commercial"
        })
        print("[fail] Allowed duplicate email registration!")
        return False
    except ValueError as e:
        print(f"[ok] Prevented duplicate email registration: {e}")

    # Check invalid email validation
    try:
        cs.create_customer({
            "name": "Invalid Email Inc",
            "contact": "Tester",
            "email": "invalid-email-address", # bad format
            "category": "Commercial"
        })
        print("[fail] Allowed invalid email format!")
        return False
    except ValueError as e:
        print(f"[ok] Prevented invalid email format: {e}")

    # Check invalid GSTIN validation
    try:
        cs.create_customer({
            "name": "Invalid GSTIN Inc",
            "contact": "Tester",
            "gstin": "BAD_GSTIN_12345", # invalid format
            "category": "Commercial"
        })
        print("[fail] Allowed invalid GSTIN format!")
        return False
    except ValueError as e:
        print(f"[ok] Prevented invalid GSTIN format: {e}")

    # Check invalid phone validation
    try:
        cs.create_customer({
            "name": "Invalid Phone Inc",
            "contact": "Tester",
            "phone": "abc-1234-phone-chars", # alphabetic characters
            "category": "Commercial"
        })
        print("[fail] Allowed invalid phone format!")
        return False
    except ValueError as e:
        print(f"[ok] Prevented invalid phone format: {e}")

    # 4. Test Customer profile editing
    edit_data = {
        "name": "QA Enterprise India Private Limited",
        "contact": "Pranav Shah (Director)",
        "phone": "+91 99999 88888",
        "email": "director@qa-enterprise.in",
        "address": "Building 10B, DLF Cyber City, Sector 24, Gurugram, HR - 122002",
        "gstin": "06BBBBB1111B1Z3",
        "category": "Industrial",
        "value_numeric": 60000000.0,
        "capacity_mw": 3.0
    }
    
    success_edit = cs.update_customer_profile(cust_id, edit_data)
    assert success_edit is True
    
    cust_updated = cs.get_customer(cust_id)
    assert cust_updated["name"] == "QA Enterprise India Private Limited"
    assert cust_updated["contact"] == "Pranav Shah (Director)"
    assert cust_updated["phone"] == "+91 99999 88888"
    assert cust_updated["email"] == "director@qa-enterprise.in"
    assert cust_updated["address"] == "Building 10B, DLF Cyber City, Sector 24, Gurugram, HR - 122002"
    assert cust_updated["gstin"] == "06BBBBB1111B1Z3"
    assert cust_updated["capacity_mw"] == 3.0
    assert cust_updated["value_numeric"] == 60000000.0
    assert cust_updated["segment"] == "Industrial · 3.0MW"
    print("[ok] Customer profile edited and segment auto-updated correctly.")

    # 5. Test Soft Delete / Archiving
    # Normal list should return client
    active_list = cs.list_customers()
    assert any(c["id"] == cust_id for c in active_list), "Customer must be visible in list"
    
    # Soft delete customer
    success_del, msg_del = cs.delete_customer(cust_id, permanent=False)
    assert success_del is True
    print(f"[ok] Soft delete completed: {msg_del}")
    
    # Normal list should NOT return client
    active_list_post = cs.list_customers()
    assert not any(c["id"] == cust_id for c in active_list_post), "Soft deleted customer must be hidden from normal listings"
    print("[ok] Soft deleted customer verified hidden from normal listings.")

    # 6. Test Hard Delete Safety Rules
    # Recreate customer and register a site
    cust_id_2 = cs.create_customer({
        "name": "QA Factory Group",
        "contact": "Ramesh Kumar",
        "category": "Industrial"
    })["id"]
    
    site_id = ps.create_site({
        "customer_id": cust_id_2,
        "name": "Gurugram Plant",
        "address_street": "Sector 4",
        "address_city": "Gurugram",
        "address_state": "Haryana",
        "address_zip": "122001"
    })
    
    # Attempt permanent hard delete with active site
    success_hard, err_hard = cs.delete_customer(cust_id_2, permanent=True)
    assert success_hard is False
    assert "associated project sites" in err_hard
    print(f"[ok] Hard delete block verified (has active site): {err_hard}")

    # Remove site and retry hard delete
    ps.delete_site(site_id)
    success_hard_2, msg_hard = cs.delete_customer(cust_id_2, permanent=True)
    assert success_hard_2 is True
    print(f"[ok] Hard delete succeeded after clearing site dependency: {msg_hard}")

    print("\n==========================================================")
    print("ALL FIXES VERIFIED SUCCESSFULLY!")
    print("==========================================================")
    return True

if __name__ == "__main__":
    if run_priority_fixes_tests():
        sys.exit(0)
    else:
        sys.exit(1)
