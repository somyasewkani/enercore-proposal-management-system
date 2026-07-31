import os
import sqlite3
import json
from datetime import datetime
from typing import Tuple
from flask import render_template
from xhtml2pdf import pisa

from database.connection import get_connection
from services.proposal_service import get_proposal_details, get_system_settings, log_site_activity

def generate_proposal_pdf(proposal_id: str, actor: str = "System") -> Tuple[bool, str]:
    """Compiles proposal HTML templates into a professional multi-page PDF on the disk."""
    # 1. Load and validate proposal details
    proposal = get_proposal_details(proposal_id)
    if not proposal:
        return False, "Proposal does not exist."
        
    # Check status
    if proposal.get("status") in ["Rejected", "Expired"]:
        return False, f"Cannot generate PDF for {proposal['status']} proposals."
        
    # Validate required feasibility info exists
    if proposal.get("plant_size_kw") is None or proposal.get("system_cost") is None:
        return False, "Feasibility solar sizing calculations are missing from this proposal version."
        
    # Load system settings and parsed OCR data
    settings = get_system_settings()
    
    ocr_data = {}
    if proposal.get("normalized_json"):
        try:
            ocr_data = json.loads(proposal["normalized_json"])
        except Exception:
            pass

    # 2. Render Template within Flask Application Context
    from app_flask import app
    with app.app_context():
        try:
            html_content = render_template(
                'pdf/proposal_pdf.html',
                proposal=proposal,
                settings=settings,
                ocr_data=ocr_data
            )
        except Exception as e:
            return False, f"HTML template compilation error: {e}"

    # 3. Define Storage Paths
    prop_number = proposal["proposal_number"]
    version = proposal["version"]
    filename = f"{prop_number}-V{version}.pdf"
    
    dest_dir = os.path.join("uploads", "proposals", prop_number)
    os.makedirs(dest_dir, exist_ok=True)
    pdf_path = os.path.join(dest_dir, filename)

    # 4. Generate PDF via xhtml2pdf
    try:
        with open(pdf_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
            
        if pisa_status.err:
            return False, f"PDF engine compilation error code: {pisa_status.err}"
    except Exception as e:
        return False, f"Unexpected error during PDF generation: {e}"

    # 5. Save PDF metadata to database
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # Format current timestamp
        current_time = datetime.now()
        
        update_query = """
            UPDATE proposals
            SET pdf_filename = ?, pdf_path = ?, pdf_generated_at = ?, pdf_generated_by = ?, updated_at = ?
            WHERE id = ?;
        """ if is_sqlite else """
            UPDATE proposals
            SET pdf_filename = %s, pdf_path = %s, pdf_generated_at = %s, pdf_generated_by = %s, updated_at = %s
            WHERE id = %s;
        """
        
        cur.execute(update_query, (
            filename,
            pdf_path.replace("\\", "/"), # standardize forward slashes
            current_time,
            actor,
            current_time,
            proposal_id
        ))
        conn.commit()
        
        # Log timeline audit trail
        log_site_activity(
            proposal["site_id"],
            "PDF Generated",
            f"Client PDF document compiled for version V{version} ({filename}).",
            actor
        )
        return True, pdf_path.replace("\\", "/")
        
    except Exception as e:
        conn.rollback()
        return False, f"Database error updating PDF metadata: {e}"
    finally:
        conn.close()
