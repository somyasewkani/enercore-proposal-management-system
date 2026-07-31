# Changelog - Enercore AI Proposal & Project Management Portal
All notable changes and milestones achieved in this project will be documented here.

## [1.0.0] - 2026-07-28

### Added
* **CRM Kanban Pipeline Stage Movement:** CRM pipeline dashboard mapping deals by stages with columns value aggregates and stage update routing.
* **Electricity Bill OCR Parsing:** Advanced multimodal parsing using Gemini API to extract bill billing parameters (Consumer Numbers, Connected Loads, billing periods, energy charges, MDI, due dates). Includes Caparo Maruti statement fallback parsing.
* **Solar Sizing Calculations:** Mathematical calculation engine supporting power recommended capacity, energy generation models, annual ROI savings, system cost estimations, tree equivalence calculations, and sanctioned load capping warnings.
* **Multi-Version Proposal Generator:** Sequential numbering generation (`ENR-YYYY-XXXX`) and multi-version history picking (allowing revisions V1, V2 side-by-side).
* **High-fidelity PDF Compiler:** Automated cover page, Technical & Financial summary sections, signature grids, disclaimers, and file system output writing (`uploads/proposals/`).
* **Project Conversion & Lifecycles:** Project conversion mapping after approval, auto-increment numbers (`PRJ-YYYY-XXXX`), custom timeline activity tracking, drawing attachments uploads, and dashboard progress bars.
* **Dynamic Reports & Analytics:** Live Chart.js graphs mapping monthly project creation metrics, lead conversion trends, and category capacity MW distributions.
* **Format Validators:** Backend regex checking for corporate email addresses, phone digits, and 15-char alpha-numeric Indian GSTIN configurations.
* **Archiving safety controls:** Deletions refactored to soft-delete archive logs, hiding records from regular listings by default. Permanent hard delete is blocked if active proposals, sites, or projects exist under the customer.

### Changed
* **Database Adapter:** SQLite and PostgreSQL adapter refactored to check column presence before executing dynamic `ALTER TABLE` migrations, preventing syntax failures.
* **Chart.js integrations:** Replaced SVG charts with dynamic interactive Chart.js canvas elements containing custom zero-data overlays.
* **Secure credentials check:** Replaced simple password verification with hashed password check using bcrypt.
