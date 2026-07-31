"""
Integration Test Suite - Sprint 7: Professional PDF Proposal Generator
"""

import os
import sys
import json
import shutil
from pathlib import Path

# Add project root to sys.path
sys.path.append("c:\\Users\\somya\\Downloads\\enercore-ai-portal-updated\\enercore-ai-portal")

from database.connection import get_connection, init_db
import services.customer_service as cs
import services.proposal_service as ps
import services.proposal_generator as pg
import services.pdf_generator as pdfg
import app_flask as af

def run_pdf_generator_tests():
    # Fresh database reset and directory clean
    db_path = Path("database/enercore.db")
    if db_path.exists():
        os.remove(db_path)
        
    uploads_dir = Path("uploads")
    if uploads_dir.exists():
        shutil.rmtree(uploads_dir)
        
    init_db(seed_demo=False)
    print("[1] Database initialized and clean uploads folder setup.")

    # Create test customer and site
    cs.create_customer({
        'name': 'Google Plex',
        'category': 'Commercial',
        'segment': 'Commercial · 1.0MW',
        'status': 'Active Lead',
        'tone': 'promising',
        'value_numeric': 2500000.0,
        'updated': 'Now',
        'contact': 'Sundar Pichai',
        'phone': '5556667777'
    })
    c_id = cs.list_customers()[0]['id']

    site_id = ps.create_site({
        'customer_id': c_id,
        'name': 'Mountain View HQ',
        'address_street': '1600 Amphitheatre Pkwy',
        'address_city': 'Mountain View',
        'address_state': 'CA',
        'address_zip': '94043'
    })

    # Save mock bill file
    site_dir = Path("uploads/bills") / site_id
    site_dir.mkdir(parents=True, exist_ok=True)
    bill_file = site_dir / "statement.pdf"
    bill_file.write_bytes(b"dummy document content")

    bill_id = ps.create_electricity_bill({
        'site_id': site_id,
        'billing_month': 10,
        'billing_year': 2026,
        'original_filename': 'statement.pdf',
        'stored_filename': 'statement.pdf',
        'file_path': str(bill_file),
        'file_type': 'PDF',
        'file_size': 512,
        'bill_status': 'Uploaded'
    })

    # Seed Completed OCR & calculations
    mock_ocr_json = json.dumps({
        "customer_name": "Google LLC",
        "consumer_number": "CON-9999",
        "units_consumed": "15000"
    })
    
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ocr_results (bill_id, raw_response, normalized_json, ocr_provider, ocr_version)
            VALUES (?, ?, ?, ?, ?);
        """, (bill_id, "mock ocr", mock_ocr_json, "Demo", "1.0"))
        ocr_id = cur.lastrowid
        
        cur.execute("""
            INSERT INTO calculation_results (
                bill_id, plant_size_kw, recommended_inverter_kw, estimated_monthly_generation,
                estimated_annual_generation, monthly_savings, annual_savings, system_cost,
                payback_years, co2_offset, trees_equivalent, calculation_version, calculation_status
            ) VALUES (?, 150.0, 150.0, 15000.0, 180000.0, 120000.0, 1440000.0, 7500000.0, 5.2, 147600.0, 5904.0, '1.0', 'Success');
        """, (bill_id,))
        calc_id = cur.lastrowid
        
        cur.execute("""
            UPDATE electricity_bills
            SET ocr_status = 'Completed', latest_ocr_result_id = ?, latest_calculation_id = ?
            WHERE id = ?;
        """, (ocr_id, calc_id, bill_id))
        conn.commit()
    finally:
        conn.close()

    # Generate the proposal V1
    success, warnings, prop_id = pg.generate_proposal_record(bill_id, actor="Systems Architect", remarks="Mountain View Initial feasibility")
    assert success is True
    print("[2] Compiled proposal record V1:", prop_id)

    # Test 1: Generate PDF Document for proposal V1
    pdf_success, pdf_path = pdfg.generate_proposal_pdf(prop_id, actor="Systems Architect")
    assert pdf_success is True
    
    # Check physical folder structure and filename formatting
    expected_filename = "ENR-2026-0001-V1.pdf"
    expected_relative_path = "uploads/proposals/ENR-2026-0001/ENR-2026-0001-V1.pdf"
    
    assert pdf_path == expected_relative_path
    assert os.path.exists(pdf_path) is True
    assert os.path.getsize(pdf_path) > 0 # PDF file has bytes
    print("[Test 1 Passed] Proposal PDF compiled correctly to: ", pdf_path)

    # Test 2: Database Persistence
    prop_details = ps.get_proposal_details(prop_id)
    assert prop_details["pdf_filename"] == expected_filename
    assert prop_details["pdf_path"] == expected_relative_path
    assert prop_details["pdf_generated_by"] == "Systems Architect"
    assert prop_details["pdf_generated_at"] is not None
    print("[Test 2 Passed] Database metadata holds correct fields.")

    # Test 3: Multiple PDF versions side-by-side
    # Generate new proposal version V2
    success2, warnings2, prop_id2 = pg.generate_proposal_record(bill_id, actor="Systems Architect", remarks="Mountain View V2 optimized")
    assert success2 is True
    
    # Generate PDF for V2
    pdf_success2, pdf_path2 = pdfg.generate_proposal_pdf(prop_id2, actor="Principal Engineer")
    assert pdf_success2 is True
    expected_path_v2 = "uploads/proposals/ENR-2026-0001/ENR-2026-0001-V2.pdf"
    assert pdf_path2 == expected_path_v2
    assert os.path.exists(pdf_path2) is True
    
    # Verify V1 PDF file is preserved and not deleted or overwritten!
    assert os.path.exists(pdf_path) is True
    print("[Test 3 Passed] Multiple PDF versions stored separately and previous versions preserved.")

    # Test 4: Download and HTML Preview routing checks
    with af.app.test_client() as client:
        with client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['user'] = {'full_name': 'Test Engineer', 'email': 'test@enercore.ai', 'role': 'Sales'}
            
        # Download route for V2
        r_dl = client.get(f'/proposal/{prop_id2}/download')
        assert r_dl.status_code == 200
        assert r_dl.headers["Content-Disposition"].startswith("attachment;")
        assert "ENR-2026-0001-V2.pdf" in r_dl.headers["Content-Disposition"]
        
        # Download route for V1
        r_dl_v1 = client.get(f'/proposal/{prop_id}/download')
        assert r_dl_v1.status_code == 200
        assert "ENR-2026-0001-V1.pdf" in r_dl_v1.headers["Content-Disposition"]
        
        # Test preview template rendering button outputs
        r_prev = client.get(f'/proposal/{prop_id2}')
        assert r_prev.status_code == 200
        assert b"Download PDF Proposal" in r_prev.data
        assert b"Regenerate PDF Document" in r_prev.data
        assert b"Systems Architect" in r_prev.data # Prepared by
        
    print("\n[ALL SPRINT 7 TESTS PASSED SUCCESSFULLY!]")

if __name__ == "__main__":
    run_pdf_generator_tests()
