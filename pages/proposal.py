"""
Enercore AI Solar Proposal Generator
pages/proposal.py

"New Proposal" wizard (nav item: New Proposal). Three steps:
  1. Upload Bill        -> pages/upload_bill.py (render_upload_bill)
  2. System Design       -> collects placeholder sizing inputs
  3. Financials & Generate -> shows placeholder financial summary and
                               a "Generate Proposal" action

Step state lives in st.session_state.proposal_step. All calculations
are placeholder heuristics until services/proposal_service.py is wired
up to a real sizing/financial engine.
"""

import streamlit as st

from components.cards import glass_card, inject_card_styles, kpi_card
from components.chatbot import render_chatbot
from components.topnav import render_topnav
from pages.upload_bill import render_upload_bill

_STEP_LABELS = {1: "Upload Bill", 2: "System Design", 3: "Financials & Generate"}


def _init_wizard_state() -> None:
    if "proposal_step" not in st.session_state:
        st.session_state.proposal_step = 1
    if "extracted_bill_data" not in st.session_state:
        st.session_state.extracted_bill_data = None
    if "system_design" not in st.session_state:
        st.session_state.system_design = None


def _render_step_tracker() -> None:
    cols = st.columns(3)
    current = st.session_state.proposal_step
    for i, (col, (step_num, label)) in enumerate(zip(cols, _STEP_LABELS.items())):
        with col:
            if step_num < current:
                marker, color = "✓", "#14532d"
            elif step_num == current:
                marker, color = str(step_num), "#006b1b"
            else:
                marker, color = str(step_num), "#a9b8b1"
            weight = "700" if step_num <= current else "500"
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <div style="width:26px; height:26px; border-radius:50%;
                                background:{'rgba(28,124,79,0.15)' if step_num <= current else 'rgba(169,184,177,0.15)'};
                                color:{color}; display:flex; align-items:center; justify-content:center;
                                font-weight:700; font-size:0.8rem; border:1.5px solid {color};">
                        {marker}
                    </div>
                    <span style="font-size:0.82rem; font-weight:{weight}; color:{color};">{label}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown(
        '<hr style="margin:0.8rem 0 1.2rem 0; border-color:rgba(191,202,185,0.2);">',
        unsafe_allow_html=True,
    )


def _estimate_system(avg_monthly_usage_kwh: int, roof_area_sqft: int, panel_wattage: int) -> dict:
    """Placeholder sizing heuristic — swap for services/proposal_service.py sizing engine."""
    annual_kwh = avg_monthly_usage_kwh * 12
    # rough placeholder assumption: 1 kW of solar produces ~1300 kWh/yr in this region
    system_size_kw = round(annual_kwh / 1300, 1)
    panel_area_sqft = 18  # approx per panel
    max_panels_by_roof = max(int(roof_area_sqft // panel_area_sqft), 1)
    panels_needed = max(int((system_size_kw * 1000) / panel_wattage), 1)
    panels_installed = min(panels_needed, max_panels_by_roof)
    actual_size_kw = round((panels_installed * panel_wattage) / 1000, 1)
    annual_production_kwh = int(actual_size_kw * 1300)
    offset_pct = min(round((annual_production_kwh / annual_kwh) * 100), 100) if annual_kwh else 0

    return {
        "system_size_kw": actual_size_kw,
        "panels_installed": panels_installed,
        "annual_production_kwh": annual_production_kwh,
        "offset_pct": offset_pct,
    }


def _render_step_1() -> None:
    inject_card_styles()
    st.markdown(
        '<span style="color:#006b1b; font-weight:700; font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.5rem; display:block;">New Proposal · Step 1 of 3</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-weight:700; font-size:1.5rem; color:#191c1e; margin-bottom:0.1rem;">Upload Electricity Bill</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.95rem; color:#3f4a3d; margin-bottom:1rem;">Upload utility statements to extract consumption profiles and calculate solar ROI.</div>',
        unsafe_allow_html=True,
    )

    render_upload_bill()


def _render_step_2() -> None:
    inject_card_styles()
    st.markdown(
        '<span style="color:#006b1b; font-weight:700; font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.5rem; display:block;">New Proposal · Step 2 of 3</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-weight:700; font-size:1.5rem; color:#191c1e; margin-bottom:0.1rem;">System Design</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.95rem; color:#3f4a3d; margin-bottom:1rem;">Configure the physical constraints for this site. Enercore AI will size the system against the usage data from the uploaded bill.</div>',
        unsafe_allow_html=True,
    )

    bill_data = st.session_state.get("extracted_bill_data") or {"avg_monthly_usage_kwh": 900}

    with glass_card():
        st.markdown(
            """
            <h3 style="font-weight:700; font-size:1.2rem; color:#191c1e; margin-bottom:1rem;">
                <span style="margin-right:0.5rem;">⚙️</span>
                Proposal Settings
            </h3>
            """,
            unsafe_allow_html=True,
        )

        # Theme Selection
        st.markdown(
            '<div style="font-weight:600; color:#3f4a3d; margin-bottom:0.5rem;">Theme choice</div>',
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            theme_choice = st.radio("Theme", ["Modern", "Classic"], horizontal=True)
        with col2:
            st.markdown(
                f'<span style="display:block; margin-top:0.5rem; font-size:0.85rem; color:#006b1b;">Using: {theme_choice}</span>',
                unsafe_allow_html=True,
            )

        st.write("")

        # Pricing Toggles
        st.markdown(
            '<div style="font-weight:600; color:#3f4a3d; margin-bottom:0.5rem;">Pricing Toggles</div>',
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            show_rebates = st.checkbox("Show Federal Rebates", value=True)
        with col2:
            show_roi = st.checkbox("Display ROI Timeline", value=True)

        st.write("")

        # Warranty Info
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(
                '<div style="font-weight:600; color:#3f4a3d; margin-bottom:0.5rem;">Warranty Info</div>',
                unsafe_allow_html=True,
            )
            warranty = st.selectbox(
                "Warranty",
                ["Standard 25-Year Performance Guarantee", "Extended 30-Year Comprehensive", "Premium Lifetime Service Plan"],
                label_visibility="collapsed",
            )

    st.write("")

    # Technical Specs Section
    with glass_card():
        st.markdown(
            """
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                <h3 style="font-weight:700; font-size:1.2rem; color:#191c1e; margin:0;">
                    <span style="margin-right:0.5rem;">⚙️</span>
                    Technical Specs
                </h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            roof_area = st.number_input(
                "Available roof area (sq ft)", min_value=100, max_value=50000, value=1400, step=50
            )
        with col2:
            panel_wattage = st.selectbox(
                "Panel wattage", options=[350, 400, 450, 500], index=2
            )
        with col3:
            roof_type = st.selectbox(
                "Roof type", options=["Asphalt Shingle", "Metal", "Tile", "Flat/Commercial"]
            )

        panel_type = st.radio(
            "Panel type", options=["Standard Monocrystalline", "Premium All-Black", "Bifacial"],
            horizontal=True,
        )

        if st.button("Run Sizing Estimate", use_container_width=True):
            st.session_state.system_design = _estimate_system(
                bill_data.get("avg_monthly_usage_kwh", 900), roof_area, panel_wattage
            ) | {"panel_type": panel_type, "roof_type": roof_type, "warranty": warranty, "show_rebates": show_rebates, "show_roi": show_roi}

        if st.session_state.get("system_design"):
            design = st.session_state.system_design
            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                kpi_card("System Size", f"{design['system_size_kw']} kW", icon="🔆")
            with m2:
                kpi_card("Panels", str(design["panels_installed"]), icon="🧩")
            with m3:
                kpi_card("Est. Annual Output", f"{design['annual_production_kwh']:,} kWh", icon="⚡")
            with m4:
                kpi_card("Usage Offset", f"{design['offset_pct']}%", icon="🎯", tone="up")

    st.write("")
    nav_col1, nav_col2 = st.columns(2)
    with nav_col1:
        if st.button("← Back to Bill Upload", use_container_width=True):
            st.session_state.proposal_step = 1
            st.rerun()
    with nav_col2:
        if st.button(
            "Continue to Financials  →",
            use_container_width=True,
            disabled=not st.session_state.get("system_design"),
        ):
            st.session_state.proposal_step = 3
            st.rerun()


def _render_step_3() -> None:
    inject_card_styles()
    st.markdown(
        '<span style="color:#006b1b; font-weight:700; font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.5rem; display:block;">New Proposal · Step 3 of 3</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-weight:700; font-size:1.5rem; color:#191c1e; margin-bottom:0.1rem;">Financials &amp; Generate</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.95rem; color:#3f4a3d; margin-bottom:1rem;">Review the projected costs and savings, then generate the client-ready proposal.</div>',
        unsafe_allow_html=True,
    )

    design = st.session_state.get("system_design") or {
        "system_size_kw": 8.5, "annual_production_kwh": 11050, "offset_pct": 92,
    }

    # Placeholder financial heuristics — replace with services/proposal_service.py
    cost_per_watt = 3.10
    gross_cost = design["system_size_kw"] * 1000 * cost_per_watt
    federal_credit = gross_cost * 0.30
    net_cost = gross_cost - federal_credit
    annual_savings = design["annual_production_kwh"] * 0.182
    payback_years = round(net_cost / annual_savings, 1) if annual_savings else 0

    # Side-by-side layout for financials and preview
    left_col, right_col = st.columns([1.5, 1])

    with left_col:
        with glass_card():
            st.markdown(
                """
                <h3 style="font-weight:700; font-size:1.2rem; color:#191c1e; margin-bottom:1rem;">
                    <span style="margin-right:0.5rem;">💰</span>
                    Financial Analysis
                </h3>
                <div style="height:1px; background:rgba(191,202,185,0.3); margin-bottom:1.5rem;"></div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f'<div style="font-size:0.9rem; color:#3f4a3d; margin-bottom:0.25rem;">System Total Cost</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div style="font-size:2rem; font-weight:700; color:#191c1e;">${gross_cost:,.0f}</div>',
                    unsafe_allow_html=True,
                )

            with col2:
                st.markdown(
                    f'<div style="font-size:0.9rem; color:#3f4a3d; margin-bottom:0.25rem;">Estimated Yearly Savings</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div style="font-size:2rem; font-weight:700; color:#006b1b;">+${annual_savings:,.0f}</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                f'<div style="font-size:0.9rem; color:#3f4a3d; margin-bottom:0.25rem;">Payback Period</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="font-size:2rem; font-weight:700; color:#ff8f06;">{payback_years} Years</div>',
                unsafe_allow_html=True,
            )

    with right_col:
        with glass_card():
            st.markdown(
                """
                <h3 style="font-weight:700; font-size:1.2rem; color:#191c1e; margin-bottom:1rem;">
                    <span style="margin-right:0.5rem;">🏢</span>
                    Company Profile
                </h3>
                """,
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(
                    """
                    <div style="width:64px; height:64px; border-radius:50%; background:rgba(38,134,48,0.1); display:flex; align-items:center; justify-content:center;">
                        <span style="font-size:32px; color:#006b1b;">✓</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown("**Tier 1 Installer**")
                st.markdown('<span style="font-size:0.85rem; color:#6f7a6b;">Accredited since 2012</span>', unsafe_allow_html=True)

    st.write("")
    client_name = st.text_input(
        "Proposal recipient (client name)",
        placeholder="e.g. Nexus Logistics",
        label_visibility="collapsed",
    )
    st.markdown(
        '<div style="font-size:0.75rem; color:#6f7a6b;">Enter the client name for the proposal document</div>',
        unsafe_allow_html=True,
    )

    st.write("")
    nav_col1, nav_col2 = st.columns(2)
    with nav_col1:
        if st.button("← Back to System Design", use_container_width=True):
            st.session_state.proposal_step = 2
            st.rerun()
    with nav_col2:
        if st.button("Generate Proposal  ✓", use_container_width=True, type="primary"):
            if not client_name:
                st.error("Please enter the client name before generating the proposal.")
            else:
                st.success(
                    f"Proposal generated for {client_name}. "
                    "(PDF export will be available once the document service is connected.)"
                )
                st.balloons()


def render_proposal() -> None:
    """Render the full New Proposal wizard, dispatching on the current step."""
    _init_wizard_state()
    _render_step_tracker()

    step = st.session_state.proposal_step
    if step == 1:
        _render_step_1()
    elif step == 2:
        _render_step_2()
    else:
        _render_step_3()