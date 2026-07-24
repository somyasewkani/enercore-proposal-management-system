"""
Enercore AI Solar Proposal Generator
components/sidebar.py

Reusable, premium enterprise sidebar: brand header, icon-based navigation,
and a user profile footer with logout. Designed to be imported by app.py
and any page that needs consistent navigation.
"""

import streamlit as st

NAV_ITEMS = [
    ("Dashboard", "dashboard"),
    ("New Proposal", "description"),
    ("Clients", "groups"),
    ("Pipeline", "account_tree"),
    ("Analysis", "query_stats"),
    ("Proposal History", "history"),
    ("Analytics", "insights"),
    ("Settings", "settings"),
]

# Material Symbols icon mapping for each page
ICON_MAP = {name: icon for name, icon in NAV_ITEMS}


def _inject_sidebar_styles() -> None:
    """Scoped CSS for the sidebar's brand block, nav pills, and profile card."""
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

            [data-testid="stSidebar"] > div:first-child {
                padding-top: 1.2rem;
            }

            .enercore-brand {
                display: flex;
                align-items: center;
                gap: 0.65rem;
                padding: 0 0.2rem 1rem 0.2rem;
            }

            .enercore-brand-icon {
                font-family: 'Material Symbols Outlined';
                font-size: 1.7rem;
                font-weight: 400;
                filter: drop-shadow(0 2px 6px rgba(0,0,0,0.25));
            }

            .enercore-brand-name {
                font-weight: 800;
                font-size: 1.05rem;
                line-height: 1.05;
                color: #ffffff !important;
                letter-spacing: 0.01em;
            }

            .enercore-brand-tag {
                font-size: 0.65rem;
                font-weight: 600;
                letter-spacing: 0.08em;
                color: rgba(255,255,255,0.65) !important;
            }

            .enercore-pro-badge {
                margin-left: auto;
                background: rgba(79, 199, 133, 0.18);
                border: 1px solid rgba(79, 199, 133, 0.45);
                color: #d9f5e4 !important;
                font-size: 0.62rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                border-radius: 999px;
                padding: 0.18rem 0.55rem;
            }

            .enercore-nav-divider {
                border: none;
                border-top: 1px solid rgba(255,255,255,0.14);
                margin: 0.4rem 0 0.8rem 0;
            }

            /* Style the radio group as a vertical nav list */
            [data-testid="stSidebar"] div[role="radiogroup"] {
                gap: 0.15rem;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label {
                background: transparent;
                border-radius: 10px;
                padding: 0.5rem 0.6rem;
                width: 100%;
                transition: background 0.15s ease;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
                background: rgba(255,255,255,0.08);
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
                background: rgba(79, 199, 133, 0.22);
                border: 1px solid rgba(79, 199, 133, 0.4);
            }

            .enercore-profile-card {
                display: flex;
                align-items: center;
                gap: 0.7rem;
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 14px;
                padding: 0.7rem 0.8rem;
                margin-top: 0.6rem;
            }

            .enercore-avatar {
                width: 38px;
                height: 38px;
                min-width: 38px;
                border-radius: 50%;
                background: linear-gradient(135deg, #4fc785, #1c7c4f);
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 0.85rem;
                color: #ffffff !important;
            }

            .enercore-profile-name {
                font-weight: 700;
                font-size: 0.88rem;
                color: #ffffff !important;
                line-height: 1.1;
            }

            .enercore-profile-role {
                font-size: 0.72rem;
                color: rgba(255,255,255,0.65) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _initials(full_name: str) -> str:
    """Derive up to two uppercase initials from a full name."""
    parts = [p for p in full_name.strip().split(" ") if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def render_sidebar() -> str:
    """Render the full sidebar (brand, nav, profile) and return the active page name."""

    _inject_sidebar_styles()

    with st.sidebar:
        st.markdown(
            """
            <div class="enercore-brand">
                <div class="enercore-brand-icon">🔆</div>
                <div>
                    <div class="enercore-brand-name">Enercore</div>
                    <div class="enercore-brand-tag">SOLAR INTELLIGENCE</div>
                </div>
                <div class="enercore-pro-badge">PRO</div>
            </div>
            <hr class="enercore-nav-divider">
            """,
            unsafe_allow_html=True,
        )

        labels = [f"{ICON_MAP[name]}  {name}" for name, _ in NAV_ITEMS]
        names = [name for name, _ in NAV_ITEMS]

        current = st.session_state.get("active_page", NAV_ITEMS[0][0])
        default_index = names.index(current) if current in names else 0

        selected_label = st.radio(
            label="Navigation",
            options=labels,
            index=default_index,
            label_visibility="collapsed",
        )
        selected_page = names[labels.index(selected_label)]

        st.markdown('<hr class="enercore-nav-divider">', unsafe_allow_html=True)

        user = st.session_state.get("user") or {}
        full_name = user.get("full_name", "Guest User")
        role = user.get("role", "Not signed in")

        st.markdown(
            f"""
            <div class="enercore-profile-card">
                <div class="enercore-avatar">{_initials(full_name)}</div>
                <div>
                    <div class="enercore-profile-name">{full_name}</div>
                    <div class="enercore-profile-role">{role}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        if st.button("Log out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

    return selected_page