"""
Enercore AI Solar Proposal Generator
pages/settings.py

Settings page (nav item: Settings). Tabs for profile, organization
branding, notifications, team management, and integrations. All
values are placeholder data until services/settings_service.py and
the database layer are connected.
"""

import streamlit as st

from components.cards import glass_card, inject_card_styles, status_pill

_TEAM_MEMBERS = [
    {"name": "Ava Whitfield", "email": "admin@enercore.ai", "role": "Solar Proposal Admin", "status": "Active"},
    {"name": "Marcus Lee", "email": "sales@enercore.ai", "role": "Sales Engineer", "status": "Active"},
    {"name": "Priya Nandakumar", "email": "priya@enercore.ai", "role": "Analyst", "status": "Active"},
    {"name": "Devon Ortiz", "email": "devon@enercore.ai", "role": "Sales Engineer", "status": "Invited"},
]

_INTEGRATIONS = [
    {"name": "Salesforce CRM", "icon": "🧭", "connected": True, "description": "Sync leads and opportunities"},
    {"name": "DocuSign", "icon": "✍️", "connected": True, "description": "Send proposals for e-signature"},
    {"name": "QuickBooks", "icon": "📒", "connected": False, "description": "Sync invoices and contract value"},
    {"name": "Slack", "icon": "💬", "connected": False, "description": "Get proposal and deal alerts"},
]


def _render_header() -> None:
    st.markdown(
        '<span style="color:#1c7c4f; font-weight:700; font-size:0.72rem; '
        'letter-spacing:0.08em; text-transform:uppercase;">Account &amp; Workspace</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-weight:700; font-size:1.5rem; color:#0b3d2e; margin-bottom:0.1rem;">'
        "Settings</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.85rem; color:#5b7267; margin-bottom:1rem;">'
        "Manage your profile, organization details, and integrations.</div>",
        unsafe_allow_html=True,
    )


def _render_profile_tab() -> None:
    user = st.session_state.get("user") or {}
    with glass_card():
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Full name", value=user.get("full_name", "Ava Whitfield"))
            st.text_input("Work email", value=user.get("email", "admin@enercore.ai"), disabled=True)
        with col2:
            st.text_input("Role", value=user.get("role", "Solar Proposal Admin"), disabled=True)
            st.selectbox("Timezone", ["Pacific Time (PT)", "Mountain Time (MT)", "Central Time (CT)", "Eastern Time (ET)"])

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Change password**")
        p1, p2 = st.columns(2)
        with p1:
            st.text_input("New password", type="password", placeholder="••••••••")
        with p2:
            st.text_input("Confirm new password", type="password", placeholder="••••••••")

        st.write("")
        if st.button("Save Profile Changes", type="primary"):
            st.success("Profile changes saved. (Not yet persisted — database layer not connected.)")


def _render_organization_tab() -> None:
    with glass_card():
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Company name", value="Enercore Group")
            st.text_input("Industry", value="Renewable Energy / Solar EPC")
            st.text_input("Primary contact email", value="ops@enercore.ai")
        with col2:
            st.text_input("Business address", value="500 Solar Way, Sacramento, CA")
            st.selectbox("Default currency", ["USD ($)", "EUR (€)", "GBP (£)", "INR (₹)"])
            st.file_uploader("Company logo", type=["png", "jpg", "svg"])

        st.write("")
        if st.button("Save Organization Details", type="primary"):
            st.success("Organization details saved. (Not yet persisted — database layer not connected.)")


def _render_notifications_tab() -> None:
    with glass_card():
        st.markdown("**Email notifications**")
        st.toggle("New lead assigned to me", value=True)
        st.toggle("Proposal viewed by client", value=True)
        st.toggle("Contract signed", value=True)
        st.toggle("Weekly performance summary", value=False)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**SMS alerts**")
        st.toggle("Urgent follow-up reminders", value=True)
        st.toggle("Contract signature deadlines", value=False)

        st.write("")
        if st.button("Save Notification Preferences", type="primary"):
            st.success("Notification preferences saved.")


def _render_team_tab() -> None:
    with glass_card():
        header_col, action_col = st.columns([3, 1])
        with header_col:
            st.markdown("**Team members**")
        with action_col:
            st.button("➕ Invite Member", use_container_width=True)

        st.markdown(
            '<hr style="margin:0.5rem 0 0.7rem 0; border-color:rgba(11,61,46,0.08);">',
            unsafe_allow_html=True,
        )

        header_cols = st.columns([2, 2.4, 2, 1.2])
        for col, label in zip(header_cols, ["NAME", "EMAIL", "ROLE", "STATUS"]):
            col.markdown(
                f'<span style="font-size:0.7rem; font-weight:700; color:#5b7267; '
                f'letter-spacing:0.04em;">{label}</span>',
                unsafe_allow_html=True,
            )

        for member in _TEAM_MEMBERS:
            cols = st.columns([2, 2.4, 2, 1.2])
            cols[0].markdown(f"**{member['name']}**")
            cols[1].markdown(
                f'<span style="color:#5b7267; font-size:0.85rem;">{member["email"]}</span>',
                unsafe_allow_html=True,
            )
            cols[2].markdown(
                f'<span style="color:#5b7267; font-size:0.85rem;">{member["role"]}</span>',
                unsafe_allow_html=True,
            )
            tone = "success" if member["status"] == "Active" else "warning"
            cols[3].markdown(status_pill(member["status"], tone), unsafe_allow_html=True)


def _render_integrations_tab() -> None:
    cols = st.columns(2)
    for i, integration in enumerate(_INTEGRATIONS):
        with cols[i % 2]:
            with glass_card():
                top_col1, top_col2 = st.columns([3, 1])
                with top_col1:
                    st.markdown(
                        f'<div style="font-size:1.4rem;">{integration["icon"]}</div>'
                        f'<div style="font-weight:700; color:#0b3d2e; margin-top:0.3rem;">{integration["name"]}</div>'
                        f'<div style="font-size:0.8rem; color:#5b7267;">{integration["description"]}</div>',
                        unsafe_allow_html=True,
                    )
                with top_col2:
                    tone = "success" if integration["connected"] else "neutral"
                    label = "Connected" if integration["connected"] else "Not Connected"
                    st.markdown(
                        f'<div style="text-align:right; margin-top:0.3rem;">{status_pill(label, tone)}</div>',
                        unsafe_allow_html=True,
                    )
                st.write("")
                button_label = "Manage" if integration["connected"] else "Connect"
                st.button(button_label, key=f"integration_{integration['name']}", use_container_width=True)


def render_settings() -> None:
    """Render the full Settings page with tabbed sections."""
    inject_card_styles()
    _render_header()

    tab_profile, tab_org, tab_notifications, tab_team, tab_integrations = st.tabs(
        ["Profile", "Organization", "Notifications", "Team", "Integrations"]
    )

    with tab_profile:
        _render_profile_tab()
    with tab_org:
        _render_organization_tab()
    with tab_notifications:
        _render_notifications_tab()
    with tab_team:
        _render_team_tab()
    with tab_integrations:
        _render_integrations_tab()