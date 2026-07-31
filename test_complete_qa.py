"""
Enercore AI Portal - Complete End-to-End QA Testing Suite
test_complete_qa.py
"""

import os
import sys
import json
import shutil
import sqlite3
import bcrypt
from pathlib import Path

# Add current path to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database.connection import get_connection, init_db
import services.auth_service as auth
import services.customer_service as cs
import services.proposal_service as ps
import services.ocr_service as ocrs
import services.calculation_service as calcs
import services.proposal_generator as pg
import services.pdf_generator as pdfg
import services.project_service as prjs

def run_qa_tests():
    print("==========================================================")
    print("STARTING COMPLETE END-TO-END QA TESTING & DOMAIN AUDIT")
    print("==========================================================\n")
    
    # ------------------------------------------------------------
    # 1. DATABASE INITIALIZATION & RESET
    # ------------------------------------------------------------
    db_path = Path("database/enercore.db")
    if db_path.exists():
        try:
            os.remove(db_path)
            print("[ok] Database file removed for clean state testing.")
        except Exception as e:
            print(f"[warning] Failed to remove database file: {e}")
            
    # Reset database schema
    init_db(seed_demo=False)
    print("[ok] Database initialized with clean schema.")

    # ------------------------------------------------------------
    # 2. AUTHENTICATION QA VERIFICATION
    # ------------------------------------------------------------
    print("\n--- 2. AUTHENTICATION TEST CASES ---")
    
    # Assert default admin seeded
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, role FROM users WHERE email = ?;", ("admin@enercore.com",))
    user_row = cur.fetchone()
    assert user_row is not None, "Admin user must be seeded automatically in init_db"
    print("[ok] Admin user 'admin@enercore.com' successfully seeded.")
    conn.close()

    # Wrong password test
    res_wrong_pw = auth.login_user("admin@enercore.com", "wrongpassword")
    assert res_wrong_pw is None, "Login must fail with incorrect password"
    print("[ok] Test Passed: Authentication blocked for incorrect password.")

    # Wrong email test
    res_wrong_email = auth.login_user("wrongemail@enercore.com", "admin123")
    assert res_wrong_email is None, "Login must fail with incorrect email"
    print("[ok] Test Passed: Authentication blocked for unregistered email.")

    # Valid login test
    res_success = auth.login_user("admin@enercore.com", "admin123")
    assert res_success is not None, "Successful login should return user dict details"
    assert res_success["email"] == "admin@enercore.com", "User detail email must match"
    assert res_success["role"] == "Sales Engineer", "User role must match"
    print("[ok] Test Passed: Hashed password security verified successfully.")

    # ------------------------------------------------------------
    # 3. CUSTOMER MANAGEMENT QA VERIFICATION
    # ------------------------------------------------------------
    print("\n--- 3. CUSTOMER CRUD & VALIDATION TEST CASES ---")
    
    # Create customer
    try:
        cs.create_customer({
            'name': 'M/S CAPARO MARUTI LTD',
            'category': 'Commercial',
            'segment': 'Industrial · 1.5MW',
            'status': 'New Lead',
            'tone': 'neutral',
            'value_numeric': 75000000.0,
            'capacity_mw': 1.5,
            'updated': 'Just now',
            'contact': 'Quality Manager',
            'phone': '9999912345'
        })
        print("[ok] Customer 'M/S CAPARO MARUTI LTD' created successfully.")
    except Exception as e:
        print(f"[fail] Customer creation failed: {e}")
        return False
        
    customers = cs.list_customers()
    assert len(customers) == 1, "There should be exactly 1 customer"
    cust_id = customers[0]['id']
    
    # Edit customer (by status update)
    cs.update_customer_status(cust_id, "Contacted")
    
    updated_cust = cs.list_customers()[0]
    assert updated_cust['status'] == 'Contacted'
    print("[ok] Customer edit operations (status toggle) completed and persisted.")

    # ------------------------------------------------------------
    # 4. SITE MANAGEMENT QA VERIFICATION
    # ------------------------------------------------------------
    print("\n--- 4. SITE CRUD & MAPPING TEST CASES ---")
    
    site_id = ps.create_site({
        'customer_id': cust_id,
        'name': 'Gurugram Factory Site',
        'address_street': '7 MUL JV, Gurugram, HR, IND',
        'address_city': 'Gurugram',
        'address_state': 'Haryana',
        'address_zip': '122001'
    })
    print(f"[ok] Factory Site created with ID: {site_id}")
    
    # Verify mapping
    site_details = ps.get_site_details(site_id)
    assert site_details['customer_id'] == cust_id, "Site customer_id mapping incorrect"
    assert site_details['name'] == 'Gurugram Factory Site', "Site name incorrect"
    assert site_details['address_city'] == 'Gurugram', "Site city incorrect"
    print("[ok] Site customer mapping and address validations passed.")

    # ------------------------------------------------------------
    # 5. CRM PIPELINE STAGES QA VERIFICATION
    # ------------------------------------------------------------
    print("\n--- 5. CRM PIPELINE STAGES TEST CASES ---")
    
    # Create deal
    # Create deal
    from services.pipeline_service import get_all_deals_by_stage, create_pipeline_deal, update_deal_stage
    create_pipeline_deal({
        'company_name': 'M/S CAPARO MARUTI LTD',
        'category': 'Industrial',
        'value_numeric': 75000000.0,
        'stage': 'New Lead',
        'contact_person': 'Senior QA Lead'
    })
    print("[ok] Pipeline CRM deal registered under 'New Lead' column.")
    
    deals_disc = get_all_deals_by_stage()
    deals_in_new_lead = deals_disc['New Lead']['deals']
    assert any(d['company_name'] == 'M/S CAPARO MARUTI LTD' for d in deals_in_new_lead), "Deal must exist in New Lead stage"
    
    deal_id = [d['id'] for d in deals_in_new_lead if d['company_name'] == 'M/S CAPARO MARUTI LTD'][0]
    
    # Move stage
    update_deal_stage(deal_id, 'Proposal Sent')
    deals_moved = get_all_deals_by_stage()
    assert any(d['company_name'] == 'M/S CAPARO MARUTI LTD' for d in deals_moved['Proposal Sent']['deals']), "Deal must exist in Proposal Sent stage"
    print("[ok] Deal stage successfully transitioned to 'Proposal Sent'. Column counts updated.")

    # ------------------------------------------------------------
    # 6. OCR PIPELINE QA VERIFICATION (REAL PDF BILL)
    # ------------------------------------------------------------
    print("\n--- 6. BILL UPLOAD & OCR EXTRACTION ACCURACY ---")
    
    # Verify file upload folder
    upload_path = Path("uploads/bills/site_1/new_bill.pdf")
    assert upload_path.exists(), "Real bill new_bill.pdf must be placed in uploads/bills/site_1/ for pipeline"
    print(f"[ok] Real bill document validated at path: {upload_path} ({upload_path.stat().st_size} bytes)")
    
    # Register bill in DB
    bill_id = ps.create_electricity_bill({
        'site_id': site_id,
        'billing_month': 3,
        'billing_year': 2026,
        'original_filename': 'New Doc 03-13-2026 09.54.pdf',
        'stored_filename': 'new_bill.pdf',
        'file_path': 'uploads/bills/site_1/new_bill.pdf',
        'file_type': 'PDF',
        'file_size': int(upload_path.stat().st_size),
        'bill_status': 'Uploaded'
    })
    print(f"[ok] Bill successfully registered in database. ID: {bill_id}")
    
    # Execute OCR Pipeline
    success_ocr, warnings_ocr = ocrs.run_ocr_for_bill(bill_id, actor="Senior QA Lead")
    assert success_ocr is True, f"OCR run failed: {warnings_ocr}"
    print("[ok] OCR execution completed successfully.")
    
    # Verify accuracy of extracted fields
    bill_after_ocr = ps.get_bill_details(bill_id)
    assert bill_after_ocr["ocr_status"] == "Completed", "OCR Status should be marked Completed"
    
    ocr_json = json.loads(bill_after_ocr["normalized_json"])
    
    # Compare OCR outputs with Dakshin Haryana Bijli Vitran Nigam Bill values
    expected_fields = {
        "customer_name": "M/S CAPARO MARUTI LTD",
        "consumer_number": "2131000652X",
        "account_number": "5314860000",
        "bill_number": "531485674457",
        "billing_month": 3,
        "billing_year": 2026,
        "billing_period_start": "2026-02-01",
        "billing_period_end": "2026-03-01",
        "bill_date": "2026-03-09",
        "due_date": "2026-03-16",
        "units_consumed": 386340.0,
        "maximum_demand": 890.80,
        "connected_load": 1500.0,
        "sanctioned_load": 1500.0,
        "contract_demand": 1500.0,
        "tariff_category": "HTS",
        "discom_name": "Dakshin Haryana Bijli Vitran Nigam",
        "meter_number": "X0979476",
        "total_amount": 3386305.00,
        "energy_charges": 2685063.00,
        "fixed_charges": 400438.21,
        "taxes": 103264.52,
        "subsidy": 0.0,
        "late_fee": 49246.00,
        "power_factor": 0.95
    }
    
    accuracy_failed = []
    print("\n   [OCR Field Verifications vs Actual Bill Document]:")
    for key, expected_val in expected_fields.items():
        actual_val = ocr_json.get(key)
        if actual_val != expected_val:
            accuracy_failed.append((key, expected_val, actual_val))
            print(f"   [FAIL] Field '{key}': Expected '{expected_val}', Got '{actual_val}'")
        else:
            print(f"   [PASS] Field '{key}': Matches '{expected_val}' perfectly.")
            
    assert len(accuracy_failed) == 0, f"OCR extraction accuracy failures: {accuracy_failed}"
    print("\n[ok] OCR Extraction Accuracy verified with 100% precision.")

    # ------------------------------------------------------------
    # 7. SOLAR CALCULATION ENGINE QA AUDIT
    # ------------------------------------------------------------
    print("\n--- 7. SOLAR CALCULATION ENGINE QA AUDIT ---")
    
    success_calc, warnings_calc = calcs.run_solar_calculations(bill_id, actor="Senior QA Lead")
    assert success_calc is True, f"Solar sizing calculations failed: {warnings_calc}"
    print("[ok] Solar calculations executed successfully.")
    
    # Load calculation results
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM calculation_results WHERE bill_id = ?;", (bill_id,))
    cols = [d[0] for d in cur.description]
    calc_row = dict(zip(cols, cur.fetchone()))
    conn.close()
    
    # Audit formulas:
    # 1. Size sizing formula check: (Units / 30) / (Peak Sun Hours * Performance Ratio)
    # (386340 / 30) / (4.5 * 0.75) = 12878 / 3.375 = 3815.70 kW
    # Capped at Connected Load (1500.0 kW).
    expected_capped_size = 1500.0
    assert calc_row["plant_size_kw"] == expected_capped_size, f"Solar plant size capping failed! Expected 1500.0 kW, Got {calc_row['plant_size_kw']}"
    print(f"[ok] Capping Logic Verified: System capped sizing at {expected_capped_size} kW (sanctioned limit).")
    
    # 2. Generation logic check:
    # Annual Generation = Size * 4.5 * 365 * 0.75 = 1500 * 4.5 * 365 * 0.75 = 1,847,812.5 kWh
    expected_annual_generation = 1500.0 * 4.5 * 365.0 * 0.75
    assert calc_row["estimated_annual_generation"] == expected_annual_generation
    print(f"[ok] Annual Generation Verified: {calc_row['estimated_annual_generation']} kWh matches mathematical expectation.")
    
    # 3. Financial logic check:
    # Monthly savings = min(estimated_monthly_gen, units_consumed) * tariff
    # Monthly gen = 1500 * 4.5 * 30 * 0.75 = 151,875 kWh
    # min(151875, 386340) = 151875 kWh. Tariff = 8.0 Rs.
    # Monthly savings = 151875 * 8 = 1,215,000 Rs.
    # Annual savings = 1215000 * 12 = 14,580,000 Rs.
    assert calc_row["monthly_savings"] == 1215000.0
    assert calc_row["annual_savings"] == 14580000.0
    print(f"[ok] Financial Savings Verified: Monthly Savings Rs. {calc_row['monthly_savings']}, Annual Rs. {calc_row['annual_savings']}")
    
    # System cost: 1500 * 50,000 = 75,000,000 Rs.
    assert calc_row["system_cost"] == 75000000.0
    # Payback years = 75,000,000 / 14,580,000 = 5.14 years
    assert calc_row["payback_years"] == 5.14
    print(f"[ok] Payback Sizing Verified: Cost Rs. {calc_row['system_cost']}, Payback {calc_row['payback_years']} years.")

    # 4. Environmental offset factors check:
    # CO2 offset = 1847812.5 * 0.82 = 1515206.25 kg CO2
    # Trees equivalent = 1515206.25 * 0.04 = 60608.25 trees
    assert calc_row["co2_offset"] == 1515206.25
    assert calc_row["trees_equivalent"] == 60608.2
    print(f"[ok] Carbon Offsets Verified: CO2 Offset {calc_row['co2_offset']} kg, Tree Equivalent {calc_row['trees_equivalent']}.")

    # ------------------------------------------------------------
    # 8. PROPOSAL GENERATION & VERSIONING
    # ------------------------------------------------------------
    print("\n--- 8. PROPOSAL GENERATOR & VERSIONING TEST CASES ---")
    
    success_prop, warnings_prop, prop_id = pg.generate_proposal_record(bill_id, actor="Senior QA Lead", remarks="Caparo Feasibility proposal V1")
    assert success_prop is True
    print(f"[ok] Proposal compiled successfully. ID: {prop_id}")
    
    prop_details = ps.get_proposal_details(prop_id)
    assert prop_details["proposal_number"].startswith("ENR-"), "Proposal numbering prefix incorrect"
    assert prop_details["version"] == 1, "Proposal version must be 1"
    assert prop_details["status"] == "Draft", "Initial proposal status must be Draft"
    print(f"[ok] Proposal sequence number: {prop_details['proposal_number']}, Version: {prop_details['version']}")

    # Multi-version check
    success_prop2, warnings_prop2, prop_id2 = pg.generate_proposal_record(bill_id, actor="Senior QA Lead", remarks="Caparo Feasibility proposal V2")
    assert success_prop2 is True
    
    prop_details2 = ps.get_proposal_details(prop_id2)
    assert prop_details2["proposal_number"] == prop_details["proposal_number"], "Proposal number must remain identical across versions"
    assert prop_details2["version"] == 2, "Second proposal version must be 2"
    assert prop_details2["is_active"] == 1, "Latest version must be active"
    
    # Check old version marked inactive
    prop_details_old = ps.get_proposal_details(prop_id)
    assert prop_details_old["is_active"] == 0, "Old version must be marked inactive"
    print("[ok] Multi-versioning control validated. Version 1 marked Inactive, Version 2 marked Active.")

    # ------------------------------------------------------------
    # 9. PDF GENERATION QA
    # ------------------------------------------------------------
    print("\n--- 9. PDF GENERATION TEST CASES ---")
    
    success_pdf, pdf_path = pdfg.generate_proposal_pdf(prop_id2, actor="Senior QA Lead")
    assert success_pdf is True
    assert os.path.exists(pdf_path), "Generated PDF file must exist on disk"
    assert os.path.getsize(pdf_path) > 0, "PDF file cannot be empty"
    print(f"[ok] PDF compiled correctly and saved to path: {pdf_path}")

    # ------------------------------------------------------------
    # 10. PROJECT CONVERSION & MANAGEMENT
    # ------------------------------------------------------------
    print("\n--- 10. PROJECT CONVERSION & MANAGEMENT ---")
    
    # 1. Update proposal status to Approved (required for conversion)
    ps.update_proposal_status(prop_id2, "Approved")
    print("[ok] Proposal approved successfully.")
    
    # 2. Convert proposal to project
    success_conv, proj_id = prjs.convert_proposal_to_project(prop_id2, actor="Senior QA Lead", manager="PM Engineer")
    assert success_conv is True, f"Project conversion failed: {proj_id}"
    print(f"[ok] Project successfully created. ID: {proj_id}")
    
    # 3. Verify Customer status transitioned to 'Contract Signed'
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM customers WHERE id = ?;", (cust_id,))
    cust_status = cur.fetchone()[0]
    assert cust_status == 'Contract Signed', f"Customer status should transition to 'Contract Signed', got '{cust_status}'"
    print("[ok] Customer portfolio status successfully transitioned to 'Contract Signed'.")

    # 4. Verify sequential project numbering sequence
    proj_details = prjs.get_project_details(proj_id)
    assert proj_details["project_number"].startswith("PRJ-"), "Project number prefix incorrect"
    assert proj_details["capacity_kw"] == 1500.0, "Project capacity incorrect"
    assert proj_details["contract_value"] == 75000000.0, "Project contract value incorrect"
    print(f"[ok] Project sequence number: {proj_details['project_number']}, Value: Rs. {proj_details['contract_value']}")

    # 5. Check duplicate conversion block
    success_dup, err_dup = prjs.convert_proposal_to_project(prop_id2)
    assert success_dup is False
    assert "active project already exists" in err_dup
    print(f"[ok] Prevented duplicate conversion: {err_dup}")

    # 6. Update stage to Completed & verify completion dates
    prjs.update_project_status(
        proj_id,
        new_status="Completed",
        progress=100,
        actor="Senior QA Lead",
        remarks="Commissioned and grid-connected successfully.",
        manager="Senior PM Lead"
    )
    
    proj_details_comp = prjs.get_project_details(proj_id)
    assert proj_details_comp["status"] == "Completed"
    assert proj_details_comp["progress_percentage"] == 100
    assert proj_details_comp["actual_completion"] is not None, "Actual completion timestamp must be recorded"
    print(f"[ok] Project stage transitioned to Completed. Completion date set: {proj_details_comp['actual_completion']}")

    # 7. Document uploads verification
    # Register document upload
    mock_file = Path("uploads/projects") / proj_details_comp["project_number"] / "drawing_draft.dwg"
    mock_file.parent.mkdir(parents=True, exist_ok=True)
    with open(mock_file, "w") as f:
        f.write("MOCK DRAWING CONTENT")
        
    success_doc = prjs.add_project_document(
        project_id=proj_id,
        document_type="SLD / Engineering Drawing",
        original_filename="drawing_draft.dwg",
        stored_filename="drawing_draft.dwg",
        file_path=str(mock_file),
        file_size=20,
        uploaded_by="Senior QA Lead"
    )
    assert success_doc is True
    assert mock_file.exists()
    print(f"[ok] Document registered and stored in project hierarchy: {mock_file}")

    # ------------------------------------------------------------
    # 11. DASHBOARD & ANALYTICS KPI VERIFICATIONS
    # ------------------------------------------------------------
    print("\n--- 11. DASHBOARD & ANALYTICS KPI CHECKS ---")
    
    # Load dashboard execution overview metrics
    from services.project_service import get_project_dashboard_kpis
    kpi_list = get_project_dashboard_kpis()
    kpis = {k["label"]: k["value"] for k in kpi_list}
    assert kpis["Active Projects"] == "0", "No active projects (Completed)"
    assert kpis["Completed Projects"] == "1", "Exactly 1 completed project"
    assert kpis["Installed Capacity"] == "1.5 MW", "Installed capacity must match completed project size (1.5 MW)"
    assert kpis["Pipeline Capacity"] == "0.0 MW", "Pipeline capacity must be zero"
    assert kpis["Project Revenue"] == "$75,000,000.00", "Revenue must aggregate contract values ($75,000,000.00)"
    print("[ok] Dashboard KPI Aggregations and MW capacity metrics correct.")
    
    print("\n==========================================================")
    print("ALL E2E QA TESTS COMPLETED AND PASSED SUCCESSFULLY!")
    print("==========================================================")
    return True

if __name__ == "__main__":
    run_qa_tests()
