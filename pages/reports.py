"""
Enercore AI Solar Proposal Generator
pages/reports.py

Analytics page (nav item: Analytics). Revenue trend, proposal
conversion funnel, and regional capacity breakdown. All chart data
below is placeholder data until services/analytics_service.py is
connected to the reporting warehouse.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.cards import glass_card, inject_card_styles
from components.chatbot import render_chatbot
from components.topnav import render_topnav

# --------------------------------------------------------------------------- #
# Placeholder data (to be replaced by services/analytics_service.py)
# --------------------------------------------------------------------------- #
_KPIS = [
    {"label": "Total Revenue Potential", "value": "$4.2M", "delta": "+12.4%", "icon": "📈", "tone": "up"},
    {"label": "Proposed Capacity", "value": "84.5 MW", "delta": "+28%", "icon": "⚡", "tone": "up"},
    {"label": "Active Proposals", "value": "94", "delta": "142 total", "icon": "📄", "tone": "neutral"},
    {"label": "Client Retention", "value": "High", "delta": "89% score", "icon": "💝", "tone": "up"},
]

_REVENUE_TREND = pd.DataFrame(
    {
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "Revenue": [2.1, 2.6, 3.0, 3.4, 4.1, 4.9],
    }
)

_FUNNEL_STAGES = pd.DataFrame(
    {
        "Stage": ["Leads", "Qualified", "Site Analysis", "Proposal Sent", "Contract Signed"],
        "Count": [1284, 860, 612, 342, 214],
    }
)

_REGIONAL = pd.DataFrame(
    {
        "Region": ["Manufacturing & Logistics", "Healthcare Systems", "Educational Campus", "Commercial Real Estate"],
        "Revenue ($M)": [1.4, 0.9, 0.7, 1.2],
    }
)

_INDUSTRY_LEADS = pd.DataFrame(
    [
        {"industry": "Manufacturing", "leads": 42, "deal_size": "$245k", "win_prob": 72, "trend": "up"},
        {"industry": "Healthcare", "leads": 28, "deal_size": "$180k", "win_prob": 54, "trend": "flat"},
        {"industry": "Retail Centers", "leads": 19, "deal_size": "$112k", "win_prob": 32, "trend": "down"},
    ]
)

# Data for dual-line area chart (Lead Conversion Trends)
_LEAD_DATA = pd.DataFrame(
    {
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"] * 2,
        "Leads": [80, 70, 75, 65, 55, 40, 85, 75, 80, 75, 60, 45],
        "Type": ["Converted"] * 6 + ["Identified"] * 6,
    }
)

# Data for Solar Capacity Proposed (pie chart)
_CAPACITY_DATA = pd.DataFrame(
    {
        "Segment": ["Residential", "Commercial", "Industrial", "Utility"],
        "Capacity (MW)": [12.5, 28.3, 32.1, 11.6],
    }
)


def _inject_reports_styles() -> None:
    st.markdown(
        """
        <style>
            .enercore-stats-card {
                background: rgba(255,255,255,0.6);
                border: 1px solid rgba(255,255,255,0.4);
                border-radius: 20px;
                padding: 1.5rem;
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                box-shadow: 0 6px 20px rgba(11, 61, 46, 0.10);
                transition: all 0.3s ease;
            }

            .enercore-stats-card:hover {
                transform: translateY(-4px);
            }

            .enercore-stats-icon {
                width: 48px;
                height: 48px;
                border-radius: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
                margin-bottom: 0.75rem;
            }

            .enercore-stats-label {
                font-size: 0.75rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                color: #6f7a6b;
            }

            .enercore-stats-value {
                font-size: 1.5rem;
                font-weight: 700;
                color: #191c1e;
                line-height: 1.2;
            }

            .enercore-chart-card {
                background: rgba(255,255,255,0.6);
                border: 1px solid rgba(255,255,255,0.4);
                border-radius: 24px;
                padding: 2rem;
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                box-shadow: 0 6px 20px rgba(11, 61, 46, 0.10);
                transition: all 0.3s ease;
            }

            .enercore-chart-card:hover {
                transform: translateY(-4px);
            }

            .enercore-subsection-title {
                font-weight: 700;
                font-size: 1.25rem;
                color: #191c1e;
                margin-bottom: 0.25rem;
            }

            .enercore-subsection-desc {
                font-size: 0.85rem;
                color: #3f4a3d;
                margin-bottom: 1.5rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    st.markdown(
        '<span style="color:#006b1b; font-weight:700; font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase;">Performance Overview</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-weight:700; font-size:2rem; color:#191c1e; margin-bottom:0.1rem;">Intelligence Dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:1rem; color:#3f4a3d; margin-bottom:0.8rem;">Real-time solar performance metrics and predictive growth insights.</div>',
        unsafe_allow_html=True,
    )

    filter_col, export_col = st.columns([3, 1.2])
    with filter_col:
        st.selectbox(
            "Date range",
            ["Year to Date", "Last 90 Days", "Last 30 Days", "Custom Range"],
            label_visibility="collapsed",
        )
    with export_col:
        st.button("📥 Export Report", use_container_width=True, type="primary")


def _render_kpis() -> None:
    cols = st.columns(4)
    for col, kpi in zip(cols, _KPIS):
        with col:
            bg_color = "#e6f5ec" if kpi["tone"] == "up" else "#eaf1ff"
            icon_color = "#006b1b" if kpi["tone"] == "up" else "#005ea4"

            st.markdown(
                f"""
                <div class="enercore-stats-card">
                    <div class="enercore-stats-icon" style="background:{bg_color}; color:{icon_color};">{kpi["icon"]}</div>
                    <div class="enercore-stats-label">{kpi["label"]}</div>
                    <div class="enercore-stats-value">{kpi["value"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_lead_conversion_trends() -> None:
    """Render the lead conversion trends area chart with dual lines."""
    st.markdown(
        """
        <div class="enercore-chart-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1.5rem;">
                <div>
                    <div class="enercore-subsection-title">Lead Conversion Trends</div>
                    <div class="enercore-subsection-desc">Pipeline efficiency over the last 6 months</div>
                </div>
                <div style="display:flex; gap:1rem; align-items:center;">
                    <div style="display:flex; align-items:center; gap:0.5rem;">
                        <div style="width:10px; height:10px; border-radius:50%; background:#006b1b;"></div>
                        <span style="font-size:0.85rem; color:#191c1e;">Converted</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.5rem;">
                        <div style="width:10px; height:10px; border-radius:50%; background:#005ea4;"></div>
                        <span style="font-size:0.85rem; color:#191c1e;">Identified</span>
                    </div>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Create dual line area chart
    fig = go.Figure()

    # Converted leads - solid line with area fill
    converted_data = _LEAD_DATA[_LEAD_DATA["Type"] == "Converted"]
    fig.add_trace(go.Scatter(
        x=converted_data["Month"],
        y=converted_data["Leads"],
        mode='lines',
        name='Converted',
        line=dict(color='#006b1b', width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 107, 27, 0.2)',
    ))

    # Identified leads - dashed line
    identified_data = _LEAD_DATA[_LEAD_DATA["Type"] == "Identified"]
    fig.add_trace(go.Scatter(
        x=identified_data["Month"],
        y=identified_data["Leads"],
        mode='lines',
        name='Identified',
        line=dict(color='#005ea4', width=2, dash='dash'),
    ))

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=40),
        height=280,
        font=dict(color="#191c1e", size=12),
        showlegend=False,
        hovermode='x unified',
    )
    fig.update_xaxes(gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=11))
    fig.update_yaxes(gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=11))

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def _render_solar_capacity_pie() -> None:
    """Render the solar capacity proposed pie chart."""
    st.markdown(
        """
        <div class="enercore-chart-card">
            <div class="enercore-subsection-title">Solar Capacity Proposed</div>
            <div class="enercore-subsection-desc">By segment distribution</div>
        """,
        unsafe_allow_html=True,
    )

    fig = go.Figure(data=[go.Pie(
        labels=_CAPACITY_DATA["Segment"],
        values=_CAPACITY_DATA["Capacity (MW)"],
        marker=dict(
            colors=['#006b1b', '#ff8f06', '#005ea4', '#ffdcc2'],
            line=dict(color='rgba(255,255,255,0.8)', width=2)
        ),
        hole=0.4,
        textinfo='label+percent',
        textfont=dict(size=11, color='#191c1e'),
        hovertemplate='<b>%{label}</b><br>%{value} MW<extra></extra>',
    )])

    fig.update_layout(
        height=260,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def _render_revenue_potential() -> None:
    """Render the revenue potential by industry bar chart."""
    st.markdown(
        """
        <div class="enercore-chart-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem;">
                <div>
                    <div class="enercore-subsection-title">Revenue Potential by Industry</div>
                    <div class="enercore-subsection-desc">Projected revenue by sector</div>
                </div>
                <div style="font-size:0.85rem; font-weight:600; color:#006b1b; cursor:pointer;">
                    VIEW DETAILS →
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    for _, row in _REGIONAL.iterrows():
        pct = int((row["Revenue ($M)"] / 1.4) * 100)
        bar_color = "#006b1b" if row["Revenue ($M)"] == 1.4 else "#ff8f06" if row["Revenue ($M)"] == 1.2 else "#005ea4" if row["Revenue ($M)"] == 0.9 else "#ffdcc2"
        st.markdown(
            f"""
            <div style="margin-bottom:1rem;">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.25rem;">
                    <span style="font-size:0.9rem; color:#191c1e; font-weight:600;">{row["Region"]}</span>
                    <span style="font-size:0.9rem; color:#3f4a3d;">${row["Revenue ($M)"]}M</span>
                </div>
                <div style="width:100%; height:6px; background:#e6e8ea; border-radius:999px;">
                    <div style="width:{pct}%; height:6px; background:{bar_color}; border-radius:999px;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_proposals_velocity() -> None:
    """Render the proposals velocity bar chart."""
    st.markdown(
        """
        <div class="enercore-chart-card">
            <div class="enercore-subsection-title">Proposals Velocity</div>
            <div class="enercore-subsection-desc">Monthly document generation trends</div>
        """,
        unsafe_allow_html=True,
    )

    months = ["Mar", "Apr", "May", "Jun", "Jul", "Aug"]
    values = [12, 18, 24, 32, 28, 40]

    fig = go.Figure(data=[go.Bar(
        x=months,
        y=values,
        marker=dict(
            color=['#d3e4ff', '#d3e4ff', '#d3e4ff', '#006b1b', '#7ddc7a', '#d3e4ff'],
            border_radius=8,
        ),
        text=values,
        textfont=dict(size=10, color='#191c1e'),
        textposition='outside',
    )])

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=30),
        height=260,
        font=dict(color="#191c1e", size=12),
        yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)', tickfont=dict(size=10)),
        xaxis=dict(tickfont=dict(size=11)),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        """
        <div style="margin-top:1rem; padding:1rem; background:rgba(0, 107, 27, 0.08); border-radius:12px; display:flex; align-items:center; gap:1rem;">
            <span style="font-size:1.5rem; color:#006b1b;">⚡</span>
            <div>
                <div style="font-size:0.9rem; font-weight:700; color:#191c1e;">Efficiency Gain: +14%</div>
                <div style="font-size:0.8rem; color:#3f4a3d;">AI Proposal drafting reduced turnaround by 4.2 hours.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_industry_leads_table() -> None:
    """Render the industry lead distribution table."""
    st.markdown(
        """
        <div style="background:rgba(255,255,255,0.6); border:1px solid rgba(255,255,255,0.4);
            border-radius:24px; overflow:hidden; margin-top:1.5rem;">
            <div style="padding:2rem; border-bottom:1px solid rgba(191,202,185,0.2); display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-weight:700; font-size:1.25rem; color:#191c1e;">Industry Lead Distribution</div>
                    <div style="font-size:0.85rem; color:#3f4a3d; margin-top:0.25rem;">Top sector opportunities and win-rates</div>
                </div>
                <button style="background:none; border:1px solid #006b1b; color:#006b1b; padding:0.5rem 1rem; border-radius:8px; font-weight:600; cursor:pointer;">
                    DOWNLOAD CSV
                </button>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Table headers
    header_cols = st.columns([2.5, 1.5, 1.2, 1.5, 0.8])
    labels = ["Industry Sector", "Active Leads", "Avg. Deal Size", "Win Probability", "Trend"]
    for col, label in zip(header_cols, labels):
        col.markdown(
            f'<span style="font-size:0.75rem; font-weight:700; color:#6f7a6b; text-transform:uppercase;">{label}</span>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr style="margin:0.5rem 0; border-color:rgba(191,202,185,0.15);">', unsafe_allow_html=True)

    for _, row in _INDUSTRY_LEADS.iterrows():
        cols = st.columns([2.5, 1.5, 1.2, 1.5, 0.8])

        with cols[0]:
            icon_map = {"Manufacturing": "🏭", "Healthcare": "🏥", "Retail Centers": "🛍️"}
            icon = icon_map.get(row["industry"], "📊")
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <div style="width:32px; height:32px; border-radius:8px; background:#e6e8ea; display:flex; align-items:center; justify-content:center; font-size:16px;">{icon}</div>
                    <span style="font-weight:700; color:#191c1e;">{row["industry"]}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with cols[1]:
            st.markdown(f'<span style="font-size:0.9rem; color:#191c1e;">{row["leads"]}</span>', unsafe_allow_html=True)

        with cols[2]:
            st.markdown(f'<span style="font-size:0.9rem; color:#191c1e;">{row["deal_size"]}</span>', unsafe_allow_html=True)

        with cols[3]:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <div style="flex:1; width:60px; height:6px; background:#e6e8ea; border-radius:999px;">
                        <div style="width:{row['win_prob']}%; height:6px; background:#006b1b; border-radius:999px;"></div>
                    </div>
                    <span style="font-size:0.85rem; font-weight:700; color:#191c1e;">{row["win_prob"]}%</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with cols[4]:
            trend_icon = "📈" if row["trend"] == "up" else "📉" if row["trend"] == "down" else "📊"
            trend_color = "#006b1b" if row["trend"] == "up" else "#ba1a1a" if row["trend"] == "down" else "#8f4e00"
            st.markdown(
                f'<span style="font-size:1.2rem; color:{trend_color};">{trend_icon}</span>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


def render_reports() -> None:
    """Render the full Analytics page."""
    inject_card_styles()

    # Top navigation bar
    render_topnav(search_placeholder="Search analytics, leads, reports...", breadcrumbs=None)

    _inject_reports_styles()
    _render_header()
    st.write("")
    _render_kpis()
    st.write("")

    # Row 1: Lead Conversion Trends (8 cols) + Solar Capacity Pie (4 cols)
    cols1 = st.columns([2, 1])
    with cols1[0]:
        _render_lead_conversion_trends()
    with cols1[1]:
        _render_solar_capacity_pie()

    st.write("")

    # Row 2: Revenue Potential (7 cols) + Proposals Velocity (5 cols)
    cols2 = st.columns([7, 5])
    with cols2[0]:
        _render_revenue_potential()
    with cols2[1]:
        _render_proposals_velocity()

    st.write("")
    _render_industry_leads_table()

    # Floating AI Chatbot
    render_chatbot()