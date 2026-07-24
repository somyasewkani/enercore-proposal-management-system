"""
Enercore AI Solar Proposal Generator
pages/dashboard.py

Executive dashboard: KPI summary, solar capacity pipeline chart,
follow-up reminders, and recent client activity backed by the database.
"""

from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

from components.chatbot import render_chatbot
from components.cards import glass_card, inject_card_styles, kpi_card, status_pill
from components.topnav import render_topnav

from services.dashboard_service import (
    get_dashboard_kpis,
    get_pipeline_chart_data,
    get_followups,
    get_recent_activity,
    export_recent_activity_csv,
)

_STATUS_STYLES = {
    "Proposal Sent": ("#fff4e5", "#b06a00"),
    "Analysis Phase": ("#eaf1ff", "#2456c9"),
    "Contract Signed": ("#e6f5ec", "#14532d"),
}

ICONT_MAP = {
    "leaderboard": "📈",
    "description": "📄",
    "analytics": "🎯",
    "solar_power": "🔆",
}


def _inject_dashboard_styles() -> None:
    st.markdown(
        """
        <style>
            .enercore-kpi-card {
                background: rgba(255,255,255,0.7);
                border: 1px solid rgba(255,255,255,0.4);
                border-radius: 16px;
                padding: 1.1rem 1.2rem;
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                box-shadow: 0 6px 20px rgba(11, 61, 46, 0.10);
                transition: all 0.3s ease;
            }

            .enercore-kpi-card:hover {
                background: rgba(255,255,255,0.85);
                transform: translateY(-2px);
            }

            .enercore-kpi-icon {
                width: 44px;
                height: 44px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.3rem;
                margin-bottom: 0.6rem;
            }

            .enercore-kpi-label {
                font-size: 0.75rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                color: #3f4a3d;
            }

            .enercore-kpi-value {
                font-size: 1.8rem;
                font-weight: 800;
                color: #191c1e;
                line-height: 1.15;
            }

            .enercore-kpi-delta-up {
                display: inline-block;
                margin-top: 0.4rem;
                font-size: 0.75rem;
                font-weight: 700;
                color: #006b1b;
                background: rgba(125, 220, 122, 0.3);
                border-radius: 999px;
                padding: 0.15rem 0.7rem;
            }

            .enercore-kpi-delta-neutral {
                display: inline-block;
                margin-top: 0.4rem;
                font-size: 0.75rem;
                font-weight: 600;
                color: #3f4a3d;
                background: rgba(224, 227, 229, 0.5);
                border-radius: 999px;
                padding: 0.15rem 0.7rem;
            }

            .enercore-followup-item {
                padding: 0.8rem 1rem;
                border-radius: 12px;
                border: 1px solid rgba(191, 202, 185, 0.3);
                background: rgba(236, 238, 240, 0.3);
                margin-bottom: 0.6rem;
                transition: all 0.2s ease;
            }

            .enercore-followup-item:hover {
                border-color: rgba(0, 107, 27, 0.4);
                background: rgba(236, 238, 240, 0.5);
            }

            .enercore-followup-when {
                font-size: 0.75rem;
                font-weight: 700;
                color: #006b1b;
                text-transform: uppercase;
                letter-spacing: 0.04em;
            }

            .enercore-followup-secondary {
                font-size: 0.75rem;
                font-weight: 700;
                color: #8f4e00;
                text-transform: uppercase;
            }

            .enercore-followup-default {
                font-size: 0.75rem;
                font-weight: 600;
                color: #6f7a6b;
                text-transform: uppercase;
            }

            .enercore-followup-title {
                font-weight: 700;
                color: #191c1e;
                font-size: 0.95rem;
                margin-top: 0.2rem;
            }

            .enercore-followup-note {
                font-size: 0.85rem;
                color: #3f4a3d;
                margin-top: 0.2rem;
            }

            .enercore-status-pill {
                display: inline-block;
                font-size: 0.78rem;
                font-weight: 700;
                border-radius: 999px;
                padding: 0.2rem 0.7rem;
            }

            .enercore-section-title {
                font-weight: 700;
                font-size: 1.5rem;
                color: #191c1e;
                margin-bottom: 0.1rem;
            }

            .enercore-section-subtitle {
                font-size: 0.95rem;
                color: #3f4a3d;
                margin-bottom: 0.8rem;
            }

            .enercore-activity-table {
                border-collapse: collapse;
                width: 100%;
            }

            .enercore-activity-table th {
                font-size: 0.7rem;
                font-weight: 700;
                color: #6f7a6b;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                padding: 1rem;
                text-align: left;
                border-bottom: 1px solid rgba(191, 202, 185, 0.2);
            }

            .enercore-activity-table td {
                padding: 1rem;
                border-bottom: 1px solid rgba(191, 202, 185, 0.1);
            }

            .enercore-activity-table tr:hover {
                background: rgba(236, 238, 240, 0.3);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    """Render page header with breadcrumb and title."""
    st.markdown(
        '<span style="color:#8f4e00; font-weight:700; font-size:0.8rem; '
        'letter-spacing:0.2em; text-transform:uppercase; margin-bottom:0.5rem; display:block;">Executive Insights</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="enercore-section-title">Solar Portfolio Overview</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="enercore-section-subtitle">Real-time performance tracking for solar deployment operations.</div>',
        unsafe_allow_html=True,
    )


def _render_header_actions() -> str:
    """Render header action buttons (date filter and new proposal)."""
    action_col1, action_col2 = st.columns([3, 1.2])
    with action_col1:
        date_range = st.selectbox(
            "Date range",
            ["Last 30 Days", "Last 90 Days", "This Year", "All Time"],
            label_visibility="collapsed",
            key="streamlit_dashboard_date_filter",
        )
    with action_col2:
        if st.button("➕ New Proposal", use_container_width=True, type="primary"):
            st.session_state.active_page = "New Proposal"
            st.rerun()

    range_map = {"Last 30 Days": "30", "Last 90 Days": "90", "This Year": "365", "All Time": "all"}
    return range_map.get(date_range, "30")


def _render_kpis(kpis) -> None:
    cols = st.columns(4)
    for col, kpi in zip(cols, kpis):
        delta_class = "enercore-kpi-delta-up" if kpi["tone"] == "up" else "enercore-kpi-delta-neutral"
        icon_bg = "#d8f5e4" if kpi["tone"] == "up" else "#d3e4ff"
        icon_color = "#006b1b" if kpi["tone"] == "up" else "#005ea4"

        with col:
            icon = ICONT_MAP.get(kpi["icon"], "📊")
            st.markdown(
                f"""
                <div class="enercore-kpi-card">
                    <div class="enercore-kpi-icon" style="background:{icon_bg}; color:{icon_color};">{icon}</div>
                    <div class="enercore-kpi-label">{kpi["label"]}</div>
                    <div class="enercore-kpi-value">{kpi["value"]}</div>
                    <div class="{delta_class}">{kpi["delta"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_pipeline_chart(chart_data) -> None:
    st.markdown(
        """
        <div style="background:rgba(255,255,255,0.7); border:1px solid rgba(255,255,255,0.4);
            border-radius:16px; padding:1.5rem; backdrop-filter:blur(20px); margin-bottom:1rem;">
            <div style="font-weight:700; font-size:1.25rem; color:#191c1e; margin-bottom:0.5rem;">Solar Capacity Pipeline</div>
            <div style="font-size:0.85rem; color:#3f4a3d; margin-bottom:1rem;">Projected MW deployment per month for next 2 quarters.</div>
        """,
        unsafe_allow_html=True,
    )

    df = pd.DataFrame({
        "Month": chart_data["months"],
        "Residential": chart_data["residential"],
        "Commercial": chart_data["commercial"],
    })
    melted = df.melt(id_vars="Month", var_name="Segment", value_name="MW")
    fig = px.bar(
        melted,
        x="Month",
        y="MW",
        color="Segment",
        barmode="group",
        color_discrete_map={"Residential": "#006b1b", "Commercial": "#ff8f06"},
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=320,
        font=dict(color="#191c1e", size=12),
    )
    fig.update_yaxes(gridcolor="rgba(0,0,0,0.05)", ticksuffix=" MW")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def _render_followups(followups) -> None:
    st.markdown(
        f"""
        <div style="background:rgba(255,255,255,0.7); border:1px solid rgba(255,255,255,0.4);
            border-radius:16px; padding:1.5rem; backdrop-filter:blur(20px); margin-bottom:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                <div style="font-weight:700; font-size:1.25rem; color:#191c1e;">Follow-ups</div>
                <span style="background:#fff4e5; color:#623300; padding:0.25rem 0.75rem; border-radius:999px; font-size:0.75rem; font-weight:700;">{len(followups)} Today</span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    for item in followups:
        when_class = f"enercore-followup-{item['tone']}" if item['tone'] in ['secondary', 'default'] else "enercore-followup-when"
        st.markdown(
            f"""
            <div class="enercore-followup-item">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.3rem;">
                    <span class="{when_class}">{item["when"]}</span>
                    <span style="font-size:18px; color:#6f7a6b;">📞</span>
                </div>
                <div class="enercore-followup-title">{item["title"]}</div>
                <div class="enercore-followup-note">{item["note"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button("View All Reminders", use_container_width=True, key="btn_followups"):
        st.session_state.active_page = "Pipeline"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _render_recent_activity(search_query: str) -> None:
    st.markdown(
        """
        <div style="background:rgba(255,255,255,0.7); border:1px solid rgba(255,255,255,0.4);
            border-radius:16px; padding:0; backdrop-filter:blur(20px); overflow:hidden; margin-top:1rem;">
        """,
        unsafe_allow_html=True,
    )

    # Header section
    st.markdown(
        """
        <div style="padding:1.5rem; border-bottom:1px solid rgba(191,202,185,0.2);
            display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-weight:700; font-size:1.25rem; color:#191c1e;">Recent Client Activity</div>
                <div style="font-size:0.85rem; color:#3f4a3d;">Latest updates from the sales and implementation pipeline.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Action buttons
    b1, b2 = st.columns([1, 1])
    with b1:
        csv_data = export_recent_activity_csv(search=search_query)
        st.download_button(
            label="Export CSV",
            data=csv_data,
            file_name="enercore_activity.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with b2:
        if st.button("View All Activity", use_container_width=True, type="primary", key="btn_all_activity"):
            st.session_state.active_page = "Clients"
            st.rerun()

    items, _ = get_recent_activity(search=search_query, per_page=10)

    if items:
        # Table header
        header_cols = st.columns([2.5, 1.5, 1.5, 1.5, 1])
        for col, label in zip(header_cols, ["Client / Company", "Updated Date", "Project Status", "Contract Value", "Action"]):
            col.markdown(
                f'<span style="font-size:0.75rem; font-weight:700; color:#3f4a3d; text-transform:uppercase;">{label}</span>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr style="margin:0.5rem 0; border-color:rgba(191,202,185,0.15);">', unsafe_allow_html=True)

        for item in items:
            cols = st.columns([2.5, 1.5, 1.5, 1.5, 1])
            cols[0].markdown(f"**{item['name']}**\n\n*{item['segment']}*")
            cols[1].markdown(f'<span style="font-size:0.85rem; color:#3f4a3d;">{item["updated_at"]}</span>', unsafe_allow_html=True)
            bg, fg = _STATUS_STYLES.get(item["status"], ("#eee", "#333"))
            cols[2].markdown(
                f'<span class="enercore-status-pill" style="background:{bg}; color:{fg};">{item["status"]}</span>',
                unsafe_allow_html=True,
            )
            cols[3].markdown(f"**{item['value_formatted']}**")
            cols[4].markdown("⋯", help="More actions")
    else:
        st.info("No recent client activity records found.")

    st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard() -> None:
    """Render the full executive dashboard page."""
    inject_card_styles()
    _inject_dashboard_styles()

    # Top navigation bar
    search_q = render_topnav(search_placeholder="Search leads, proposals, or assets...", breadcrumbs=None)

    _render_header()
    date_range_val = _render_header_actions()

    # Fetch dynamic database metrics
    kpis = get_dashboard_kpis(date_range=date_range_val)
    chart_data = get_pipeline_chart_data()
    followups = get_followups()

    st.write("")
    _render_kpis(kpis)

    st.write("")
    chart_col, followup_col = st.columns([2, 1])
    with chart_col:
        _render_pipeline_chart(chart_data)
    with followup_col:
        _render_followups(followups)

    _render_recent_activity(search_query=search_q or "")

    # Floating AI Chatbot
    render_chatbot()