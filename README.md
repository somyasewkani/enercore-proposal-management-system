# Enercore AI Solar Proposal & Project Management Portal
**Version 1.0 Release**

An enterprise-grade, Clean Architecture web application that automates utility bill parsing via Gemini OCR, recommended solar photovoltaic system sizing, ROI calculations, professional client PDF compilation, and downstream project execution lifecycle tracking.

---

## 🏗️ Architecture & Technical Stack

The application is built using a **Clean Architecture** model, dividing components into isolated layers:

```
┌─────────────────────────────────────────────────────────┐
│                     Presentation Layer                  │
│  Flask Controllers (app_flask.py) & Jinja2 Templates    │
└────────────────────────────┬────────────────────────────┘
                             │ (Services APIs)
┌────────────────────────────▼────────────────────────────┐
│                       Service Layer                     │
│  ocr_service.py     calculation_service.py              │
│  proposal_generator.py     pdf_generator.py             │
│  project_service.py        customer_service.py          │
└────────────────────────────┬────────────────────────────┘
                             │ (Database Adapter API)
┌────────────────────────────▼────────────────────────────┐
│                    Infrastructure Layer                 │
│         database/connection.py (SQLite / PostgreSQL)     │
└─────────────────────────────────────────────────────────┘
```

* **Core Backend:** Python 3.11+, Flask.
* **Database Adapter:** Unified sqlite3 and psycopg2 connector wrapper featuring auto-seeding and idempotent columns migration script.
* **OCR Provider:** Google Gemini Pro Multimodal API.
* **PDF Compiler:** ReportLab-based `xhtml2pdf` engine styling HTML templates.
* **UI/UX System:** Material-inspired CSS styling, custom glassmorphism overlays, dynamic CSS grids, Chart.js for data visualization, and Google Material Symbols.

---

## 📂 Project Directory Structure

```
enercore-ai-portal/
├── app_flask.py            # Main Flask Routing & Application entry point
├── requirements.txt        # Python dependency manifest
├── .gitignore              # Standard git exclusions list
├── .env.example            # Environment variables template
├── database/
│   └── connection.py       # DB connection pool, schemas, and seeds
├── services/
│   ├── auth_service.py     # Hashed credential validation layer
│   ├── customer_service.py # Client CRUD, soft deletes, and format validation
│   ├── pipeline_service.py # CRM Kanban pipeline tracking
│   ├── calculation_service.py # Solar sizing, payback, and emission offsets
│   ├── ocr_service.py      # Gemini OCR parsing andCaparo fallback
│   ├── proposal_generator.py # Sequence formatting & multi-version controls
│   ├── pdf_generator.py    # HTML compiling and PDF file storage writing
│   └── project_service.py  # Converted project timeline & dashboard KPIs
├── templates/              # HTML templates
│   ├── base.html           # Main master layout
│   ├── customers.html      # Clients list with registration forms
│   ├── customer_details.html # Dashboard sidebar, site grids & profile edits
│   ├── analytics.html      # Dynamic Chart.js reports with zero data states
│   └── pdf/                # PDF HTML templates
├── uploads/                # Local document uploads directories (git-ignored)
│   ├── bills/              # Electricity bills (PDF)
│   ├── proposals/          # Compiled client proposal PDFs
│   └── projects/           # Project DWG drawings, BOMs, and contracts
└── test_complete_qa.py    # Complete E2E regression check script
```

---

## 🗄️ Database Schemas (SQLite & PostgreSQL)

The database maps six primary business tables:

### 1. `customers` Table
Holds the corporate client account metrics:
```sql
CREATE TABLE customers (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    segment VARCHAR(255),
    contact VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    address TEXT,
    gstin VARCHAR(100),
    status VARCHAR(100) NOT NULL,
    tone VARCHAR(50) DEFAULT 'neutral',
    value_numeric NUMERIC DEFAULT 0,
    capacity_mw NUMERIC DEFAULT 0,
    is_deleted INTEGER DEFAULT 0,
    updated_at VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. `sites` Table
Maps project locations under clients:
```sql
CREATE TABLE sites (
    id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    address_street VARCHAR(255),
    address_city VARCHAR(255),
    address_state VARCHAR(255),
    address_zip VARCHAR(50),
    contact_person VARCHAR(255),
    contact_number VARCHAR(50),
    status VARCHAR(100) DEFAULT 'New',
    is_archived INTEGER DEFAULT 0,
    is_deleted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. `electricity_bills` Table
Maps utility billing statement metadata and file paths:
```sql
CREATE TABLE electricity_bills (
    id VARCHAR(50) PRIMARY KEY,
    site_id VARCHAR(50) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    billing_month INTEGER NOT NULL,
    billing_year INTEGER NOT NULL,
    billing_period_start VARCHAR(100),
    billing_period_end VARCHAR(100),
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    original_filename VARCHAR(255),
    stored_filename VARCHAR(255),
    file_path TEXT,
    file_type VARCHAR(50),
    file_size INTEGER,
    bill_status VARCHAR(100) DEFAULT 'Uploaded',
    ocr_status VARCHAR(100) DEFAULT 'Not Started'
);
```

### 4. `calculation_results` Table
Holds recommended sizing dimensions and offsets:
```sql
CREATE TABLE calculation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id VARCHAR(50) NOT NULL REFERENCES electricity_bills(id) ON DELETE CASCADE,
    plant_size_kw NUMERIC,
    recommended_inverter_kw NUMERIC,
    estimated_monthly_generation NUMERIC,
    estimated_annual_generation NUMERIC,
    monthly_savings NUMERIC,
    annual_savings NUMERIC,
    system_cost NUMERIC,
    payback_years NUMERIC,
    co2_offset NUMERIC,
    trees_equivalent NUMERIC,
    calculation_version VARCHAR(50) DEFAULT '1.0',
    calculation_status VARCHAR(50) DEFAULT 'Success',
    warnings TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5. `proposals` Table
Manages sequencing, status levels, and multi-version tracking:
```sql
CREATE TABLE proposals (
    id VARCHAR(50) PRIMARY KEY,
    proposal_number VARCHAR(100) NOT NULL,
    customer_id VARCHAR(50) REFERENCES customers(id) ON DELETE CASCADE,
    site_id VARCHAR(50) REFERENCES sites(id) ON DELETE SET NULL,
    bill_id VARCHAR(50) REFERENCES electricity_bills(id) ON DELETE SET NULL,
    calculation_id INTEGER REFERENCES calculation_results(id) ON DELETE SET NULL,
    proposal_name VARCHAR(255),
    version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'Draft',
    plant_size_kw NUMERIC,
    recommended_inverter_kw NUMERIC,
    annual_generation NUMERIC,
    annual_savings NUMERIC,
    system_cost NUMERIC,
    payback_years NUMERIC,
    prepared_by VARCHAR(255),
    prepared_date VARCHAR(100),
    remarks TEXT,
    is_active INTEGER DEFAULT 1,
    pdf_filename VARCHAR(255),
    pdf_path TEXT,
    pdf_generated_at TIMESTAMP,
    pdf_generated_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6. `projects` Table
Holds the primary execution data:
```sql
CREATE TABLE projects (
    id VARCHAR(50) PRIMARY KEY,
    project_number VARCHAR(100) NOT NULL UNIQUE,
    proposal_id VARCHAR(50) NOT NULL REFERENCES proposals(id) ON DELETE RESTRICT,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    site_id VARCHAR(50) REFERENCES sites(id) ON DELETE SET NULL,
    project_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'Planning',
    execution_model VARCHAR(50) DEFAULT 'EPC',
    capacity_kw NUMERIC DEFAULT 0,
    contract_value NUMERIC DEFAULT 0,
    project_manager VARCHAR(255),
    start_date VARCHAR(100),
    expected_completion VARCHAR(100),
    actual_completion VARCHAR(100),
    progress_percentage NUMERIC DEFAULT 0,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔧 Installation & Deployment Steps

1. **Clone & Set Up Environment:**
   ```bash
   git clone <repository_url>
   cd enercore-ai-portal
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Credentials:**
   Copy `.env.example` to `.env` and populate variables:
   ```bash
   cp .env.example .env
   ```
   Specify your actual `GEMINI_API_KEY` for OCR processing.

3. **Initialize Database:**
   ```bash
   python -c "from database.connection import init_db; init_db(seed_demo=True)"
   ```

4. **Start local Server:**
   ```bash
   python app_flask.py
   ```
   The portal is served locally at: http://localhost:5000  
   *Default Admin login:* `admin@enercore.com` / `admin123`

---

## 📈 Standard User Workflows

```
Login 
  → Create Client Lead 
  → Edit Client Profile & GSTIN 
  → Add Project Site location 
  → Upload Utility Bill (PDF)
  → Execute Gemini OCR Extraction 
  → Review Capped Sizing & Offsets 
  → Generate Proposal V1 
  → Compile Cover Page PDF 
  → Approve Proposal 
  → Convert to Project 
  → Upload Engineering Drawings 
  → Update Timelines & Complete Project
  → View Dynamic Reports Dashboard
```

---

## 🧪 Testing Strategy

Execute regression checks in the virtual environment:
```bash
# 1. Run Client Profile & Validation tests
python test_priority_fixes.py

# 2. Run E2E pipeline regression tests on the Caparo Maruti bill
python test_complete_qa.py
```

---

## 📋 Release Summary (Version 1.0)

### Changelog:
* **Database:** Idempotent SQLite/Postgres database migrations added.
* **Validation:** Backend strict pattern validators (Regex checks for email, phone, GSTIN format validations, and duplicate email checks) implemented.
* **Safety Rules:** Customer deletion refactored to soft-delete archive, preventing hard deletions if active site/bill/proposal/project dependencies exist.
* **Analytics:** Replaced static charts with dynamic Chart.js configurations querying SQL aggregates, with custom zero-data overlays.
* **UI/UX:** Added two-column details layout with Client Profile sidebars and responsive modal edit forms.

### Known Limitations:
* **Internet Connection:** Gemini OCR services require active connections to the Google Generative AI servers. If offline, the Caparo Maruti statement fallback parser executes automatically.
* **Discom Support:** Sizing ROI relies on flat tariff schedules. Future upgrades will support time-of-day (TOD) slots.