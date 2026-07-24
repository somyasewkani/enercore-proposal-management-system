"""
Enercore AI Solar Proposal Generator
pages/customers.py

Clients page: KPI summary, search + segment/status filters, and a
responsive table of client data. All data is placeholder until services/customer_service.py
and the database layer are connected.
"""

import streamlit as st

from components.chatbot import render_chatbot
from components.cards import glass_card, inject_card_styles, kpi_card, status_pill
from components.topnav import render_topnav

# --------------------------------------------------------------------------- #
# Placeholder data (to be replaced by services/customer_service.py)
# --------------------------------------------------------------------------- #
_CLIENTS = [
    {
        "id": "SOL-8291",
        "company": "Nexus Logistics",
        "contact_person": "Sarah Jenkins",
        "contact_title": "Chief Ops Officer",
        "industry": "Warehouse",
        "location": "Austin, TX",
        "status": "Active Proposal",
        "status_tone": "success",
        "category": "Commercial",
    },
    {
        "id": "SOL-4432",
        "company": "Vertex Data Centers",
        "contact_person": "Marcus Thorne",
        "contact_title": "Sustainability Lead",
        "industry": "Technology",
        "location": "Ashburn, VA",
        "status": "Analysis Phase",
        "status_tone": "info",
        "category": "Commercial",
    },
    {
        "id": "SOL-1109",
        "company": "Summit Retail Group",
        "contact_person": "Elena Rodriguez",
        "contact_title": "Facility Manager",
        "industry": "Retail",
        "location": "Phoenix, AZ",
        "status": "On Hold",
        "status_tone": "neutral",
        "category": "Commercial",
    },
    {
        "id": "SOL-2278",
        "company": "Green Valley Health",
        "contact_person": "David Chen",
        "contact_title": "Energy Specialist",
        "industry": "Healthcare",
        "location": "Denver, CO",
        "status": "Proposal Sent",
        "status_tone": "success",
        "category": "Healthcare",
    },
]

_KPIS = [
    {"label": "Total Clients", "value": "128", "delta": "+9 this month", "icon": "👥", "tone": "up"},
    {"label": "Active Contracts", "value": "47", "delta": "Stable", "icon": "📑", "tone": "neutral"},
    {"label": "Total Contract Value", "value": "$68.4M", "delta": "+6.2%", "icon": "💰", "tone": "up"},
    {"label": "Avg. Deal Size", "value": "$534K", "delta": "Stable", "icon": "📐", "tone": "neutral"},
]

_INDUSTRY_OPTIONS = ["All", "Warehouse", "Technology", "Retail", "Healthcare", "Education", "Infrastructure"]


def _render_header() -> None:
    st.markdown(
        '<span style="color:#8f4e00; font-weight:700; font-size:0.8rem; '
        'letter-spacing:0.2em; text-transform:uppercase; margin-bottom:0.5rem; display:block;">Client Directory</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-weight:700; font-size:1.5rem; color:#191c1e; margin-bottom:0.1rem;">Clients</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.95rem; color:#3f4a3d; margin-bottom:1rem;">Monitor and manage your enterprise solar project portfolio.</div>',
        unsafe_allow_html=True,
    )


def _render_kpis() -> None:
    cols = st.columns(4)
    for col, kpi in zip(cols, _KPIS):
        with col:
            kpi_card(
                label=kpi["label"],
                value=kpi["value"],
                delta=kpi["delta"],
                icon=kpi["icon"],
                tone=kpi["tone"],
            )


def _render_filters(search_query: str) -> tuple[str, str, str]:
    seg_col, date_col, status_col = st.columns(3)
    with seg_col:
        industry = st.selectbox(
            "Industry filter",
            ["All Industries"] + _INDUSTRY_OPTIONS[:-1],
            label_visibility="collapsed",
        )
    with date_col:
        st.selectbox(
            "Last Activity",
            ["Last 30 Days", "Last 90 Days", "Last Year", "Custom Range"],
            label_visibility="collapsed",
        )
    with status_col:
        status = st.selectbox(
            "Status filter",
            ["All Statuses", "Active Proposal", "Analysis Phase", "On Hold", "Proposal Sent"],
            label_visibility="collapsed",
        )
    return industry, status


def _render_client_table(clients: list[dict]) -> None:
    """Render the clients in a table format matching the design."""
    for client in clients:
        cols = st.columns([3, 2, 1.5, 1.5, 1.2, 0.8])

        with cols[0]:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.75rem;">
                    <div style="width:38px; height:38px; border-radius:10px; background:rgba(0, 94, 164, 0.1); display:flex; align-items:center; justify-content:center; color:#005ea4;">
                        <span style="font-size:16px;">🏭</span>
                    </div>
                    <div>
                        <div style="font-weight:700; color:#191c1e; font-size:0.95rem;">{client["company"]}</div>
                        <div style="font-size:0.75rem; color:#6f7a6b;">ID: {client["id"]}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with cols[1]:
            st.markdown(f"**{client['contact_person']}**")
            st.markdown(
                f'<span style="font-size:0.75rem; color:#6f7a6b;">{client["contact_title"]}</span>',
                unsafe_allow_html=True,
            )

        with cols[2]:
            st.markdown(
                f'<span style="background:rgba(226,232,240,0.8); color:#191c1e; font-size:0.75rem; font-weight:700; padding:0.15rem 0.5rem; border-radius:999px;">{client["industry"]}</span>',
                unsafe_allow_html=True,
            )

        with cols[3]:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.25rem; font-size:0.85rem; color:#3f4a3d;">
                    <span style="font-size:16px;">📍</span>
                    {client["location"]}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with cols[4]:
            st.markdown(status_pill(client["status"], client["status_tone"]), unsafe_allow_html=True)

        with cols[5]:
            st.markdown("⋯", help="More actions")

        st.markdown(
            '<hr style="margin:0.75rem 0; border-color:rgba(191,202,185,0.15);">',
            unsafe_allow_html=True,
        )


def _render_right_sidebar() -> None:
    """Render the right sidebar widgets: Follow-ups and Quick Stats."""
    # Follow-ups widget
    st.markdown(
        """
        <div style="background:rgba(255,255,255,0.7); border-left:4px solid #ff8f06;
            border:1px solid rgba(255,255,255,0.4); border-radius:16px; padding:1.25rem;
            backdrop-filter:blur(20px); margin-bottom:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                <div style="font-weight:700; font-size:1.1rem; color:#191c1e;">Follow-ups</div>
                <span style="background:#ffddb3; color:#623300; padding:0.15rem 0.5rem; border-radius:999px; font-size:0.75rem; font-weight:700;">3 DUE</span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    follow_ups = [
        {"company": "Nexus Logistics", "status": "Overdue", "note": "Confirm site inspection date for the North-East hub expansion.", "due": "Scheduled: Oct 12"},
        {"company": "Vertex Data", "status": "Today", "note": "Send revised technical specs for the Ashburn facility solar array.", "due": "Due: 4:00 PM"},
        {"company": "Summit Retail", "status": "Tomorrow", "note": "Initial discovery call with Elena regarding Phoenix rollout.", "due": "Oct 16, 10:00 AM"},
    ]

    for item in follow_ups:
        status_color = "#ba1a1a" if item["status"] == "Overdue" else "#8f4e00" if item["status"] == "Today" else "#6f7a6b"
        st.markdown(
            f"""
            <div style="padding:0.75rem; background:rgba(236,238,240,0.5); border-radius:12px; margin-bottom:0.75rem; border:1px solid transparent; transition:all 0.2s;"
                onmouseover="this.style.borderColor='rgba(255,143,6,0.2)';" onmouseout="this.style.borderColor='transparent';">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.25rem;">
                    <span style="font-weight:700; color:#006b1b; font-size:0.85rem;">{item["company"]}</span>
                    <span style="font-size:0.7rem; font-weight:700; color:{status_color}; text-transform:uppercase;">{item["status"]}</span>
                </div>
                <div style="font-size:0.8rem; color:#3f4a3d; margin-bottom:0.5rem;">{item["note"]}</div>
                <div style="display:flex; align-items:center; gap:0.25rem; font-size:0.75rem; color:#6f7a6b;">
                    <span style="font-size:16px;">🕒</span>
                    {item["due"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.button("Manage All Reminders", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Quick Stats widget
    st.markdown(
        """
        <div style="background:rgba(255,255,255,0.7); border:1px solid rgba(255,255,255,0.4);
            border-radius:16px; padding:1.25rem; backdrop-filter:blur(20px); position:relative; overflow:hidden;">
            <div style="font-weight:700; font-size:1.1rem; color:#191c1e; margin-bottom:1rem;">Quick Stats</div>
        """,
        unsafe_allow_html=True,
    )

    # Conversion Rate
    st.markdown(
        """
        <div style="margin-bottom:1rem;">
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:0.25rem;">
                <span style="color:#6f7a6b;">Conversion Rate</span>
                <span style="color:#006b1b; font-weight:700;">24.8%</span>
            </div>
            <div style="width:100%; height:6px; background:#e6e8ea; border-radius:999px;">
                <div style="width:24.8%; height:6px; background:#006b1b; border-radius:999px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Proposal Velocity
    st.markdown(
        """
        <div style="margin-bottom:1rem;">
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:0.25rem;">
                <span style="color:#6f7a6b;">Proposal Velocity</span>
                <span style="color:#005ea4; font-weight:700;">+12d</span>
            </div>
            <div style="width:100%; height:6px; background:#e6e8ea; border-radius:999px;">
                <div style="width:65%; height:6px; background:#005ea4; border-radius:999px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="position:absolute; bottom:-1.5rem; right:-1.5rem; opacity:0.05; pointer-events:none;">
            <span style="font-size:8rem;">📊</span>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_customers() -> None:
    """Render the full Clients page."""
    inject_card_styles()

    # Top navigation bar
    render_topnav(search_placeholder="Search clients...", breadcrumbs=None)

    _render_header()
    st.write("")

    # Header actions
    header_cols = st.columns([3, 1.2])
    with header_cols[0]:
        search_query = st.text_input(
            "Search clients",
            placeholder="🔍 Search clients, proposals, or locations...",
            label_visibility="collapsed",
        )
    with header_cols[1]:
        if st.button("➕ Add New Client", use_container_width=True, type="primary"):
            st.info("Add client form will be available in a future update.")

    st.write("")
    _render_kpis()
    st.write("")

    industry, status = _render_filters(search_query)

    st.write("")
    st.markdown(
        f'<span style="font-size:0.85rem; color:#6f7a6b;">Showing {len(_CLIENTS)} of {len(_CLIENTS)} clients</span>',
        unsafe_allow_html=True,
    )

    main_col, right_col = st.columns([3, 1])

    with right_col:
        _render_right_sidebar()

    with main_col:
        # Table header
        st.markdown(
            """
            <div style="background:rgba(236,238,240,0.3); border-radius:12px 12px 0 0; padding:0.75rem 1rem; font-size:0.75rem; font-weight:700; color:#6f7a6b; text-transform:uppercase;">
                <div style="display:grid; grid-template-columns:3fr 2fr 1.5fr 1.5fr 1.2fr 0.8fr; gap:1rem;">
                    <span>COMPANY NAME</span>
                    <span>CONTACT PERSON</span>
                    <span>INDUSTRY</span>
                    <span>LOCATION</span>
                    <span>STATUS</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Table body
        for client in _CLIENTS:
            cols = st.columns([3, 2, 1.5, 1.5, 1.2, 0.8])

            with cols[0]:
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; gap:0.75rem; padding:0.75rem 0;">
                        <div style="width:38px; height:38px; border-radius:10px; background:rgba(0, 107, 27, 0.1); display:flex; align-items:center; justify-content:center; color:#006b1b;">
                            <span style="font-size:16px;">🏭</span>
                        </div>
                        <div>
                            <div style="font-weight:700; color:#191c1e; font-size:0.9rem;">{client["company"]}</div>
                            <div style="font-size:0.7rem; color:#6f7a6b;">ID: {client["id"]}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with cols[1]:
                st.markdown(
                    f"""
                    <div style="padding:0.75rem 0;">
                        <div style="font-weight:600; color:#191c1e; font-size:0.85rem;">{client['contact_person']}</div>
                        <div style="font-size:0.75rem; color:#6f7a6b;">{client['contact_title']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with cols[2]:
                st.markdown(
                    f'<span style="display:block; padding:0.75rem 0; background:rgba(226,232,240,0.8); color:#191c1e; font-size:0.75rem; font-weight:700; padding:0.25rem 0.6rem; border-radius:999px;">{client["industry"]}</span>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; gap:0.25rem; padding:0.75rem 0; font-size:0.85rem; color:#3f4a3d;">
                        <span>📍</span>
                        {client["location"]}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(status_pill(client["status"], client["status_tone"]), unsafe_allow_html=True)

            with cols[5]:
                st.markdown("⋯", help="More actions")

            st.markdown(
                '<hr style="margin:0; border-color:rgba(191,202,185,0.1);">',
                unsafe_allow_html=True,
            )

        # View all button
        st.markdown(
            """
            <div style="padding:1rem; text-align:center;">
                <span style="color:#006b1b; font-weight:700; font-size:0.85rem;">View All 48 Clients →</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Floating AI Chatbot
    render_chatbot()