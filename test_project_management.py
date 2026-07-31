"""
Enercore Solar Proposal Management System
test_project_management.py

Integration Test Suite for Sprint 8 - Project Conversion & Project Management.
"""

import os
import sys
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add current path to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from typing import Tuple, List, Dict, Any, Optional
from database.connection import get_connection, init_db
import services.customer_service as cs
import services.proposal_service as ps
import services.project_service as prjs
import app_flask as af


def setup_test_data() -> Tuple[str, str]:
    """Helper seeds a client, site, electricity bill, calc, and an approved proposal."""
    # Reset database
    db_path = Path("database/enercore.db")
    if db_path.exists():
        try:
            os.remove(db_path)
        except Exception:
            pass
            
    init_db(seed_demo=False)
    
    # Create customer
    cs.create_customer({
        'name': 'Google LLC',
        'category': 'Commercial',
        'segment': 'Commercial · 2.5MW',
        'status': 'Active Lead',
        'tone': 'promising',
        'value_numeric': 2500000.0,
        'updated': 'Now',
        'contact': 'Sundar Pichai',
        'phone': '1234567890'
    })
    cust_id = cs.list_customers()[0]['id']
    
    # Create site
    site_id = ps.create_site({
        'customer_id': cust_id,
        'name': 'Mountain View Campus',
        'address_street': '1600 Amphitheatre Pkwy',
        'address_city': 'Mountain View',
        'address_state': 'CA',
        'address_zip': '94043'
    })
    
    # Create bill
    bill_id = ps.create_electricity_bill({
        'site_id': site_id,
        'billing_month': 7,
        'billing_year': 2026,
        'original_filename': 'bill.pdf',
        'stored_filename': 'bill.pdf',
        'file_path': 'uploads/bills/bill.pdf',
        'file_type': 'PDF',
        'file_size': 1024,
        'bill_status': 'Uploaded'
    })
    
    # Create calculation result
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO calculation_results (
            bill_id, plant_size_kw, recommended_inverter_kw, estimated_monthly_generation,
            estimated_annual_generation, monthly_savings, annual_savings, system_cost,
            payback_years, co2_offset, trees_equivalent, calculation_version, calculation_status
        ) VALUES (?, 250.0, 200.0, 11250.0, 135000.0, 5000.0, 60000.0, 425000.0, 7.1, 110.0, 4400.0, '1.0', 'Success');
    """, (bill_id,))
    calc_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    # Create approved proposal
    prop_data = {
        'id': 'prop_google_test_1',
        'proposal_number': 'ENR-2026-1001',
        'customer_id': cust_id,
        'site_id': site_id,
        'bill_id': bill_id,
        'calculation_id': calc_id,
        'proposal_name': 'Google Solar Feasibility Proposal',
        'version': 1,
        'status': 'Approved',
        'plant_size_kw': 250.0,
        'recommended_inverter_kw': 200.0,
        'annual_generation': 135000.0,
        'annual_savings': 60000.0,
        'system_cost': 425000.0,
        'payback_years': 7.1,
        'prepared_by': 'Sales Manager',
        'prepared_date': '2026-07-28',
        'remarks': 'Test approved proposal remarks.'
    }
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO proposals (
            id, proposal_number, customer_id, site_id, bill_id, calculation_id, proposal_name,
            version, status, plant_size_kw, recommended_inverter_kw, annual_generation,
            annual_savings, system_cost, payback_years, prepared_by, prepared_date, remarks
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        prop_data['id'], prop_data['proposal_number'], prop_data['customer_id'],
        prop_data['site_id'], prop_data['bill_id'], prop_data['calculation_id'],
        prop_data['proposal_name'], prop_data['version'], prop_data['status'],
        prop_data['plant_size_kw'], prop_data['recommended_inverter_kw'], prop_data['annual_generation'],
        prop_data['annual_savings'], prop_data['system_cost'], prop_data['payback_years'],
        prop_data['prepared_by'], prop_data['prepared_date'], prop_data['remarks']
    ))
    conn.commit()
    conn.close()
    
    return prop_data['id'], cust_id


def run_project_management_tests():
    print("Starting Sprint 8 Project Management Integration Tests...")
    
    # 1. Setup DB and initial approved proposal
    prop_id, cust_id = setup_test_data()
    print("[ok] Test environment data seeded.")
    
    # 2. Test Validation Rule: Proposal must be Approved
    # Create a draft proposal first
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO proposals (id, proposal_number, customer_id, status, proposal_name)
        VALUES ('prop_draft_test', 'ENR-2026-9999', ?, 'Draft', 'Draft proposal');
    """, (cust_id,))
    conn.commit()
    conn.close()
    
    success, err = prjs.convert_proposal_to_project('prop_draft_test', actor='Test Runner')
    assert success is False
    assert "must be Approved" in err
    print("[ok] Test Passed: Correctly blocked conversion of non-Approved proposal.")
    
    # 3. Test Successful Conversion & Project Numbering (PRJ-2026-0001)
    success, proj_id = prjs.convert_proposal_to_project(prop_id, actor='Test Runner')
    assert success is True
    assert proj_id is not None
    
    project = prjs.get_project_details(proj_id)
    assert project is not None
    assert project['project_number'] == "PRJ-2026-0001"
    assert project['capacity_kw'] == 250.0
    assert project['contract_value'] == 425000.0
    assert project['status'] == "Planning"
    assert project['progress_percentage'] == 0
    print("[ok] Test Passed: Successfully converted approved proposal into project.")
    
    # 4. Check that customer pipeline status is updated to 'Contract Signed'
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM customers WHERE id = ?;", (cust_id,))
    c_status = cur.fetchone()[0]
    conn.close()
    assert c_status == "Contract Signed"
    print("[ok] Test Passed: Customer status correctly transitioned to 'Contract Signed'.")

    # 5. Test Active Project Validation Blockage (No double conversions)
    success2, err2 = prjs.convert_proposal_to_project(prop_id, actor='Test Runner')
    assert success2 is False
    assert "active project already exists" in err2
    print("[ok] Test Passed: Blocked duplicate project conversion for same proposal.")

    # 6. Test Sequential Numbering Increments (PRJ-2026-0002)
    # Seed a second approved proposal
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO proposals (id, proposal_number, customer_id, status, proposal_name, plant_size_kw, system_cost)
        VALUES ('prop_google_test_2', 'ENR-2026-1002', ?, 'Approved', 'Google Second Proposal', 150.0, 2500000.0);
    """, (cust_id,))
    conn.commit()
    conn.close()
    
    success3, proj_id2 = prjs.convert_proposal_to_project('prop_google_test_2', actor='Test Runner')
    assert success3 is True
    project2 = prjs.get_project_details(proj_id2)
    assert project2['project_number'] == "PRJ-2026-0002"
    print("[ok] Test Passed: Sequential numbering increments correctly (PRJ-2026-0002).")

    # 7. Test Activity Logging & Site activities mapping
    activities = prjs.get_project_activities(proj_id)
    assert len(activities) > 0
    assert activities[-1]['activity_type'] == "Project Created"
    assert "converted from approved proposal" in activities[-1]['description']
    print("[ok] Test Passed: Automatic creation timeline activity logged.")

    # 8. Test Updating Status & Progress %
    # Update to Site Survey
    upd_success = prjs.update_project_status(
        project_id=proj_id,
        new_status="Site Survey",
        progress=15,
        actor="Project Manager X",
        remarks="Scheduled technical team visit."
    )
    assert upd_success is True
    
    project_upd = prjs.get_project_details(proj_id)
    assert project_upd['status'] == "Site Survey"
    assert project_upd['progress_percentage'] == 15
    assert project_upd['remarks'] == "Scheduled technical team visit."
    
    activities_upd = prjs.get_project_activities(proj_id)
    assert activities_upd[0]['activity_type'] == "Survey Scheduled"
    print("[ok] Test Passed: Updated status, progress %, and logged custom step activity.")

    # Test Completion Transition
    upd_comp = prjs.update_project_status(
        project_id=proj_id,
        new_status="Completed",
        progress=100,
        actor="Project Manager X",
        remarks="All commissioning logs signed off."
    )
    assert upd_comp is True
    project_comp = prjs.get_project_details(proj_id)
    assert project_comp['status'] == "Completed"
    assert project_comp['progress_percentage'] == 100
    assert project_comp['actual_completion'] is not None
    print("[ok] Test Passed: Commissioning complete sets actual completion date.")

    # 9. Test Document Upload Metadata Logging
    doc_success = prjs.add_project_document(
        project_id=proj_id,
        document_type="Drawings",
        original_filename="blueprint.dwg",
        stored_filename="blueprint_xyz.dwg",
        file_path="uploads/projects/PRJ-2026-0001/blueprint_xyz.dwg",
        file_size=20480,
        uploaded_by="Design Engineer"
    )
    assert doc_success is True
    
    docs = prjs.get_project_documents(proj_id)
    assert len(docs) == 1
    assert docs[0]['document_type'] == "Drawings"
    assert docs[0]['original_filename'] == "blueprint.dwg"
    
    activities_doc = prjs.get_project_activities(proj_id)
    assert "blueprint.dwg" in activities_doc[0]['description']
    print("[ok] Test Passed: Document metadata recorded and audit timeline entry logged.")

    # 10. Test Dashboard KPIs aggregation
    kpis = prjs.get_project_dashboard_kpis()
    # Active projects should be 1 (project2: Google Second Proposal is Planning)
    # Completed projects should be 1 (project1: Completed)
    # Installed capacity should be 0.25 MW (from project1: 250 kW = 0.25 MW)
    # Pipeline capacity should be 0.15 MW (from project2: 150 kW = 0.15 MW)
    # Project Revenue should be contract value sum of active + completed: 425000 + 2500000 = 2925000
    kpi_dict = {k['label']: k['value'] for k in kpis}
    
    assert kpi_dict['Active Projects'] == "1"
    assert kpi_dict['Completed Projects'] == "1"
    assert kpi_dict['Installed Capacity'] == "0.25 MW"
    assert kpi_dict['Pipeline Capacity'] == "0.15 MW"
    assert kpi_dict['Project Revenue'] == "$2,925,000.00"
    print("[ok] Test Passed: Dashboard KPI indicators aggregated correctly.")

    # 11. Test Projects Listing & Filters
    all_projects = prjs.list_projects()
    assert len(all_projects) == 2
    
    planning_projects = prjs.list_projects(status_filter="Planning")
    assert len(planning_projects) == 1
    assert planning_projects[0]['project_number'] == "PRJ-2026-0002"
    
    completed_projects = prjs.list_projects(status_filter="Completed")
    assert len(completed_projects) == 1
    assert completed_projects[0]['project_number'] == "PRJ-2026-0001"
    print("[ok] Test Passed: Projects list, search, and status filters query correctly.")
    
    # 12. Test Reports stats groupings
    rep_stats = prjs.get_project_reports_stats()
    assert len(rep_stats['by_status']) == 2
    assert len(rep_stats['monthly_creation']) >= 1
    print("[ok] Test Passed: Reports statuses, capacities, and monthly creations compile correctly.")

    # 13. Test Secure Login Authentication
    with af.app.test_client() as client:
        # Invalid credentials attempt
        r_fail = client.post('/login', data={'email': 'admin@enercore.com', 'password': 'wrongpassword'})
        assert b"Invalid email or password." in r_fail.data
        
        # Valid credentials attempt (seeding was completed during setup_test_data/init_db)
        r_success = client.post('/login', data={'email': 'admin@enercore.com', 'password': 'admin123'})
        assert r_success.status_code == 302 # Redirects to dashboard upon success
        print("[ok] Test Passed: Hashed password security blocks invalid and authorizes valid logins.")

    print("\nALL SPRINT 8 INTEGRATION TESTS PASSED SUCCESSFULLY!\n")
    return True


if __name__ == "__main__":
    run_project_management_tests()
