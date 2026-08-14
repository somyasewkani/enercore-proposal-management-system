import sqlite3
import os

# Set test database environment override before other imports to prevent interference
db_test_path = os.path.join(os.path.dirname(__file__), "database", "enercore_test.db")
os.environ["TEST_DB_FILE"] = db_test_path

import unittest
from database.connection import get_connection, init_db
from services.pipeline_service import (
    init_pipeline_db,
    create_pipeline_deal,
    update_deal_stage,
    get_pipeline_summary,
    get_pipeline_stage_counts,
    get_pipeline_cards,
    archive_pipeline_deal,
    restore_pipeline_deal,
    delete_pipeline_deal,
    get_allowed_transitions,
    is_valid_transition
)
from services.dashboard_service import get_dashboard_kpis, get_followups
from services.project_service import get_project_dashboard_kpis, get_project_execution_overview

class TestPipelineCRM(unittest.TestCase):
    def setUp(self):
        # Force SQLite database to reset cleanly for unit testing
        db_path = os.environ["TEST_DB_FILE"]
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass
            try:
                os.remove(db_path)
            except OSError:
                pass
        init_db(seed_demo=False)
        init_pipeline_db(seed_demo=False)

    def test_lifecycle_validation_transitions(self):
        # Enforce lifecycle progression:
        # New Lead -> Contacted -> Bill Received -> Analysis Completed -> Proposal Sent -> Negotiation -> Won
        self.assertTrue(is_valid_transition("New Lead", "Contacted"))
        self.assertTrue(is_valid_transition("New Lead", "Lost"))
        self.assertFalse(is_valid_transition("New Lead", "Won")) # Cannot skip directly to Won
        self.assertTrue(is_valid_transition("New Lead", "Proposal Sent"))
        
        self.assertTrue(is_valid_transition("Contacted", "Bill Received"))
        self.assertTrue(is_valid_transition("Contacted", "New Lead")) # backward allowed
        
        self.assertTrue(is_valid_transition("Negotiation", "Won"))
        self.assertTrue(is_valid_transition("Negotiation", "Lost"))
        
        # Won can transition to Negotiation or New Lead (re-opening)
        self.assertTrue(is_valid_transition("Won", "New Lead"))
        self.assertTrue(is_valid_transition("Won", "Negotiation"))
        self.assertFalse(is_valid_transition("Won", "Contacted"))

    def test_create_and_move_deal(self):
        # Create deal
        success = create_pipeline_deal({
            "company_name": "Test Company Alpha",
            "category": "COMMERCIAL",
            "value_numeric": 500000.0,
            "stage": "New Lead",
            "contact_person": "QA Agent"
        })
        self.assertTrue(success)
        
        cards = get_pipeline_cards()
        deals_new = cards["New Lead"]["deals"]
        self.assertEqual(len(deals_new), 1)
        deal = deals_new[0]
        self.assertEqual(deal["company_name"], "Test Company Alpha")
        self.assertEqual(deal["value_numeric"], 500000.0)
        self.assertEqual(deal["stage"], "New Lead")
        
        # Verify backing customer exists
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT status, is_deleted FROM customers WHERE id = ?;", (deal["customer_id"],))
        cust = cur.fetchone()
        self.assertIsNotNone(cust)
        self.assertEqual(cust[0], "New Lead")
        self.assertEqual(cust[1], 0)
        conn.close()
        
        # Move to Contacted (Valid)
        success_move = update_deal_stage(deal["id"], "Contacted")
        self.assertTrue(success_move)
        
        # Move directly to Won (Invalid, should fail validation)
        success_invalid = update_deal_stage(deal["id"], "Won")
        self.assertFalse(success_invalid)
        
        # Check that it did NOT move
        cards = get_pipeline_cards()
        self.assertEqual(len(cards["Contacted"]["deals"]), 1)
        self.assertEqual(len(cards["Won"]["deals"]), 0)

    def test_winning_lead_proposal_project_integration(self):
        # Create a lead
        create_pipeline_deal({
            "company_name": "Solar Corp Beta",
            "category": "INDUSTRIAL",
            "value_numeric": 1200000.0,
            "stage": "New Lead"
        })
        
        cards = get_pipeline_cards()
        deal = cards["New Lead"]["deals"][0]
        cust_id = deal["customer_id"]
        
        # Register a site, bill, calculation and approved proposal for this customer
        # We simulate this in database to test the integration directly
        conn = get_connection()
        cur = conn.cursor()
        
        # Create site
        site_id = "site_beta_1"
        cur.execute("""
            INSERT INTO sites (id, customer_id, name, address_street)
            VALUES (?, ?, 'Beta Factory', '123 Solar Way');
        """, (site_id, cust_id))
        
        # Create proposal
        prop_id = "prop_beta_1"
        cur.execute("""
            INSERT INTO proposals (id, proposal_number, customer_id, site_id, status, plant_size_kw, system_cost, is_active)
            VALUES (?, 'ENR-2026-9999', ?, ?, 'Approved', 1000.0, 50000000.0, 1);
        """, (prop_id, cust_id, site_id))
        
        conn.commit()
        conn.close()
        
        # Move deal through stages to Negotiation
        self.assertTrue(update_deal_stage(deal["id"], "Contacted"))
        self.assertTrue(update_deal_stage(deal["id"], "Bill Received"))
        self.assertTrue(update_deal_stage(deal["id"], "Analysis Completed"))
        self.assertTrue(update_deal_stage(deal["id"], "Proposal Sent"))
        self.assertTrue(update_deal_stage(deal["id"], "Negotiation"))
        
        # Check proposal is linked in pipeline cards
        cards = get_pipeline_cards()
        d_negotiation = cards["Negotiation"]["deals"][0]
        self.assertEqual(d_negotiation["latest_proposal_id"], prop_id)
        self.assertEqual(d_negotiation["latest_proposal_status"], "Approved")
        
        # Now mark Won! This should trigger convert_proposal_to_project automatically!
        self.assertTrue(update_deal_stage(deal["id"], "Won"))
        
        # Verify deal is in Won column
        cards = get_pipeline_cards()
        self.assertEqual(len(cards["Won"]["deals"]), 1)
        
        # Verify project was automatically created in database!
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), capacity_kw, contract_value FROM projects WHERE proposal_id = ?;", (prop_id,))
        proj = cur.fetchone()
        self.assertEqual(proj[0], 1)
        self.assertEqual(proj[1], 1000.0)
        self.assertEqual(proj[2], 50000000.0)
        
        # Verify customer status updated to Contract Signed
        cur.execute("SELECT status FROM customers WHERE id = ?;", (cust_id,))
        self.assertEqual(cur.fetchone()[0], "Contract Signed")
        conn.close()

    def test_dashboard_sync(self):
        # Empty database KPIs
        summary = get_pipeline_summary()
        self.assertEqual(summary["total_leads"], 0)
        self.assertEqual(summary["pipeline_value"], 0.0)
        
        # Create multiple deals
        create_pipeline_deal({"company_name": "Client A", "category": "RETAIL", "value_numeric": 100000.0})
        create_pipeline_deal({"company_name": "Client B", "category": "COMMERCIAL", "value_numeric": 300000.0})
        
        # Verify summary updates
        summary = get_pipeline_summary()
        self.assertEqual(summary["total_leads"], 2)
        self.assertEqual(summary["active_leads"], 2)
        self.assertEqual(summary["pipeline_value"], 400000.0)
        self.assertEqual(summary["average_deal_size"], 200000.0)
        self.assertEqual(summary["conversion_rate"], 0.0)
        
        # Get dashboard KPIs
        kpis = get_dashboard_kpis()
        kpi_map = {k["label"]: k["value"] for k in kpis}
        self.assertEqual(kpi_map["Total Leads"], "2")
        self.assertEqual(kpi_map["Active Leads"], "2")
        self.assertEqual(kpi_map["Pipeline Value"], "$400,000.00")

    def test_archive_restore_deal(self):
        create_pipeline_deal({"company_name": "Temp Company", "category": "MUNICIPAL", "value_numeric": 800000.0})
        
        cards = get_pipeline_cards()
        deal = cards["New Lead"]["deals"][0]
        
        # Archive
        self.assertTrue(archive_pipeline_deal(deal["id"]))
        
        # Cards should be empty now
        cards = get_pipeline_cards()
        self.assertEqual(len(cards["New Lead"]["deals"]), 0)
        
        # Summary should be 0
        summary = get_pipeline_summary()
        self.assertEqual(summary["total_leads"], 0)
        
        # Restore
        self.assertTrue(restore_pipeline_deal(deal["id"]))
        
        # Should be back
        cards = get_pipeline_cards()
        self.assertEqual(len(cards["New Lead"]["deals"]), 1)
        self.assertEqual(cards["New Lead"]["deals"][0]["company_name"], "Temp Company")

    def test_dashboard_date_filtering(self):
        import datetime
        from database.connection import get_connection
        
        # Clear existing tables first
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM pipeline_deals;")
        cur.execute("DELETE FROM customers;")
        cur.execute("DELETE FROM followups;")
        cur.execute("DELETE FROM projects;")
        conn.commit()
        conn.close()
        
        # Helper to insert a deal with a specific created_at date
        # and its backing customer and project/followup with same created_at
        def insert_test_data(deal_id, company, val, days_ago):
            now = datetime.datetime.now()
            created_date = now - datetime.timedelta(days=days_ago)
            created_str = created_date.strftime("%Y-%m-%d %H:%M:%S")
            
            cust_id = f"cus_{deal_id}"
            
            conn = get_connection()
            cur = conn.cursor()
            # Customer
            cur.execute("""
                INSERT INTO customers (id, name, category, status, is_deleted, created_at)
                VALUES (?, ?, 'Industrial', 'New Lead', 0, ?);
            """, (cust_id, company, created_str))
            
            # Pipeline Deal
            cur.execute("""
                INSERT INTO pipeline_deals (id, customer_id, category, value_numeric, stage, contact_person, is_archived, status, created_at)
                VALUES (?, ?, 'Industrial', ?, 'New Lead', 'Test Contact', 0, 'Active', ?);
            """, (deal_id, cust_id, val, created_str))
            
            # Followup
            cur.execute("""
                INSERT INTO followups (due_when, title, note, created_at)
                VALUES ('Tomorrow', ?, 'Notes here', ?);
            """, (f"Follow up with {company}", created_str))
            
            # Proposal
            prop_id = f"prop_{deal_id}"
            cur.execute("""
                INSERT INTO proposals (id, proposal_number, customer_id, status, is_active, created_at)
                VALUES (?, ?, ?, 'Approved', 1, ?);
            """, (prop_id, f"PROP-2026-{deal_id}", cust_id, created_str))
            
            # Project (Only for Won deals, or let's create a project separately with created_at)
            proj_id = f"proj_{deal_id}"
            cur.execute("""
                INSERT INTO projects (id, project_number, proposal_id, customer_id, project_name, status, capacity_kw, contract_value, created_at)
                VALUES (?, ?, ?, ?, ?, 'Planning', 10.0, ?, ?);
            """, (proj_id, f"PRJ-2026-{deal_id}", prop_id, cust_id, f"Project {company}", val, created_str))
            
            conn.commit()
            conn.close()

        # Insert records spread across different time ranges
        insert_test_data("deal_today", "Company Today", 100000.0, 0)      # Today (in 30, 90, year, all)
        insert_test_data("deal_15d", "Company 15 Days", 200000.0, 15)   # 15 days ago (in 30, 90, year, all)
        insert_test_data("deal_45d", "Company 45 Days", 300000.0, 45)   # 45 days ago (in 90, year, all)
        insert_test_data("deal_120d", "Company 120 Days", 400000.0, 120) # 120 days ago (in year, all)
        insert_test_data("deal_2y", "Company 2 Years", 500000.0, 730)   # 2 years ago (in all only)

        # 1. Test Last 30 Days filter
        summary_30 = get_pipeline_summary("30")
        self.assertEqual(summary_30["total_leads"], 2) # Today + 15d
        self.assertEqual(summary_30["pipeline_value"], 300000.0) # 100k + 200k
        
        kpis_30 = get_dashboard_kpis("30")
        kpi_30_map = {k["label"]: k["value"] for k in kpis_30}
        self.assertEqual(kpi_30_map["Total Leads"], "2")
        self.assertEqual(kpi_30_map["Pipeline Value"], "$300,000.00")
        
        proj_30 = get_project_execution_overview("30")
        self.assertEqual(proj_30["active_projects"], 2)
        
        followups_30 = get_followups("30")
        self.assertEqual(len(followups_30), 2)

        # 2. Test Last 90 Days filter
        summary_90 = get_pipeline_summary("90")
        self.assertEqual(summary_90["total_leads"], 3) # Today + 15d + 45d
        self.assertEqual(summary_90["pipeline_value"], 600000.0) # 100k + 200k + 300k
        
        kpis_90 = get_dashboard_kpis("90")
        kpi_90_map = {k["label"]: k["value"] for k in kpis_90}
        self.assertEqual(kpi_90_map["Total Leads"], "3")
        self.assertEqual(kpi_90_map["Pipeline Value"], "$600,000.00")
        
        proj_90 = get_project_execution_overview("90")
        self.assertEqual(proj_90["active_projects"], 3)
        
        followups_90 = get_followups("90")
        self.assertEqual(len(followups_90), 3)

        # 3. Test This Year filter
        summary_yr = get_pipeline_summary("year")
        self.assertEqual(summary_yr["total_leads"], 4) # Today + 15d + 45d + 120d
        self.assertEqual(summary_yr["pipeline_value"], 1000000.0) # 100k + 200k + 300k + 400k
        
        proj_yr = get_project_execution_overview("year")
        self.assertEqual(proj_yr["active_projects"], 4)
        
        followups_yr = get_followups("year")
        self.assertEqual(len(followups_yr), 4)

        # 4. Test All Time filter
        summary_all = get_pipeline_summary("all")
        self.assertEqual(summary_all["total_leads"], 5)
        self.assertEqual(summary_all["pipeline_value"], 1500000.0)
        
        proj_all = get_project_execution_overview("all")
        self.assertEqual(proj_all["active_projects"], 5)
        
        followups_all = get_followups("all")
        self.assertEqual(len(followups_all), 5)

if __name__ == "__main__":
    unittest.main()
