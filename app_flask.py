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
            from services.auth_service import login_user
            user_data = login_user(email, password)
            if user_data:
                session['authenticated'] = True
                session['user'] = user_data
                flash('Successfully logged in.', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = "Invalid email or password."

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

    from services.project_service import get_project_dashboard_kpis
    project_kpis = get_project_dashboard_kpis()

    return render_template(
        'dashboard.html',
        active_page='dashboard',
        kpis=kpis,
        project_kpis=project_kpis,
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
    email = request.form.get('email', '').strip()
    address = request.form.get('address', '').strip()
    gstin = request.form.get('gstin', '').strip()
    category = request.form.get('category', 'Commercial')
    value_numeric = request.form.get('value', '0')

    try:
        val = float(value_numeric) if value_numeric else 0.0
    except ValueError:
        val = 0.0

    try:
        create_customer({
            'name': name,
            'contact': contact,
            'phone': phone,
            'email': email,
            'address': address,
            'gstin': gstin,
            'category': category,
            'value_numeric': val,
            'capacity_mw': 0.5,
            'updated': 'Just now',
        })
        flash(f"Client '{name}' successfully added to portfolio.", 'success')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('customers'))


@app.route('/customers/<customer_id>/update', methods=['POST'])
@login_required
def update_customer_route(customer_id):
    name = request.form.get('name', '').strip()
    contact = request.form.get('contact', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    address = request.form.get('address', '').strip()
    gstin = request.form.get('gstin', '').strip()
    category = request.form.get('category', 'Commercial')
    value_numeric = request.form.get('value', '0')
    capacity_mw = request.form.get('capacity_mw', '0.5')

    try:
        val = float(value_numeric) if value_numeric else 0.0
    except ValueError:
        val = 0.0

    try:
        cap_mw = float(capacity_mw) if capacity_mw else 0.5
    except ValueError:
        cap_mw = 0.5

    try:
        update_customer_profile(customer_id, {
            'name': name,
            'contact': contact,
            'phone': phone,
            'email': email,
            'address': address,
            'gstin': gstin,
            'category': category,
            'value_numeric': val,
            'capacity_mw': cap_mw
        })
        flash('Client profile details updated successfully.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
        
    return redirect(url_for('customer_details_route', customer_id=customer_id))


@app.route('/customers/<customer_id>/archive', methods=['POST'])
@login_required
def archive_customer_route(customer_id):
    success, msg = delete_customer(customer_id, permanent=False)
    if success:
        flash(msg, 'success')
        return redirect(url_for('customers'))
    else:
        flash(msg, 'error')
        return redirect(url_for('customer_details_route', customer_id=customer_id))


@app.route('/customers/<customer_id>/delete', methods=['POST'])
@login_required
def delete_customer_route(customer_id):
    success, msg = delete_customer(customer_id, permanent=True)
    if success:
        flash(msg, 'success')
        return redirect(url_for('customers'))
    else:
        flash(msg, 'error')
        return redirect(url_for('customer_details_route', customer_id=customer_id))


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
    return redirect(url_for('proposals_list_route'))


@app.route('/reports')
@login_required
def reports():
    date_range = request.args.get('range', '30')
    from services.project_service import get_project_reports_stats
    project_stats = get_project_reports_stats()
    return render_template('analytics.html', active_page='reports', date_range=date_range, project_stats=project_stats)


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

        allowed_exts = {'pdf', 'png', 'jpg', 'jpeg'}
        orig_filename = file.filename
        ext = orig_filename.rsplit('.', 1)[-1].lower() if '.' in orig_filename else ''
        if ext not in allowed_exts:
            flash('Invalid file format. Allowed formats: PDF, JPG, PNG.', 'error')
            return redirect(url_for('upload_bill'))

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > 10 * 1024 * 1024:
            flash('File size exceeds the maximum limit of 10MB.', 'error')
            return redirect(url_for('upload_bill'))

        from services.proposal_service import get_sites_by_customer, create_site, create_electricity_bill, get_bills_by_site
        sites = get_sites_by_customer(customer_id)
        if sites:
            site_id = sites[0]['id']
        else:
            site_id = create_site({
                'customer_id': customer_id,
                'name': 'Primary Solar Site',
                'user': session.get('user', {}).get('full_name', 'System')
            })

        # Determine month and year dynamically to avoid duplicate collisions
        site_bills = get_bills_by_site(site_id)
        if site_bills:
            latest = site_bills[0]
            m = latest['billing_month']
            y = latest['billing_year']
            if m == 12:
                billing_month = 1
                billing_year = y + 1
            else:
                billing_month = m + 1
                billing_year = y
        else:
            import datetime
            now = datetime.datetime.now()
            billing_month = now.month
            billing_year = now.year

        # Store file in structured directory: uploads/bills/<site_id>/
        folder = os.path.join(app.root_path, 'uploads', 'bills', site_id)
        os.makedirs(folder, exist_ok=True)

        import uuid
        from werkzeug.utils import secure_filename
        safe_name = secure_filename(orig_filename)
        unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
        filepath = os.path.join('uploads', 'bills', site_id, unique_name)
        file.save(os.path.join(app.root_path, filepath))

        try:
            bill_id = create_electricity_bill({
                'site_id': site_id,
                'billing_month': billing_month,
                'billing_year': billing_year,
                'billing_period_start': '',
                'billing_period_end': '',
                'original_filename': orig_filename,
                'stored_filename': unique_name,
                'file_path': filepath,
                'file_type': ext.upper(),
                'file_size': file_size,
                'bill_status': 'Uploaded',
                'notes': 'Uploaded via main utility upload wizard.',
                'user': session.get('user', {}).get('full_name', 'System')
            })

            # Re-save demo OCR results for backward compatibility with analysis view
            from services.proposal_service import save_ocr_result
            save_ocr_result(
                bill_id=bill_id,
                extracted_text="OCR Parsed Utility Bill",
                json_data='{"plant_size": "250", "daily_yield": "1,125", "annual_savings": "42,500", "payback": "3.8", "irr": "24.6%"}'
            )

            flash(f'Electricity bill "{orig_filename}" uploaded successfully.', 'success')
            return redirect(url_for('analysis', bill_id=bill_id))
        except Exception as e:
            flash(f"Error saving statement: {e}", "error")
            return redirect(url_for('upload_bill'))

    customers_list = list_customers()
    return render_template('upload_bill.html', active_page='analysis', customers=customers_list)


@app.route('/settings', methods=['GET'])
@login_required
def settings():
    from services.proposal_service import get_system_settings
    settings_dict = get_system_settings()
    return render_template('settings.html', active_page='settings', settings=settings_dict)


@app.route('/settings/save', methods=['POST'])
@login_required
def save_settings():
    from services.proposal_service import save_system_settings
    
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', '')

    if session.get('user'):
        session['user']['full_name'] = full_name or session['user']['full_name']
        session['user']['email'] = email or session['user']['email']
        session['user']['role'] = role or session['user']['role']

    # Read and save solar assumptions
    solar_keys = [
        "peak_sun_hours", "performance_ratio", "inverter_efficiency", "system_loss",
        "electricity_tariff", "installation_cost_per_kw", "co2_conversion_factor",
        "tree_conversion_factor"
    ]
    solar_settings = {}
    for key in solar_keys:
        val = request.form.get(key)
        if val is not None:
            solar_settings[key] = val.strip()

    if solar_settings:
        save_system_settings(solar_settings)

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
    from services.proposal_service import get_site_details, get_site_activities, get_bills_by_site
    site = get_site_details(site_id)
    if not site:
        flash("Site not found.", "error")
        return redirect(url_for('customers'))

    activities = get_site_activities(site_id)
    bills = get_bills_by_site(site_id)
    return render_template(
        'site_dashboard.html',
        site=site,
        activities=activities,
        bills=bills
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


@app.route('/bills/upload', methods=['POST'])
@login_required
def upload_bill_route():
    from services.proposal_service import create_electricity_bill, get_site_details
    import uuid
    import os
    from werkzeug.utils import secure_filename

    site_id = request.form.get('site_id')
    billing_month = request.form.get('billing_month')
    billing_year = request.form.get('billing_year')
    period_start = request.form.get('billing_period_start', '').strip()
    period_end = request.form.get('billing_period_end', '').strip()
    notes = request.form.get('notes', '').strip()

    if not site_id or not billing_month or not billing_year:
        flash("Site, Billing Month, and Billing Year are required fields.", "error")
        return redirect(request.referrer or url_for('customers'))

    site = get_site_details(site_id)
    if not site:
        flash("Target site not found.", "error")
        return redirect(url_for('customers'))

    file = request.files.get('bill_file')
    if not file or file.filename == '':
        flash("Please select a valid electricity bill file to upload.", "error")
        return redirect(url_for('site_dashboard', site_id=site_id))

    # Validate file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 10 * 1024 * 1024:
        flash("File size exceeds the maximum limit of 10MB.", "error")
        return redirect(url_for('site_dashboard', site_id=site_id))

    allowed_exts = {'pdf', 'png', 'jpg', 'jpeg'}
    orig_filename = file.filename
    ext = orig_filename.rsplit('.', 1)[-1].lower() if '.' in orig_filename else ''
    if ext not in allowed_exts:
        flash("Invalid file format. Allowed formats: PDF, JPG, PNG.", "error")
        return redirect(url_for('site_dashboard', site_id=site_id))

    # Save structured: uploads/bills/<site_id>/
    folder = os.path.join(app.root_path, 'uploads', 'bills', site_id)
    os.makedirs(folder, exist_ok=True)

    safe_name = secure_filename(orig_filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    filepath = os.path.join('uploads', 'bills', site_id, unique_name)
    file.save(os.path.join(app.root_path, filepath))

    try:
        bill_id = create_electricity_bill({
            'site_id': site_id,
            'billing_month': int(billing_month),
            'billing_year': int(billing_year),
            'billing_period_start': period_start,
            'billing_period_end': period_end,
            'original_filename': orig_filename,
            'stored_filename': unique_name,
            'file_path': filepath,
            'file_type': ext.upper(),
            'file_size': file_size,
            'bill_status': 'Uploaded',
            'notes': notes,
            'user': session.get('user', {}).get('full_name', 'System')
        })

        # Save demo OCR results for compatibility with analysis view
        from services.proposal_service import save_ocr_result
        save_ocr_result(
            bill_id=bill_id,
            extracted_text="OCR Parsed Utility Bill",
            json_data='{"plant_size": "250", "daily_yield": "1,125", "annual_savings": "42,500", "payback": "3.8", "irr": "24.6%"}'
        )

        flash(f"Electricity bill '{orig_filename}' uploaded successfully.", "success")
    except ValueError as val_err:
        flash(str(val_err), "error")
    except Exception as e:
        flash(f"Error saving bill: {e}", "error")

    return redirect(url_for('site_dashboard', site_id=site_id))


@app.route('/uploads/bills/<site_id>/<filename>')
@login_required
def serve_bill_file(site_id, filename):
    import os
    if '..' in site_id or '..' in filename:
        return abort(400)
    
    folder = os.path.join(app.root_path, 'uploads', 'bills', site_id)
    return send_from_directory(folder, filename)


@app.route('/bills/<bill_id>')
@login_required
def site_bill_details(bill_id):
    from services.proposal_service import get_bill_details
    import json
    bill = get_bill_details(bill_id)
    if not bill:
        flash("Electricity bill not found.", "error")
        return redirect(url_for('customers'))
    
    ocr_data = None
    if bill.get('normalized_json'):
        try:
            ocr_data = json.loads(bill['normalized_json'])
        except Exception:
            pass

    ocr_warnings = None
    if bill.get('warnings'):
        try:
            ocr_warnings = json.loads(bill['warnings'])
        except Exception:
            ocr_warnings = [bill['warnings']]
            
    calc_warnings = None
    if bill.get('calc_warnings'):
        try:
            calc_warnings = json.loads(bill['calc_warnings'])
        except Exception:
            calc_warnings = [bill['calc_warnings']]
            
    from services.proposal_service import list_proposals
    existing_props = list_proposals(customer_f='all', status_f='all', search_q='', sort_order='newest')
    site_proposals = [p for p in existing_props if p['site_id'] == bill['site_id']]
    latest_proposal = site_proposals[0] if site_proposals else None
    
    return render_template(
        'bill_details.html',
        bill=bill,
        ocr_data=ocr_data,
        ocr_warnings=ocr_warnings,
        calc_warnings=calc_warnings,
        latest_proposal=latest_proposal
    )


@app.route('/bills/edit/<bill_id>', methods=['POST'])
@login_required
def edit_bill_route(bill_id):
    from services.proposal_service import update_electricity_bill, get_bill_details
    bill = get_bill_details(bill_id)
    if not bill:
        flash("Electricity bill not found.", "error")
        return redirect(url_for('customers'))

    billing_month = request.form.get('billing_month')
    billing_year = request.form.get('billing_year')
    period_start = request.form.get('billing_period_start', '').strip()
    period_end = request.form.get('billing_period_end', '').strip()
    status = request.form.get('bill_status', 'Uploaded').strip()
    notes = request.form.get('notes', '').strip()

    if not billing_month or not billing_year:
        flash("Billing Month and Year are required fields.", "error")
        return redirect(url_for('site_bill_details', bill_id=bill_id))

    try:
        update_electricity_bill(bill_id, {
            'billing_month': int(billing_month),
            'billing_year': int(billing_year),
            'billing_period_start': period_start,
            'billing_period_end': period_end,
            'bill_status': status,
            'notes': notes,
            'user': session.get('user', {}).get('full_name', 'System')
        })
        flash("Bill metadata updated successfully.", "success")
    except ValueError as val_err:
        flash(str(val_err), "error")
    except Exception as e:
        flash(f"Error updating bill details: {e}", "error")

    return redirect(url_for('site_bill_details', bill_id=bill_id))


@app.route('/bills/delete/<bill_id>', methods=['POST'])
@login_required
def delete_bill_route(bill_id):
    from services.proposal_service import delete_electricity_bill, get_bill_details
    bill = get_bill_details(bill_id)
    if not bill:
        flash("Electricity bill not found.", "error")
        return redirect(request.referrer or url_for('customers'))

    delete_electricity_bill(bill_id, user=session.get('user', {}).get('full_name', 'System'))
    flash("Electricity bill soft deleted successfully.", "success")
    return redirect(request.referrer or url_for('site_dashboard', site_id=bill['site_id']))


@app.route('/bills/restore/<bill_id>', methods=['POST'])
@login_required
def restore_bill_route(bill_id):
    from services.proposal_service import restore_electricity_bill, get_bill_details
    bill = get_bill_details(bill_id)
    if not bill:
        flash("Electricity bill not found.", "error")
        return redirect(request.referrer or url_for('customers'))

    try:
        restore_electricity_bill(bill_id, user=session.get('user', {}).get('full_name', 'System'))
        flash("Electricity bill restored successfully.", "success")
    except ValueError as val_err:
        flash(str(val_err), "error")
    except Exception as e:
        flash(f"Error restoring bill: {e}", "error")

    return redirect(request.referrer or url_for('site_dashboard', site_id=bill['site_id']))


@app.route('/bills')
@login_required
def bills_directory_route():
    from services.proposal_service import search_bills_db
    from database.connection import get_connection
    import sqlite3

    search_q = request.args.get('search', '').strip()
    customer_filter = request.args.get('customer', 'all')
    month_filter = request.args.get('month', 'all')
    year_filter = request.args.get('year', 'all')
    status_filter = request.args.get('status', 'all')

    cust_list = list_customers()

    bills_list = search_bills_db(
        search_q=search_q,
        customer_id=customer_filter,
        month=month_filter,
        year=year_filter,
        status=status_filter
    )

    return render_template(
        'bills.html',
        active_page='bills',
        bills=bills_list,
        customers=cust_list,
        search_q=search_q,
        customer_filter=customer_filter,
        month_filter=month_filter,
        year_filter=year_filter,
        status_filter=status_filter
    )


@app.route('/bills/<bill_id>/run-ocr', methods=['POST'])
@login_required
def run_ocr_endpoint(bill_id):
    from services.ocr_service import run_ocr_for_bill
    import os
    
    if not os.environ.get("GEMINI_API_KEY"):
        flash("Google Gemini API Key is not configured in the environment. Please set GEMINI_API_KEY.", "error")
        return redirect(url_for('site_bill_details', bill_id=bill_id))

    actor = session.get('user', {}).get('full_name', 'System')
    try:
        success, warnings = run_ocr_for_bill(bill_id, actor=actor)
        if success:
            if warnings:
                msg = f"OCR completed with warnings: {', '.join(warnings)}"
                flash(msg, "warning")
            else:
                flash("AI OCR extraction completed successfully! Data stored in database.", "success")
        else:
            err_msg = warnings[0] if warnings else "Unknown execution error."
            flash(f"OCR Extraction failed: {err_msg}", "error")
    except Exception as e:
        flash(f"An unexpected error occurred during OCR execution: {e}", "error")

    return redirect(url_for('site_bill_details', bill_id=bill_id))


@app.route('/bills/<bill_id>/calculate', methods=['POST'])
@login_required
def calculate_solar_endpoint(bill_id):
    from services.calculation_service import run_solar_calculations
    actor = session.get('user', {}).get('full_name', 'System')
    try:
        success, warnings = run_solar_calculations(bill_id, actor=actor)
        if success:
            if warnings:
                msg = f"Calculations completed with warnings: {', '.join(warnings)}"
                flash(msg, "warning")
            else:
                flash("Solar Sizing and Payback calculations completed successfully!", "success")
        else:
            err_msg = warnings[0] if warnings else "Unknown calculation error."
            flash(f"Calculation failed: {err_msg}", "error")
    except Exception as e:
        flash(f"An unexpected error occurred during solar calculations: {e}", "error")

    return redirect(url_for('site_bill_details', bill_id=bill_id))


@app.route('/bills/<bill_id>/generate-proposal', methods=['POST'])
@login_required
def generate_proposal_route(bill_id):
    from services.proposal_generator import generate_proposal_record
    actor = session.get('user', {}).get('full_name', 'System')
    remarks = request.form.get('remarks', '').strip()
    
    success, warnings, proposal_id = generate_proposal_record(bill_id, actor=actor, remarks=remarks)
    if success:
        flash("Solar proposal generated successfully!", "success")
        return redirect(url_for('proposal_preview_route', proposal_id=proposal_id))
    else:
        err = warnings[0] if warnings else "Unknown proposal generation error."
        flash(f"Proposal Generation failed: {err}", "error")
        return redirect(url_for('site_bill_details', bill_id=bill_id))


@app.route('/proposals')
@login_required
def proposals_list_route():
    from services.proposal_service import list_proposals
    search_q = request.args.get('search', '').strip()
    status_f = request.args.get('status', 'all')
    customer_f = request.args.get('customer', 'all')
    sort_order = request.args.get('sort', 'newest')
    
    proposals_list = list_proposals(search_q=search_q, status_f=status_f, customer_f=customer_f, sort_order=sort_order)
    cust_list = list_customers()
    
    return render_template(
        'proposals.html',
        active_page='proposals',
        proposals=proposals_list,
        customers=cust_list,
        search_q=search_q,
        status_filter=status_f,
        customer_filter=customer_f,
        sort_order=sort_order
    )


@app.route('/proposal/<proposal_id>')
@login_required
def proposal_preview_route(proposal_id):
    from services.proposal_service import get_proposal_details, get_proposal_versions
    import json
    proposal = get_proposal_details(proposal_id)
    if not proposal:
        flash("Client proposal not found.", "error")
        return redirect(url_for('proposals_list_route'))
        
    versions = get_proposal_versions(proposal["proposal_number"])
    
    ocr_data = {}
    if proposal.get("normalized_json"):
        try:
            ocr_data = json.loads(proposal["normalized_json"])
        except Exception:
            pass

    from services.project_service import has_active_project_for_proposal
    has_project, project_id = has_active_project_for_proposal(proposal_id)
            
    return render_template(
        'proposal_preview.html',
        active_page='proposals',
        proposal=proposal,
        versions=versions,
        ocr_data=ocr_data,
        has_project=has_project,
        project_id=project_id
    )


@app.route('/proposal/<proposal_id>/status', methods=['POST'])
@login_required
def proposal_status_route(proposal_id):
    from services.proposal_service import update_proposal_status
    actor = session.get('user', {}).get('full_name', 'System')
    new_status = request.form.get('status', '').strip()
    
    if update_proposal_status(proposal_id, new_status, actor=actor):
        flash(f"Proposal status updated to '{new_status}' successfully.", "success")
    else:
        flash("Failed to update proposal status.", "error")
        
    return redirect(url_for('proposal_preview_route', proposal_id=proposal_id))


@app.route('/proposal/<proposal_id>/generate-pdf', methods=['POST'])
@login_required
def generate_proposal_pdf_route(proposal_id):
    from services.pdf_generator import generate_proposal_pdf
    actor = session.get('user', {}).get('full_name', 'System')
    
    success, err_or_path = generate_proposal_pdf(proposal_id, actor=actor)
    if success:
        flash("PDF Proposal generated successfully!", "success")
    else:
        flash(f"PDF generation failed: {err_or_path}", "error")
        
    return redirect(url_for('proposal_preview_route', proposal_id=proposal_id))


@app.route('/proposal/<proposal_id>/download')
@login_required
def download_proposal_pdf_route(proposal_id):
    from services.proposal_service import get_proposal_details
    from flask import send_file
    import os
    
    proposal = get_proposal_details(proposal_id)
    if not proposal or not proposal.get("pdf_path"):
        flash("PDF document has not been generated for this proposal.", "error")
        return redirect(url_for('proposal_preview_route', proposal_id=proposal_id))
        
    pdf_path = proposal["pdf_path"]
    if not os.path.exists(pdf_path):
        flash("The generated PDF document file was not found on the server storage.", "error")
        return redirect(url_for('proposal_preview_route', proposal_id=proposal_id))
        
    download_name = f"{proposal['proposal_number']}-V{proposal['version']}.pdf"
    return send_file(pdf_path, as_attachment=True, download_name=download_name)


# =====================================================================
# SPRINT 8: PROJECT MANAGEMENT ROUTES
# =====================================================================

@app.route('/proposal/<proposal_id>/convert', methods=['POST'])
@login_required
def convert_proposal_to_project_route(proposal_id):
    from services.project_service import convert_proposal_to_project
    actor = session.get('user', {}).get('full_name', 'System')
    
    # Calculate some defaults
    # Expect 90 days execution period
    from datetime import datetime, timedelta
    start_date = datetime.now().strftime("%Y-%m-%d")
    expected_completion = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    
    success, result_id = convert_proposal_to_project(
        proposal_id=proposal_id,
        actor=actor,
        start_date=start_date,
        expected_completion=expected_completion,
        manager=actor,
        execution_model='EPC'
    )
    if success:
        flash("Proposal successfully converted into project!", "success")
        return redirect(url_for('project_dashboard_route', project_id=result_id))
    else:
        flash(f"Conversion failed: {result_id}", "error")
        return redirect(url_for('proposal_preview_route', proposal_id=proposal_id))


@app.route('/projects')
@login_required
def projects_list_route():
    from services.project_service import list_projects, get_project_managers
    
    search_q = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    manager_filter = request.args.get('manager', 'all')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    projects = list_projects(
        search_q=search_q,
        status_filter=status_filter,
        manager_filter=manager_filter,
        sort_by=sort_by,
        sort_order=sort_order
    )
    managers = get_project_managers()
    
    return render_template(
        'projects.html',
        active_page='projects',
        projects=projects,
        managers=managers,
        search_q=search_q,
        status_filter=status_filter,
        manager_filter=manager_filter,
        sort_by=sort_by,
        sort_order=sort_order
    )


@app.route('/project/<project_id>')
@login_required
def project_dashboard_route(project_id):
    from services.project_service import get_project_details, get_project_activities, get_project_documents
    
    project = get_project_details(project_id)
    if not project:
        flash("Project does not exist.", "error")
        return redirect(url_for('projects_list_route'))
        
    activities = get_project_activities(project_id)
    documents = get_project_documents(project_id)
    
    return render_template(
        'project_dashboard.html',
        active_page='projects',
        project=project,
        activities=activities,
        documents=documents
    )


@app.route('/project/<project_id>/edit')
@login_required
def project_edit_route(project_id):
    from services.project_service import get_project_details
    
    project = get_project_details(project_id)
    if not project:
        flash("Project does not exist.", "error")
        return redirect(url_for('projects_list_route'))
        
    return render_template(
        'project_details.html',
        active_page='projects',
        project=project
    )


@app.route('/project/<project_id>/update', methods=['POST'])
@login_required
def project_update_route(project_id):
    from services.project_service import update_project_status
    actor = session.get('user', {}).get('full_name', 'System')
    
    status = request.form.get('status')
    progress = int(request.form.get('progress_percentage', 0))
    remarks = request.form.get('remarks')
    manager = request.form.get('project_manager')
    expected_completion = request.form.get('expected_completion')
    
    success = update_project_status(
        project_id=project_id,
        new_status=status,
        progress=progress,
        actor=actor,
        remarks=remarks,
        manager=manager,
        expected_completion=expected_completion
    )
    
    if success:
        flash("Project details updated successfully!", "success")
    else:
        flash("Failed to update project status details.", "error")
        
    return redirect(url_for('project_dashboard_route', project_id=project_id))


@app.route('/project/<project_id>/upload', methods=['POST'])
@login_required
def project_upload_route(project_id):
    from services.project_service import get_project_details, add_project_document
    from werkzeug.utils import secure_filename
    import os
    
    project = get_project_details(project_id)
    if not project:
        flash("Project does not exist.", "error")
        return redirect(url_for('projects_list_route'))
        
    file = request.files.get('doc_file')
    doc_type = request.form.get('document_type')
    
    if not file or file.filename == '':
        flash("No file was selected for upload.", "error")
        return redirect(url_for('project_dashboard_route', project_id=project_id))
        
    proj_num = project["project_number"]
    dest_dir = os.path.join("uploads", "projects", proj_num)
    os.makedirs(dest_dir, exist_ok=True)
    
    orig_name = file.filename
    sec_name = secure_filename(orig_name)
    
    # Avoid collision
    base, ext = os.path.splitext(sec_name)
    stored_name = sec_name
    idx = 1
    while os.path.exists(os.path.join(dest_dir, stored_name)):
        stored_name = f"{base}_{idx}{ext}"
        idx += 1
        
    file_path = os.path.join(dest_dir, stored_name).replace("\\", "/")
    file.save(file_path)
    
    # Calculate file size
    file_size = os.path.getsize(file_path)
    actor = session.get('user', {}).get('full_name', 'System')
    
    success = add_project_document(
        project_id=project_id,
        document_type=doc_type,
        original_filename=orig_name,
        stored_filename=stored_name,
        file_path=file_path,
        file_size=file_size,
        uploaded_by=actor
    )
    
    if success:
        flash(f"Document '{orig_name}' uploaded successfully!", "success")
    else:
        flash("Failed to register document metadata in database.", "error")
        
    return redirect(url_for('project_dashboard_route', project_id=project_id))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
