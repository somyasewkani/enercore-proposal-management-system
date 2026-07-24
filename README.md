# Enercore AI Solar Proposal Generator

An AI-powered web portal that automates electricity bill analysis, solar sizing, ROI calculation, and professional proposal generation for sales executives.

Developed as a PS-2 Internship Project.

## 🚀 Quick Start

### Streamlit Version (Primary Interface)
```bash
streamlit run app.py
```
Default credentials: `admin@enercore.ai` / `Enercore@123`

### Flask Version (Jinja2 Templates)
```bash
python app_flask.py
```
Then open: http://localhost:5000

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Streamlit     │     │     Flask       │
│    (Python)     │     │    (Jinja2)     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │    Templates          │
         │   base.html           │
         │   login.html          │
         │   dashboard.html      │
         │   customers.html      │
         │   pipeline.html       │
         │   analysis.html       │
         │   analytics.html      │
         │   proposal.html       │
         │   proposal_history.html│
         │   upload_bill.html    │
         │   settings.html       │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │  UIUX Design Source   │
         │stitch_enercore_...    │
         └───────────────────────┘
```

## 📱 Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Login | Glassmorphism authentication screen |
| `/dashboard` | Dashboard | KPI overview, pipeline charts, recent activity |
| `/customers` | Clients | Client directory with filters and search |
| `/pipeline` | CRM Pipeline | Kanban-style deal tracker |
| `/analysis` | Solar Analysis | ROI calculator and performance projections |
| `/upload_bill` | Bill Upload | File upload with OCR extraction |
| `/proposal` | New Proposal | 3-step proposal wizard |
| `/proposal_history` | History | Past proposals list with filters |
| `/reports` | Analytics | Performance metrics and charts |
| `/settings` | Settings | Profile, team, integrations |

## 🎨 Design System

Based on `stitch_enercore_solar_business_portal/enercore_solar_business_portal/DESIGN.md`:

### Colors
- **Primary Green:** `#006b1b` - Primary actions, success
- **Secondary Orange:** `#8f4e00` - Warnings, highlights  
- **UI Blue:** `#005ea4` - Interactive elements
- **Surface:** `#f7f9fb` - Background
- **On Surface:** `#191c1e` - Text

### Components
- Glassmorphism cards with `backdrop-filter: blur(20px)`
- Material Symbols icons
- Inter font family
- 8px base spacing, 24px gutters
- 1440px max container width

## 🔧 Tech Stack

- **Framework:** Streamlit + Flask
- **Styling:** Tailwind CSS
- **Charts:** Plotly, Chart.js
- **Icons:** Material Symbols Outlined
- **Fonts:** Inter

## 📂 Project Structure

```
enercore-ai-portal/
├── app.py                  # Streamlit main application
├── app_flask.py            # Flask application
├── components/
│   ├── sidebar.py          # Navigation sidebar
│   ├── topnav.py           # Top navigation bar
│   ├── chatbot.py          # AI assistant component
│   └── cards.py            # Reusable UI cards
├── pages/
│   ├── login.py            # Login screen
│   ├── dashboard.py        # Dashboard page
│   ├── customers.py        # Client management
│   ├── pipeline.py         # CRM pipeline
│   ├── proposal.py         # Proposal wizard
│   ├── proposal_history.py # History page
│   ├── reports.py          # Analytics
│   ├── analysis.py         # Solar analysis
│   └── settings.py         # User settings
├── templates/              # Jinja2 templates
│   ├── base.html           # Base template with sidebar
│   ├── login.html          # Login page
│   ├── dashboard.html      # Dashboard
│   ├── customers.html      # Client management
│   ├── pipeline.html       # Kanban board
│   ├── proposal.html       # Proposal editor
│   ├── analysis.html       # ROI calculator
│   ├── analytics.html      # Analytics dashboard
│   ├── proposal_history.html # History table
│   ├── upload_bill.html    # Bill upload
│   └── settings.html       # Settings page
└── stitch_enercore_solar_business_portal/
    └── Original UIUX designs
```

## 📋 Frontend Checklist

See `FRONTEND_CHECKLIST.md` for detailed completion status.

## 🚧 Next Steps

- Connect to database layer (`database/connection.py`)
- Implement real authentication (`services/auth_service.py`)
- Add proposal generation service (`services/proposal_service.py`)
- Enable file upload processing
- Connect AI chatbot to real backend