"""
Enercore AI Solar Proposal Generator
pages/proposal_history.py

Proposal History page: Table of past proposals with filtering capabilities,
status indicators, and action buttons. All data is placeholder until services/
proposal_service.py is connected.
"""

import pandas as pd
import streamlit as st

from components.cards import glass_card, inject_card_styles, status_pill


# --------------------------------------------------------------------------- #
# Placeholder data (to be replaced by services/proposal_service.py)
# --------------------------------------------------------------------------- #
_PROPOSALS = [
    {
        "id": "EC-8842-X",
        "status": "Synced",
        "client": "Meridian Tech Corp",
        "location": "Industrial District, Houston",
        "date": "Oct 24, 2023",
        "saved": "2 hours ago",
        "capacity": "450.5",
        "type": "Commercial",
    },
    {
        "id": "EC-7210-R",
        "status": "Draft",
        "client": "Harrison Residence",
        "location": "Palo Alto, CA",
        "date": "Oct 22, 2023",
        "saved": "1 day ago",
        "capacity": "12.8",
        "type": "Residential",
    },
    {
        "id": "EC-9102-U",
        "status": "Synced",
        "client": "Greenway Logistics",
        "location": "Utility Hub, Phoenix",
        "date": "Oct 18, 2023",
        "saved": "6 days ago",
        "capacity": "2,450.0",
        "type": "Commercial",
    },
    {
        "id": "EC-4451-C",
        "status": "Needs Review",
        "client": "Skyline Office Plaza",
        "location": "Downtown Denver",
        "date": "Oct 15, 2023",
        "saved": "9 days ago",
        "capacity": "85.2",
        "type": "Commercial",
    },
    {
        "id": "EC-1205-H",
        "status": "Signed",
        "client": "Westfield Medical Center",
        "location": "Sacramento, CA",
        "date": "Oct 10, 2023",
        "saved": "2 weeks ago",
        "capacity": "1,250.0",
        "type": "Healthcare",
    },
    {
        "id": "EC-3321-R",
        "status": "Synced",
        "client": "Sunnyvale Apartments",
        "location": "Sunnyvale, CA",
        "date": "Oct 5, 2023",
        "saved": "2 weeks ago",
        "capacity": "320.5",
        "type": "Residential",
    },
    {
        "id": "EC-5578-C",
        "status": "Draft",
        "client": "Metro Warehouse Group",
        "location": "Dallas, TX",
        "date": "Oct 3, 2023",
        "saved": "3 weeks ago",
        "capacity": "1,800.0",
        "type": "Commercial",
    },
    {
        "id": "EC-9912-I",
        "status": "Synced",
        "client": "Innovatech Systems",
        "location": "Austin, TX",
        "date": "Sep 28, 2023",
        "saved": "3 weeks ago",
        "capacity": "750.0",
        "type": "Technology",
    },
]

_STATUS_TONES = {
    "Synced": "success",
    "Draft": "warning",
    "Needs Review": "danger",
    "Signed": "success",
}

_TYPE_STYLES = {
    "Commercial": ("#e6f5ec", "#14532d"),
    "Residential": ("#eaf1ff", "#2456c9"),
    "Healthcare": ("#ffeaf0", "#c0392a"),
    "Technology": ("#fff4e5", "#b06a00"),
}


def _render_header() -> None:
    """Render the page header with stats and action button."""
    st.markdown(
        """
        <span style="color:#1c7c4f; font-weight:700; font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase;">Document Center</span>
        <div style="font-weight:700; font-size:1.5rem; color:#0b3d2e; margin-bottom:0.1rem;">Proposal History</div>
        <div style="font-size:0.85rem; color:#5b7267; margin-bottom:1rem;">Review, manage, and download all generated solar installation proposals.</div>
        """,
        unsafe_allow_html=True,
    )


def _render_stats_row() -> None:
    """Render the stats cards showing total proposals and capacity."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="enercore-stats-card">
                <p class="text-outline font-label-md" style="font-size:14px; text-transform:uppercase;">Total Proposals</p>
                <h3 class="text-on-surface" style="font-size:32px; font-weight:700;">1,248</h3>
                <p class="flex items-center gap-1 text-primary font-medium" style="font-size:14px; margin-top:0.5rem;">
                    <span>↑ 12% this month</span>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="enercore-stats-card">
                <p class="text-outline font-label-md" style="font-size:14px; text-transform:uppercase;">Active Capacity</p>
                <h3 class="text-on-surface" style="font-size:32px; font-weight:700;">14.2 MW</h3>
                <p class="flex items-center gap-1 text-tertiary font-medium" style="font-size:14px; margin-top:0.5rem;">
                    <span>Across all regions</span>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="enercore-stats-card" style="background:linear-gradient(180deg, rgba(255,255,255,0.7) 0%, rgba(230,245,236,0.2) 100%);">
                <h4 class="text-on-surface" style="font-size:18px; font-weight:600; margin-bottom:0.5rem;">Draft Continuity</h4>
                <p class="text-on-surface-variant" style="font-size:14px;">You have 4 unfinished proposals. Pick up where you left off to maximize your sales velocity.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_proposal_table() -> None:
    """Render the proposals table with status pills and action buttons."""
    with glass_card():
        st.markdown(
            """
            <div style="padding:0.5rem 1rem 0.5rem 1rem; border-bottom:1px solid rgba(11,61,46,0.1); display:flex; justify-content:space-between; align-items:center;">
                <div style="flex:1;">
                    <span style="font-size:16px; font-weight:600; color:#0b3d2e;">All Proposals</span>
                    <span style="background:#e6f5ec; color:#14532d; font-size:12px; padding:2px 8px; border-radius:999px; margin-left:0.5rem;">1.2k</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Header row
        header_cols = st.columns([1.2, 1.2, 2, 1.5, 1, 1.2])
        labels = ["PREVIEW", "PROPOSAL ID", "CLIENT NAME", "CREATED", "CAPACITY", "STATUS"]
        for col, label in zip(header_cols, labels):
            col.markdown(
                f'<span style="font-size:12px; font-weight:700; color:#5b7267; letter-spacing:0.04em;">{label}</span>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr style="margin:0.5rem 0; border-color:rgba(11,61,46,0.08);">', unsafe_allow_html=True)

        # Data rows
        for prop in _PROPOSALS:
            cols = st.columns([1.2, 1.2, 2, 1.5, 1, 1.2])

            with cols[0]:
                st.markdown(
                    """
                    <div style="width:80px; height:56px; background:#f2f4f6; border-radius:8px; border:1px solid #e0e3e5; display:flex; align-items:center; justify-content:center;">
                        <span style="font-size:24px; color:#bfcab9;">📄</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with cols[1]:
                st.markdown(f"**{prop['id']}**")
                tone = _STATUS_TONES.get(prop["status"], "neutral")
                st.markdown(status_pill(prop["status"], tone), unsafe_allow_html=True)

            with cols[2]:
                st.markdown(f"**{prop['client']}**")
                st.markdown(
                    f'<span style="font-size:13px; color:#5b7267;">{prop["location"]}</span>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(prop["date"])
                st.markdown(
                    f'<span style="font-size:11px; color:#5b7267; font-style:italic;">Saved: {prop["saved"]}</span>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                bg, fg = _TYPE_STYLES.get(prop["type"], ("#e6f5ec", "#14532d"))
                st.markdown(
                    f'<span style="font-size:16px; font-weight:700; color:#0b3d2e;">{prop["capacity"]}</span> '
                    f'<span style="font-size:12px; font-weight:700; color:#5b7267;">kWp</span>',
                    unsafe_allow_html=True,
                )

            with cols[5]:
                # Action buttons
                action_cols = st.columns(3)
                with action_cols[0]:
                    st.markdown(
                        '<span style="font-size:20px; color:#005ea4; cursor:pointer;">📥</span>',
                        unsafe_allow_html=True,
                    )
                with action_cols[1]:
                    st.markdown(
                        '<span style="font-size:20px; color:#14532d; cursor:pointer;">✏️</span>',
                        unsafe_allow_html=True,
                    )
                with action_cols[2]:
                    st.markdown(
                        '<span style="font-size:20px; color:#5b7267; cursor:pointer;">⋯</span>',
                        unsafe_allow_html=True,
                    )


def render_proposal_history() -> None:
    """Render the full Proposal History page."""
    inject_card_styles()

    _render_header()
    st.write("")
    _render_stats_row()
    st.write("")
    _render_proposal_table()

    # Pagination
    st.markdown(
        """
        <div style="margin-top:1.5rem; padding:1rem; border-top:1px solid rgba(11,61,46,0.1); display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:14px; color:#3f4a3d;">Showing 1 to 10 of 1,248 entries</span>
            <div style="display:flex; gap:0.5rem;">
                <span style="width:40px; height:40px; border-radius:8px; background:#e0e3e5; display:flex; align-items:center; justify-content:center; opacity:0.3;">←</span>
                <span style="width:40px; height:40px; border-radius:8px; background:#006b1b; color:white; display:flex; align-items:center; justify-content:center; font-weight:700;">1</span>
                <span style="width:40px; height:40px; border-radius:8px; background:#ffffff; border:1px solid #e0e3e5; display:flex; align-items:center; justify-content:center;">2</span>
                <span style="width:40px; height:40px; border-radius:8px; background:#ffffff; border:1px solid #e0e3e5; display:flex; align-items:center; justify-content:center;">3</span>
                <span style="width:40px; height:40px; border-radius:8px; background:#ffffff; border:1px solid #e0e3e5; display:flex; align-items:center; justify-content:center;">…</span>
                <span style="width:40px; height:40px; border-radius:8px; background:#ffffff; border:1px solid #e0e3e5; display:flex; align-items:center; justify-content:center;">125</span>
                <span style="width:40px; height:40px; border-radius:8px; background:#ffffff; border:1px solid #e0e3e5; display:flex; align-items:center; justify-content:center;"></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )