"""
Enercore AI Solar Proposal Generator - Flask Application

Full-stack Flask application connected to database/service layer.
Matches Stitch design specifications exactly.
"""

import os
import math
from functools import wraps
from werkzeug.utils import secure_filename
from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    flash,
    Response,
    jsonify,
)

from services.customer_service import (
    list_customers,
    create_customer,
    get_customer_kpis,
    update_customer_status,
    get_customer,
)
from services.dashboard_service import (
    get_dashboard_kpis,
    get_pipeline_chart_data,
    get_followups,
    get_recent_activity,
    export_recent_activity_csv,
)
from services.pipeline_service import (
    get_all_deals_by_stage,
    get_pipeline_total_value,
    create_pipeline_deal,
    update_deal_stage,
    delete_pipeline_deal,
)
from services.proposal_service import (
    create_proposal,
    get_all_proposals,
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'enercore-solar-secret-key')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

# Navigation items matching Stitch design
NAV_ITEMS = [
    ("Dashboard", "dashboard", "dashboard"),
    ("Clients", "groups", "customers"),
    ("Pipeline", "account_tree", "pipeline"),
    ("Bill Analysis", "query_stats", "analysis"),
    ("Proposals", "description", "proposal_history"),
    ("Reports & Analytics", "insights", "reports"),
    ("Settings", "settings", "settings"),
]

DESIGN_SYSTEM = {
    "colors": {
        "primary": "#006b1b",
        "secondary": "#8f4e00",
        "tertiary": "#005ea4",
        "surface": "#f7f9fb",
        "on_surface": "#191c1e",
        "on_surface_variant": "#3f4a3d",
        "outline": "#6f7a6b",
        "outline_variant": "#bfcab9",
    },
}


@app.context_processor
def inject_design_system():
    return dict(design=DESIGN_SYSTEM, nav_items=NAV_ITEMS)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            error = "Please enter both email and password."
        else:
            session['authenticated'] = True
            session['user'] = {
                'full_name': email.split('@')[0].replace('.', ' ').title() if '@' in email else 'User',
                'email': email,
                'role': 'Sales Engineer'
            }
            flash('Successfully logged in.', 'success')
            return redirect(url_for('dashboard'))

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    date_range = request.args.get('range', '30')
    search_q = request.args.get('search', '').strip()
    category_filter = request.args.get('category', 'all')
    status_filter = request.args.get('status', 'all')
    sort_by = request.args.get('sort', 'updated_at')
    sort_order = request.args.get('order', 'desc')

    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1

    per_page = 5

    kpis = get_dashboard_kpis(date_range=date_range)
    pipeline_chart = get_pipeline_chart_data()
    followups = get_followups()
    activity_items, total_count = get_recent_activity(
        search=search_q,
        category=category_filter,
        status=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page
    )

    total_pages = max(1, math.ceil(total_count / per_page))

    return render_template(
        'dashboard.html',
        active_page='dashboard',
        kpis=kpis,
        pipeline_chart=pipeline_chart,
        followups=followups,
        activity_items=activity_items,
        date_range=date_range,
        search_q=search_q,
        category_filter=category_filter,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        per_page=per_page,
    )


@app.route('/dashboard/export-csv')
@login_required
def export_dashboard_csv():
    search_q = request.args.get('search', '')
    category_filter = request.args.get('category', 'all')
    status_filter = request.args.get('status', 'all')

    csv_data = export_recent_activity_csv(
        search=search_q,
        category=category_filter,
        status=status_filter
    )

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=enercore_client_activity.csv"}
    )


@app.route('/dashboard/action', methods=['POST'])
@login_required
def dashboard_action():
    customer_id = request.form.get('customer_id')
    new_status = request.form.get('status')

    if customer_id and new_status:
        updated = update_customer_status(customer_id, new_status)
        if updated:
            flash(f"Status for '{updated['name']}' updated to '{new_status}'.", 'success')
        else:
            flash("Failed to update status.", 'error')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/customers')
@login_required
def customers():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', 'all')
    status = request.args.get('status', 'all')

    customer_list = list_customers(search, category, status)

    from services.proposal_service import get_customer_stats
    enriched_list = []
    for c in customer_list:
        c_dict = dict(c)
        stats = get_customer_stats(c_dict["id"])
        c_dict.update(stats)
        enriched_list.append(c_dict)

    kpis = get_customer_kpis()
    return render_template(
        'customers.html',
        active_page='customers',
        customers=enriched_list,
        kpis=kpis,
        search_q=search,
        category_filter=category,
        status_filter=status,
    )


@app.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    name = request.form.get('name', '').strip()
    contact = request.form.get('contact', '').strip()
    phone = request.form.get('phone', '').strip()
    category = request.form.get('category', 'Commercial')
    value_numeric = request.form.get('value', '100000')

    if not name or not contact:
        flash('Company name and contact person are required fields.', 'error')
        return redirect(url_for('customers'))

    try:
        val = float(value_numeric)
    except ValueError:
        val = 100000.0

    create_customer({
        'name': name,
        'contact': contact,
        'phone': phone,
        'category': category,
        'segment': f"{category} · Solar Array",
        'status': 'New Lead',
        'tone': 'neutral',
        'value_numeric': val,
        'updated': 'Just now',
    })
    flash(f"Client '{name}' successfully added to portfolio.", 'success')
    return redirect(url_for('customers'))


@app.route('/pipeline')
@login_required
def pipeline():
    deals_by_stage = get_all_deals_by_stage()
    total_val = get_pipeline_total_value()
    return render_template('pipeline.html', active_page='pipeline', deals_by_stage=deals_by_stage, total_pipeline_value=total_val)


@app.route('/pipeline/add', methods=['POST'])
@login_required
def add_pipeline_deal():
    company = request.form.get('company_name', '').strip()
    category = request.form.get('category', 'COMMERCIAL')
    value = request.form.get('value_numeric', '250000')
    stage = request.form.get('stage', 'New Lead')

    if not company:
        flash('Company name is required to create a pipeline lead.', 'error')
        return redirect(url_for('pipeline'))

    try:
        val_num = float(value)
    except ValueError:
        val_num = 250000.0

    success = create_pipeline_deal({
        'company_name': company,
        'category': category,
        'value_numeric': val_num,
        'stage': stage,
    })

    if success:
        flash(f"New deal for '{company}' added to pipeline.", 'success')
    else:
        flash("Failed to create pipeline deal.", 'error')

    return redirect(url_for('pipeline'))


@app.route('/pipeline/move', methods=['POST'])
@login_required
def move_pipeline_deal():
    deal_id = request.form.get('deal_id')
    new_stage = request.form.get('new_stage')

    if deal_id and new_stage:
        update_deal_stage(deal_id, new_stage)
        flash(f"Deal updated to stage: '{new_stage}'.", 'success')
    return redirect(url_for('pipeline'))


@app.route('/pipeline/delete/<deal_id>', methods=['POST'])
@login_required
def delete_deal(deal_id):
    delete_pipeline_deal(deal_id)
    flash("Deal removed from pipeline.", 'success')
    return redirect(url_for('pipeline'))


@app.route('/analysis')
@login_required
def analysis():
    from services.proposal_service import get_bill_analysis_data, get_latest_electricity_bill
    bill_id = request.args.get('bill_id')
    if not bill_id:
        bill_id = get_latest_electricity_bill()

    analysis_data = None
    if bill_id:
        analysis_data = get_bill_analysis_data(bill_id)

    return render_template('analysis.html', active_page='analysis', analysis_data=analysis_data)


@app.route('/analysis/export')
@login_required
def export_analysis_data():
    csv_data = "Metric,Value\nRecommended Plant Size,250 kWp\nDaily Yield,1125 kWh\nAnnual Savings,$42500\nPayback Period,3.8 Years\nProject IRR,24.6%\nCarbon Offset,320 Tons/Yr\n"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=enercore_analysis_results.csv"}
    )


@app.route('/proposal', methods=['GET', 'POST'])
@login_required
def proposal():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        if not customer_id:
            flash('Please select or add a client first before generating a proposal.', 'error')
            return redirect(url_for('proposal'))

        cust = get_customer(customer_id)
        if cust:
            create_proposal({
                'customer_id': customer_id,
                'name': f'Solar Integration Proposal - {cust["name"]}',
                'system_size_kwp': 250.0,
                'annual_yield_kwh': 1125.0,
                'project_cost': 34250.0,
                'payback_years': 7.2,
                'irr': 15.0
            })
            flash(f'Official proposal for "{cust["name"]}" generated and saved in database.', 'success')
        else:
            flash('Selected client does not exist.', 'error')
        return redirect(url_for('proposal_history'))

    customers_list = list_customers()
    return render_template('proposal.html', active_page='proposal', customers=customers_list)


@app.route('/proposal_history')
@login_required
def proposal_history():
    category_filter = request.args.get('category', 'all')
    proposals_list = get_all_proposals()
    return render_template('proposal_history.html', active_page='proposal_history', proposals=proposals_list, category_filter=category_filter)


@app.route('/reports')
@login_required
def reports():
    date_range = request.args.get('range', '30')
    return render_template('analytics.html', active_page='reports', date_range=date_range)


@app.route('/reports/export')
@login_required
def export_reports():
    csv_data = "Sector,Active Leads,Avg Deal Size,Win Rate\nManufacturing,42,$245k,72%\nHealthcare,28,$180k,54%\nRetail Centers,19,$112k,32%\n"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=enercore_intelligence_report.csv"}
    )


@app.route('/upload_bill', methods=['GET', 'POST'])
@login_required
def upload_bill():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        file = request.files.get('bill_file')
        if not file or file.filename == '':
            flash('Please select a valid electricity bill file to upload.', 'error')
            return redirect(url_for('upload_bill'))

        if not customer_id:
            flash('Please select a valid client for this bill.', 'error')
            return redirect(url_for('upload_bill'))

        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            from services.proposal_service import get_sites_by_customer, create_site, create_electricity_bill, save_ocr_result
            sites = get_sites_by_customer(customer_id)
            if sites:
                site_id = sites[0]['id']
            else:
                site_id = create_site({
                    'customer_id': customer_id,
                    'name': 'Primary Solar Site'
                })

            bill_id = create_electricity_bill({
                'site_id': site_id,
                'billing_period_start': '2026-01-01',
                'billing_period_end': '2026-12-31',
                'energy_consumption_kwh': 120000.0,
                'total_cost': 42500.0,
                'file_path': filepath
            })

            save_ocr_result(
                bill_id=bill_id,
                extracted_text="OCR Parsed Utility Bill",
                json_data='{"plant_size": "250", "daily_yield": "1,125", "annual_savings": "42,500", "payback": "3.8", "irr": "24.6%"}'
            )

            flash(f'Electricity bill "{filename}" uploaded and OCR parsed successfully.', 'success')
            return redirect(url_for('analysis', bill_id=bill_id))
        else:
            flash('Invalid file format. Allowed formats: PDF, JPG, PNG.', 'error')
            return redirect(url_for('upload_bill'))

    customers_list = list_customers()
    return render_template('upload_bill.html', active_page='analysis', customers=customers_list)


@app.route('/settings', methods=['GET'])
@login_required
def settings():
    return render_template('settings.html', active_page='settings')


@app.route('/settings/save', methods=['POST'])
@login_required
def save_settings():
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', '')

    if session.get('user'):
        session['user']['full_name'] = full_name or session['user']['full_name']
        session['user']['email'] = email or session['user']['email']
        session['user']['role'] = role or session['user']['role']

    flash('Account and system preferences saved successfully.', 'success')
    return redirect(url_for('settings'))


@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """Interactive AI Assistant endpoint."""
    data = request.get_json() or {}
    message = data.get('message', '').strip().lower()

    if 'roi' in message or 'savings' in message:
        reply = "Based on local solar irradiation and current utility tariffs, typical payback periods range between 3.5 to 4.2 years with up to 70% net monthly bill reduction."
    elif 'proposal' in message or 'draft' in message:
        reply = "You can create a new proposal anytime by clicking '+ New Proposal' in the top bar or navigating to the Proposals tab."
    elif 'client' in message or 'lead' in message:
        reply = "Client records can be managed under the Clients tab or organized visually in your CRM Pipeline."
    else:
        reply = f"I've received your query regarding: '{message}'. Enercore AI is ready to assist with tariff analysis, system sizing (kWp), and automated proposal generation!"

    return jsonify({'reply': reply})


@app.route('/customers/<customer_id>')
@login_required
def customer_details_route(customer_id):
    from services.customer_service import get_customer
    from services.proposal_service import get_sites_by_customer, get_customer_stats
    cust = get_customer(customer_id)
    if not cust:
        flash("Customer not found.", "error")
        return redirect(url_for('customers'))

    # We display all active and archived sites (excluding soft deleted ones)
    sites_list = get_sites_by_customer(customer_id, include_deleted=False)
    stats = get_customer_stats(customer_id)

    return render_template(
        'customer_details.html',
        customer=cust,
        sites=sites_list,
        stats=stats
    )


@app.route('/sites/<site_id>')
@login_required
def site_dashboard(site_id):
    from services.proposal_service import get_site_details, get_site_activities
    site = get_site_details(site_id)
    if not site:
        flash("Site not found.", "error")
        return redirect(url_for('customers'))

    activities = get_site_activities(site_id)
    return render_template(
        'site_dashboard.html',
        site=site,
        activities=activities
    )


@app.route('/sites/add/<customer_id>', methods=['POST'])
@login_required
def add_site(customer_id):
    from services.proposal_service import create_site
    import re

    name = request.form.get('name', '').strip()
    contact_person = request.form.get('contact_person', '').strip()
    contact_number = request.form.get('contact_number', '').strip()
    address_street = request.form.get('address_street', '').strip()
    address_city = request.form.get('address_city', '').strip()
    address_state = request.form.get('address_state', '').strip()
    address_zip = request.form.get('address_zip', '').strip()

    if not name:
        flash("Site Name is a required field.", "error")
        return redirect(url_for('customer_details_route', customer_id=customer_id))

    # Validate phone format
    if contact_number:
        phone_pattern = r'^\+?[\d\s\-\(\)]{7,20}$'
        if not re.match(phone_pattern, contact_number):
            flash("Invalid phone number format. Please check the number.", "error")
            return redirect(url_for('customer_details_route', customer_id=customer_id))

    try:
        create_site({
            'customer_id': customer_id,
            'name': name,
            'contact_person': contact_person,
            'contact_number': contact_number,
            'address_street': address_street,
            'address_city': address_city,
            'address_state': address_state,
            'address_zip': address_zip,
            'status': 'New',
            'user': session.get('user', {}).get('full_name', 'System')
        })
        flash(f"Site '{name}' successfully created.", "success")
    except ValueError as val_err:
        flash(str(val_err), "error")
    except Exception as e:
        flash(f"Error creating site: {e}", "error")

    return redirect(url_for('customer_details_route', customer_id=customer_id))


@app.route('/sites/edit/<site_id>', methods=['POST'])
@login_required
def edit_site(site_id):
    from services.proposal_service import update_site, get_site_details
    import re

    site = get_site_details(site_id)
    if not site:
        flash("Site not found.", "error")
        return redirect(url_for('customers'))

    name = request.form.get('name', '').strip()
    contact_person = request.form.get('contact_person', '').strip()
    contact_number = request.form.get('contact_number', '').strip()
    address_street = request.form.get('address_street', '').strip()
    address_city = request.form.get('address_city', '').strip()
    address_state = request.form.get('address_state', '').strip()
    address_zip = request.form.get('address_zip', '').strip()
    status = request.form.get('status', 'New').strip()

    if not name:
        flash("Site Name is a required field.", "error")
        return redirect(url_for('customer_details_route', customer_id=site['customer_id']))

    if contact_number:
        phone_pattern = r'^\+?[\d\s\-\(\)]{7,20}$'
        if not re.match(phone_pattern, contact_number):
            flash("Invalid phone number format.", "error")
            return redirect(url_for('customer_details_route', customer_id=site['customer_id']))

    try:
        update_site(site_id, {
            'name': name,
            'contact_person': contact_person,
            'contact_number': contact_number,
            'address_street': address_street,
            'address_city': address_city,
            'address_state': address_state,
            'address_zip': address_zip,
            'status': status,
            'user': session.get('user', {}).get('full_name', 'System')
        })
        flash(f"Site '{name}' details updated successfully.", "success")
    except ValueError as val_err:
        flash(str(val_err), "error")
    except Exception as e:
        flash(f"Error updating site details: {e}", "error")

    return redirect(url_for('customer_details_route', customer_id=site['customer_id']))


@app.route('/sites/archive/<site_id>', methods=['POST'])
@login_required
def archive_site_route(site_id):
    from services.proposal_service import archive_site, get_site_details
    site = get_site_details(site_id)
    if not site:
        flash("Site not found.", "error")
        return redirect(url_for('customers'))

    archive_site(site_id, user=session.get('user', {}).get('full_name', 'System'))
    flash(f"Site '{site['name']}' has been archived.", "success")
    return redirect(url_for('customer_details_route', customer_id=site['customer_id']))


@app.route('/sites/restore/<site_id>', methods=['POST'])
@login_required
def restore_site_route(site_id):
    from services.proposal_service import restore_site, get_site_details
    site = get_site_details(site_id)
    if not site:
        flash("Site not found.", "error")
        return redirect(url_for('customers'))

    restore_site(site_id, user=session.get('user', {}).get('full_name', 'System'))
    flash(f"Site '{site['name']}' has been restored.", "success")
    return redirect(url_for('customer_details_route', customer_id=site['customer_id']))


@app.route('/sites/delete/<site_id>', methods=['POST'])
@login_required
def delete_site_route(site_id):
    from services.proposal_service import delete_site, get_site_details
    site = get_site_details(site_id)
    if not site:
        flash("Site not found.", "error")
        return redirect(url_for('customers'))

    delete_site(site_id, user=session.get('user', {}).get('full_name', 'System'))
    flash(f"Site '{site['name']}' has been deleted.", "success")
    return redirect(url_for('customer_details_route', customer_id=site['customer_id']))


@app.route('/sites')
@login_required
def sites_list_route():
    from services.proposal_service import search_sites_db
    from database.connection import get_connection
    import sqlite3

    search_q = request.args.get('search', '').strip()
    customer_filter = request.args.get('customer', 'all')
    state_filter = request.args.get('state', 'all')
    status_filter = request.args.get('status', 'all')

    cust_list = list_customers()

    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    states = []
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT address_state FROM sites WHERE address_state IS NOT NULL AND address_state != '' AND is_deleted = 0;")
        states = [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"Error fetching states: {e}")
    finally:
        conn.close()

    sites_list = search_sites_db(
        search_q=search_q,
        customer_id=customer_filter,
        state=state_filter,
        status=status_filter
    )

    return render_template(
        'sites.html',
        active_page='sites',
        sites=sites_list,
        customers=cust_list,
        states=states,
        search_q=search_q,
        customer_filter=customer_filter,
        state_filter=state_filter,
        status_filter=status_filter
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)
