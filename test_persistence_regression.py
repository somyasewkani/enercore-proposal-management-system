import os
import sys
import unittest
import sqlite3
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Setup sys.path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import run_migrations, init_db
from services.customer_service import create_customer, update_customer_profile, delete_customer, get_customer, update_customer_status
from services.proposal_service import delete_electricity_bill, get_all_proposals
from services.pipeline_service import update_deal_stage, get_all_deals_by_stage

# Fix console encoding print issues in some Windows shells
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

class TestPersistenceRegression(unittest.TestCase):
    def setUp(self):
        # We must set TEST_DB_FILE so connection/services use the test db
        self.db_path = Path("database/test_persistence_reg.db")
        self.bak_path = Path("database/test_persistence_reg.db.bak")
        os.environ["TEST_DB_FILE"] = str(self.db_path)
        self.cleanup()
        
        # Initialize full schema
        init_db(seed_demo=False)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()
        self.cleanup()
        if "TEST_DB_FILE" in os.environ:
            del os.environ["TEST_DB_FILE"]

    def cleanup(self):
        for p in [self.db_path, self.bak_path]:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass

    def run_restart_migration_simulation(self):
        """Simulate a Flask/Gunicorn server restart where run_migrations triggers."""
        # Close connection to simulate process exit
        self.conn.close()
        
        # Re-open connection in new process-like environment
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.row_factory = sqlite3.Row
        
        # Point Path("enercore.db") to our test db during run_migrations
        with patch("database.connection.Path") as mock_path:
            mock_path_instance = mock_path.return_value
            mock_path.parent = mock_path_instance
            mock_path.__truediv__ = lambda self, other: Path("database/test_persistence_reg.db") if "enercore.db" in other else Path("database/migration_report.log")
            run_migrations(self.conn, is_sqlite=True, dry_run=False)

    def test_customer_creation_persists_across_restart(self):
        # 1. Create customer
        cust_data = {
            "name": "QA Enterprise India Ltd",
            "contact": "Pranav Shah",
            "phone": "+91 98765 43210",
            "email": "pranav@qa-enterprise.in",
            "address": "452, Gurugram, HR",
            "gstin": "06AAAAA0000A1Z2",
            "category": "Industrial",
            "value_numeric": 50000000.0,
            "capacity_mw": 2.5
        }
        cust = create_customer(cust_data)
        cust_id = cust["id"]
        
        # 2. Simulate restart / run_migrations
        self.run_restart_migration_simulation()
        
        # 3. Verify customer still exists
        fetched = get_customer(cust_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "QA Enterprise India Ltd")
        self.assertEqual(fetched["is_deleted"], 0)

    def test_customer_edit_persists_across_restart(self):
        # 1. Create and edit customer
        cust_data = {
            "name": "Original Name LLC",
            "contact": "Pranav Shah",
            "category": "Commercial",
            "value_numeric": 100000.0,
            "capacity_mw": 0.5
        }
        cust = create_customer(cust_data)
        cust_id = cust["id"]
        
        cust_data["name"] = "Updated Name LLC"
        update_customer_profile(cust_id, cust_data)
        
        # 2. Simulate restart / run_migrations
        self.run_restart_migration_simulation()
        
        # 3. Verify edits persist
        fetched = get_customer(cust_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "Updated Name LLC")

    def test_customer_archive_persists_across_restart(self):
        # 1. Create and archive customer
        cust_data = {
            "name": "Archive Me Inc",
            "contact": "Tester",
            "category": "Commercial"
        }
        cust = create_customer(cust_data)
        cust_id = cust["id"]
        
        success, msg = delete_customer(cust_id, permanent=False)
        self.assertTrue(success)
        
        # 2. Simulate restart / run_migrations
        self.run_restart_migration_simulation()
        
        # 3. Verify customer remains archived (is_deleted = 1)
        fetched = get_customer(cust_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["is_deleted"], 1)
        self.assertEqual(fetched["status"], "Archived")

    def test_customer_restore_persists_across_restart(self):
        from services.customer_service import restore_customer
        
        # 1. Create and archive customer
        cust_data = {
            "name": "Restore Me Inc",
            "contact": "Tester",
            "category": "Commercial"
        }
        cust = create_customer(cust_data)
        cust_id = cust["id"]
        
        success, msg = delete_customer(cust_id, permanent=False)
        self.assertTrue(success)
        
        # Verify archived status
        fetched = get_customer(cust_id)
        self.assertEqual(fetched["is_deleted"], 1)
        self.assertEqual(fetched["status"], "Archived")
        
        # 2. Restore the customer
        success_restore, msg_restore = restore_customer(cust_id)
        self.assertTrue(success_restore)
        
        # 3. Simulate restart / run_migrations
        self.run_restart_migration_simulation()
        
        # 4. Verify customer is active and restored
        fetched = get_customer(cust_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["is_deleted"], 0)
        self.assertEqual(fetched["status"], "New Lead") # Inferred default

    def test_customer_restore_stage_inference(self):
        from services.customer_service import restore_customer
        
        # 1. Proposal Case
        cust_data = {
            "name": "Inference Proposal Client",
            "contact": "Tester",
            "category": "Commercial"
        }
        cust = create_customer(cust_data)
        cust_id = cust["id"]
        
        # Add a dummy proposal in the database directly
        cur = self.conn.cursor()
        cur.execute("INSERT INTO proposals (id, proposal_number, customer_id, version, status) VALUES ('prop_infer_test', 'ENR-2026-0001', ?, 1, 'Draft');", (cust_id,))
        self.conn.commit()
        
        # Archive
        delete_customer(cust_id, permanent=False)
        
        # Restore
        success, msg = restore_customer(cust_id)
        self.assertTrue(success)
        
        # Verify inferred stage is 'Proposal Sent'
        fetched = get_customer(cust_id)
        self.assertEqual(fetched["status"], "Proposal Sent")

        # 2. Project Case
        cust_data_b = {
            "name": "Inference Project Client",
            "contact": "Tester",
            "category": "Commercial"
        }
        cust_b = create_customer(cust_data_b)
        cust_id_b = cust_b["id"]
        
        # Add a dummy project in the database directly
        cur.execute(
            "INSERT INTO projects (id, project_number, proposal_id, customer_id, project_name, status) VALUES ('prj_infer_test', 'PRJ-2026-0001', 'prop_infer_test', ?, 'Project 1', 'Planning');",
            (cust_id_b,)
        )
        self.conn.commit()
        
        # Archive
        delete_customer(cust_id_b, permanent=False)
        
        # Restore
        success_b, msg_b = restore_customer(cust_id_b)
        self.assertTrue(success_b)
        
        # Verify inferred stage is 'Contract Signed'
        fetched_b = get_customer(cust_id_b)
        self.assertEqual(fetched_b["status"], "Contract Signed")

    def test_bill_deletion_persists_across_restart(self):
        # 1. Setup site and bill
        cur = self.conn.cursor()
        cur.execute("INSERT INTO customers (id, name, category, status, contact) VALUES ('cus_bill_test', 'Bill Cust', 'Commercial', 'New Lead', 'QA Contact');")
        cur.execute("INSERT INTO sites (id, customer_id, name, is_deleted) VALUES ('site_test', 'cus_bill_test', 'Site 1', 0);")
        cur.execute("""
            INSERT INTO electricity_bills (id, site_id, billing_month, billing_year, is_deleted)
            VALUES ('bill_test', 'site_test', 3, 2026, 0);
        """)
        self.conn.commit()
        
        # Delete bill (soft delete)
        success = delete_electricity_bill('bill_test')
        self.assertTrue(success)
        
        # 2. Simulate restart / run_migrations
        self.run_restart_migration_simulation()
        
        # 3. Verify deletion persists (is_deleted = 1)
        cur = self.conn.cursor()
        cur.execute("SELECT is_deleted FROM electricity_bills WHERE id = 'bill_test';")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)

    def test_proposal_update_persists_across_restart(self):
        # 1. Setup customer, site, bill, and proposal
        cur = self.conn.cursor()
        cur.execute("INSERT INTO customers (id, name, category, status, contact) VALUES ('cus_prop_test', 'Prop Cust', 'Commercial', 'New Lead', 'QA Contact');")
        cur.execute("INSERT INTO sites (id, customer_id, name, is_deleted) VALUES ('site_prop_test', 'cus_prop_test', 'Site 1', 0);")
        cur.execute("INSERT INTO electricity_bills (id, site_id, billing_month, billing_year, is_deleted) VALUES ('bill_prop_test', 'site_prop_test', 3, 2026, 0);")
        cur.execute("""
            INSERT INTO proposals (id, proposal_number, customer_id, site_id, bill_id, proposal_name, status)
            VALUES ('prop_test', 'ENR-2026-9999', 'cus_prop_test', 'site_prop_test', 'bill_prop_test', 'Prop V1', 'Draft');
        """)
        self.conn.commit()
        
        # Update proposal name/status directly and commit
        cur.execute("UPDATE proposals SET proposal_name = 'Prop V1 Updated', status = 'Under Review' WHERE id = 'prop_test';")
        self.conn.commit()
        
        # 2. Simulate restart / run_migrations
        self.run_restart_migration_simulation()
        
        # 3. Verify changes persist
        cur = self.conn.cursor()
        cur.execute("SELECT proposal_name, status FROM proposals WHERE id = 'prop_test';")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "Prop V1 Updated")
        self.assertEqual(row[1], "Under Review")

    def test_pipeline_stage_update_persists_across_restart(self):
        # 1. Setup customer and pipeline deal
        cust_data = {
            "name": "Pipeline Cust LLC",
            "category": "Commercial",
            "status": "New Lead",
            "contact": "Senior QA Lead"
        }
        cust = create_customer(cust_data)
        cust_id = cust["id"]
        
        # Auto-migration or manual setup created a deal. Let's find/update it.
        # Run restart migration once to ensure deal is auto-created dynamically by Sprint 10 logic
        self.run_restart_migration_simulation()
        
        cur = self.conn.cursor()
        cur.execute("SELECT id, stage FROM pipeline_deals WHERE customer_id = ?;", (cust_id,))
        deal_row = cur.fetchone()
        self.assertIsNotNone(deal_row, "A pipeline deal must be auto-created for customer with active activity")
        deal_id = deal_row[0]
        self.assertEqual(deal_row[1], "New Lead")
        
        # Update stage via pipeline service
        success = update_deal_stage(deal_id, "Proposal Sent")
        self.assertTrue(success)
        
        # 2. Simulate restart / run_migrations
        self.run_restart_migration_simulation()
        
        # 3. Verify stage persists
        cur = self.conn.cursor()
        cur.execute("SELECT stage FROM pipeline_deals WHERE id = ?;", (deal_id,))
        self.assertEqual(cur.fetchone()[0], "Proposal Sent")

    @patch("shutil.copy2")
    def test_backup_permission_error_does_not_overwrite_committed_database(self, mock_copy):
        # 1. Setup legacy backup
        with open(self.bak_path, "w") as f:
            f.write("LEGACY BACKUP DATA")
            
        # 2. Commit customer successfully
        cur = self.conn.cursor()
        cur.execute("INSERT INTO customers (id, name, category, status, contact, is_deleted) VALUES (?, ?, ?, ?, ?, 0);", 
                    ("cus_permission_test", "Committed Customer LLC", "Commercial", "New Lead", "QA Contact"))
        self.conn.commit()

        # 3. Restart where backup fails with PermissionError (e.g. file lock on Windows)
        mock_copy.side_effect = PermissionError("Windows File Lock")

        # Run migration. It should skip backup and complete successfully without restoring/overwriting.
        try:
            self.run_restart_migration_simulation()
        except Exception as e:
            self.fail(f"run_migrations raised unexpected exception: {e}")

        # 4. Verify committed data is NOT overwritten by legacy backup
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM customers WHERE id = 'cus_permission_test';")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "Committed Customer LLC")
        print("[ok] Regression Test Passed: committed database is NOT overwritten when backup creation fails with PermissionError.")

    def test_solar_capacity_pipeline_calculation(self):
        from services.dashboard_service import get_capacity_pipeline
        import datetime
        
        # 1. Verify empty database behaves gracefully
        empty_res = get_capacity_pipeline()
        self.assertEqual(len(empty_res["labels"]), 6)
        self.assertEqual(sum(empty_res["residential"]), 0.0)
        self.assertEqual(sum(empty_res["commercial"]), 0.0)
        
        # 2. Add an approved proposal for a Commercial customer
        cur = self.conn.cursor()
        cur.execute("INSERT INTO customers (id, name, category, status, is_deleted) VALUES ('cus_cap_p1', 'Cap Cust Commercial', 'Commercial', 'Proposal Sent', 0);")
        
        today = datetime.date.today()
        current_ym = f"{today.year:04d}-{today.month:02d}-01"
        
        cur.execute("""
            INSERT INTO proposals (id, proposal_number, customer_id, plant_size_kw, prepared_date, status, is_active)
            VALUES ('prop_cap_1', 'PROP-CAP-0001', 'cus_cap_p1', 1200.0, ?, 'Approved', 1);
        """, (current_ym,))
        
        self.conn.commit()
        
        # Calculate
        pipeline = get_capacity_pipeline()
        self.assertEqual(pipeline["commercial"][0], 1.2) # 1200 kW = 1.2 MW
        self.assertEqual(pipeline["residential"][0], 0.0)
        
        # 3. Add an active project for a Residential customer
        cur.execute("INSERT INTO customers (id, name, category, status, is_deleted) VALUES ('cus_cap_p2', 'Cap Cust Residential', 'Residential', 'Contract Signed', 0);")
        cur.execute("""
            INSERT INTO projects (id, project_number, proposal_id, customer_id, project_name, capacity_kw, start_date, status)
            VALUES ('proj_cap_1', 'PROJ-CAP-0001', 'prop_cap_1', 'cus_cap_p2', 'Proj 1', 500.0, ?, 'Planning');
        """, (current_ym,))
        self.conn.commit()
        
        # Calculate
        pipeline = get_capacity_pipeline()
        self.assertEqual(pipeline["residential"][0], 0.5) # 500 kW = 0.5 MW
        
        # The proposal is now converted to project, so it must be excluded to prevent double counting
        self.assertEqual(pipeline["commercial"][0], 0.0)

if __name__ == '__main__':
    unittest.main()
