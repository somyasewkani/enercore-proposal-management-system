"""
Enercore AI Solar Proposal Generator
pages/pipeline.py

CRM Pipeline page: Kanban-style board for tracking solar project opportunities.
Shows deals across stages: New Lead, Contacted, Bill Received, Analysis Completed,
Proposal Sent, Negotiation, Won, Lost. All data is placeholder until services/
pipeline_service.py is connected.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.cards import glass_card, inject_card_styles, status_pill
from components.chatbot import render_chatbot
from components.topnav import render_topnav


# --------------------------------------------------------------------------- #
# Placeholder data (to be replaced by services/pipeline_service.py)
# --------------------------------------------------------------------------- #
_DEALS = [
    # New Lead stage
    {"company": "Horizon Logistics", "value": "$450,000", "category": "Commercial", "stage": "New Lead", "updated": "2 hours ago", "owner": "Ava W."},
    {"company": "Apex Manufacturing", "value": "$620,000", "category": "Industrial", "stage": "New Lead", "updated": "Yesterday", "owner": "Marcus L."},
    {"company": "Sunrise Retail", "value": "$380,000", "category": "Retail", "stage": "New Lead", "updated": "3 days ago", "owner": "Priya N."},
    # Contacted stage
    {"company": "Green Leaf Centers", "value": "$320,000", "category": "Retail", "stage": "Contacted", "updated": "Called today", "owner": "Alex R."},
    {"company": "Summit Offices", "value": "$550,000", "category": "Commercial", "stage": "Contacted", "updated": "Yesterday", "owner": "Devon O."},
    # Bill Received stage
    {"company": "Westside Public Works", "value": "$1,200,000", "category": "Municipal", "stage": "Bill Received", "updated": "3 files uploaded", "owner": "Ava W."},
    {"company": "Highland Hotels", "value": "$850,000", "category": "Hospitality", "stage": "Bill Received", "updated": "Bill reviewed", "owner": "Marcus L."},
    {"company": "Riverside Schools", "value": "$1,800,000", "category": "Education", "stage": "Bill Received", "updated": "Pending analysis", "owner": "Priya N."},
    {"company": "Metro Warehouses", "value": "$750,000", "category": "Commercial", "stage": "Bill Received", "updated": "Bill uploaded", "owner": "Alex R."},
    # Analysis Completed stage
    {"company": "Skyline Towers", "value": "$940,000", "category": "Ready for Proposal", "stage": "Analysis Completed", "updated": "ROI: 14.2%", "owner": "Devon O."},
    # Proposal Sent stage
    {"company": "Heavy Iron Foundry", "value": "$2,100,000", "category": "Industrial", "stage": "Proposal Sent", "updated": "Sent Oct 12", "owner": "Ava W."},
    {"company": "Coastal Resorts", "value": "$1,400,000", "category": "Hospitality", "stage": "Proposal Sent", "updated": "Sent Oct 15", "owner": "Marcus L."},
    # Negotiation stage
    {"company": "Grand Resort & Spa", "value": "$1,850,000", "category": "Hospitality", "stage": "Negotiation", "updated": "V3 Contract", "owner": "Alex R."},
    # Won stage
    {"company": "Starlight Automotive", "value": "$2,400,000", "category": "Industrial", "stage": "Won", "updated": "Closed Oct 10", "owner": "Ava W."},
    {"company": "Pinnacle Labs", "value": "$800,000", "category": "Technology", "stage": "Won", "updated": "Closed Oct 8", "owner": "Priya N."},
    {"company": "Cedar Medical Center", "value": "$650,000", "category": "Healthcare", "stage": "Won", "updated": "Closed Sep 28", "owner": "Devon O."},
    {"company": "Oceanview Apartments", "value": "$980,000", "category": "Residential", "stage": "Won", "updated": "Closed Sep 15", "owner": "Alex R."},
    {"company": "North Gate Storage", "value": "$340,000", "category": "Commercial", "stage": "Won", "updated": "Closed Oct 5", "owner": "Marcus L."},
    # Lost stage
    {"company": "DataStream Center", "value": "$450,000", "category": "Technology", "stage": "Lost", "updated": "No Budget", "owner": "Ava W."},
    {"company": "Valley Textiles", "value": "$200,000", "category": "Industrial", "stage": "Lost", "updated": "Went with competitor", "owner": "Priya N."},
]

_STAGES = ["New Lead", "Contacted", "Bill Received", "Analysis Completed", "Proposal Sent", "Negotiation", "Won", "Lost"]

_CATEGORY_STYLES = {
    "Commercial": ("#e6f5ec", "#14532d"),
    "Industrial": ("#fff4e5", "#b06a00"),
    "Retail": ("#eaf1ff", "#2456c9"),
    "Hospitality": ("#e6f5ec", "#14532d"),
    "Healthcare": ("#ffeaf0", "#c0392a"),
    "Education": ("#fff4e5", "#b06a00"),
    "Municipal": ("#d3e4ff", "#004881"),
    "Technology": ("#eaf1ff", "#2456c9"),
    "Residential": ("#e6f5ec", "#14532d"),
    "Ready for Proposal": ("#e6f5ec", "#14532d"),
}


def _deal_card(company: str, value: str, category: str, updated: str, owner: str) -> None:
    """Render a single deal card in the kanban style."""
    bg, fg = _CATEGORY_STYLES.get(category, ("#e6f5ec", "#14532d"))
    st.markdown(
        f"""
        <div class="enercore-deal-card">
            <div class="flex justify-between items-start mb-3">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold" style="background:{bg}; color:{fg};">{category}</span>
                <span class="text-on-surface-variant">⋯</span>
            </div>
            <div class="font-headline-md" style="font-size:18px; color:#10241d; margin-bottom:8px;">{company}</div>
            <div class="font-bold text-primary" style="font-size:18px; margin-bottom:16px;">{value}</div>
            <div class="flex justify-between items-center pt-3" style="border-top:1px solid rgba(11,61,46,0.1);">
                <div class="flex items-center gap-2">
                    <span style="font-size:16px; color:#5b7267;">🕒</span>
                    <span style="font-size:12px; color:#5b7267;">{updated}</span>
                </div>
                <div class="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold">
                    {owner[0]}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    """Render the page header with pipeline value and add lead button."""
    inject_card_styles()

    # Add deal card specific styles
    st.markdown(
        """
        <style>
        .enercore-deal-card {
            background: rgba(255,255,255,0.62);
            border: 1px solid rgba(255,255,255,0.5);
            border-radius: 16px;
            padding: 1.25rem;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 6px 18px rgba(11, 61, 46, 0.09);
            margin-bottom: 1rem;
        }
        .enercore-deal-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 24px rgba(11, 61, 46, 0.14);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    search_col, value_col, action_col = st.columns([2, 1.5, 1])

    with search_col:
        st.text_input(
            "Search pipeline",
            placeholder="🔍 Search pipeline, deals, or companies...",
            label_visibility="collapsed",
        )

    # Calculate total pipeline value
    total_value = sum(float(d["value"].replace("$", "").replace(",", "")) for d in _DEALS)

    with value_col:
        st.markdown(
            f"""
            <div style="text-align:center; padding:0.75rem 1rem; background:rgba(230,245,236,0.5); border-radius:12px; border:1px solid rgba(11,61,46,0.1);">
                <p style="font-size:12px; color:#5b7267; margin:0 0 0.25rem 0;">Total Pipeline Value</p>
                <p style="font-size:28px; font-weight:700; color:#14532d; margin:0;">${total_value/1_000_000:.1f}M</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with action_col:
        st.button("➕ Add New Lead", use_container_width=True, type="primary")


def _render_pipeline_kanban() -> None:
    """Render the kanban-style pipeline board with columns for each stage."""
    st.markdown("<br>", unsafe_allow_html=True)

    # Create columns for each stage
    cols = st.columns(len(_STAGES))

    for col, stage in zip(cols, _STAGES):
        with col:
            # Calculate stage value
            stage_deals = [d for d in _DEALS if d["stage"] == stage]
            stage_value = sum(float(d["value"].replace("$", "").replace(",", "")) for d in stage_deals)

            # Stage header
            stage_color = "#14532d" if stage == "Won" else "#ba1a1a" if stage == "Lost" else "#5b7267"
            st.markdown(
                f"""
                <div style="margin-bottom:1rem;">
                    <h3 style="font-size:12px; font-weight:700; letter-spacing:0.05em; color:{stage_color}; text-transform:uppercase; display:flex; align-items:center; gap:0.5rem;">
                        {stage}
                        <span style="background:rgba(226,232,240,0.8); padding:2px 8px; border-radius:999px; font-size:12px;">{len(stage_deals)}</span>
                    </h3>
                    <p style="font-size:14px; font-weight:600; color:#0b3d2e; margin:0.25rem 0 0.5rem 0;">${stage_value/1_000:.1f}K</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Deal cards - use expander for better mobile experience
            for deal in stage_deals:
                _deal_card(
                    company=deal["company"],
                    value=deal["value"],
                    category=deal["category"],
                    updated=deal["updated"],
                    owner=deal["owner"],
                )


def _render_funnel_chart() -> None:
    """Render a funnel chart showing conversion through pipeline stages."""
    with glass_card():
        st.markdown(
            """
            <div style="font-weight:700; font-size:20px; color:#0b3d2e; margin-bottom:0.5rem;">Pipeline Conversion</div>
            <div style="font-size:0.8rem; color:#5b7267; margin-bottom:1rem;">Deal value by stage (millions USD)</div>
            """,
            unsafe_allow_html=True,
        )

        stage_values = []
        for stage in _STAGES:
            deals = [d for d in _DEALS if d["stage"] == stage]
            value = sum(float(d["value"].replace("$", "").replace(",", "")) for d in deals) / 1_000_000
            stage_values.append(value)

        colors = ["#e2e8f0"] * 3 + ["#4fc785"] + ["#f5a623"] * 2 + ["#14532d", "#ba1a1a"]

        fig = go.Figure(
            go.Funnel(
                y=_STAGES,
                x=stage_values,
                marker=dict(colors=colors),
                textinfo="value+percent initial",
            )
        )
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#10241d", size=12),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_pipeline() -> None:
    """Render the full CRM Pipeline page."""
    inject_card_styles()

    # Top navigation bar
    render_topnav(search_placeholder="Search pipeline, deals, or companies...", breadcrumbs=None)

    # Page header
    st.markdown(
        """
        <span style="color:#1c7c4f; font-weight:700; font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase;">Sales Pipeline</span>
        <div style="font-weight:700; font-size:1.5rem; color:#0b3d2e; margin-bottom:0.1rem;">CRM Pipeline</div>
        <div style="font-size:0.85rem; color:#5b7267; margin-bottom:1rem;">Manage and track your solar project opportunities across all stages.</div>
        """,
        unsafe_allow_html=True,
    )

    _render_header()

    # Use tabs for kanban view and funnel view
    tab_kanban, tab_funnel = st.tabs(["Kanban Board", "Funnel View"])

    with tab_kanban:
        _render_pipeline_kanban()

    with tab_funnel:
        _render_funnel_chart()

    # Floating AI Chatbot
    render_chatbot()