"""
Enercore AI Solar Proposal Generator
Main application entry point.

Handles:
- Global page configuration
- Global theming (CSS injection)
- Session state initialization
- Auth gate (routes to login if not authenticated)
- Sidebar navigation and page routing for authenticated users
"""

import streamlit as st

from pages.login import render_login
from pages.dashboard import render_dashboard
from pages.customers import render_customers
from pages.proposal import render_proposal
from pages.reports import render_reports
from pages.settings import render_settings
from pages.pipeline import render_pipeline
from pages.proposal_history import render_proposal_history
from pages.analysis import render_analysis
from components.sidebar import render_sidebar


# --------------------------------------------------------------------------- #
# Page configuration (must be the first Streamlit call)
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Enercore | AI Solar Proposal Generator",
    page_icon="🔆",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------- #
# Global theme injection
# --------------------------------------------------------------------------- #
def load_global_styles() -> None:
    """Inject the global CSS theme: green & white enterprise + glassmorphism."""
    st.markdown(
        """
        <style>
            :root {
                --enercore-green-900: #0b3d2e;
                --enercore-green-700: #14532d;
                --enercore-green-600: #1c7c4f;
                --enercore-green-500: #2fa66a;
                --enercore-green-400: #4fc785;
                --enercore-green-100: #e6f5ec;
                --enercore-white: #ffffff;
                --enercore-off-white: #f6f9f7;
                --enercore-ink: #10241d;
                --enercore-muted: #5b7267;
                --enercore-border: rgba(20, 83, 45, 0.12);
                --enercore-shadow: rgba(11, 61, 46, 0.12);
                --enercore-glass-bg: rgba(255, 255, 255, 0.55);
                --enercore-glass-border: rgba(255, 255, 255, 0.35);
            }

            html, body, [class*="css"] {
                font-family: "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
                color: var(--enercore-ink);
            }

            /* App background */
            [data-testid="stAppViewContainer"] {
                background: radial-gradient(circle at 15% 0%, #eefaf2 0%, var(--enercore-off-white) 45%, #ffffff 100%);
            }

            [data-testid="stHeader"] {
                background: rgba(255, 255, 255, 0);
            }

            /* Sidebar base surface (nav-specific styling lives in components/sidebar.py) */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, var(--enercore-green-900) 0%, var(--enercore-green-700) 55%, #0f4a35 100%);
                border-right: 1px solid var(--enercore-border);
            }

            [data-testid="stSidebar"] * {
                color: #eef7f1 !important;
            }

            [data-testid="stSidebar"] hr {
                border-color: rgba(255, 255, 255, 0.15);
            }

            /* Glassmorphism card utility */
            .enercore-card {
                background: var(--enercore-glass-bg);
                border: 1px solid var(--enercore-glass-border);
                border-radius: 18px;
                padding: 1.75rem 1.75rem;
                backdrop-filter: blur(14px);
                -webkit-backdrop-filter: blur(14px);
                box-shadow: 0 8px 30px var(--enercore-shadow);
            }

            /* Buttons */
            div.stButton > button {
                background: linear-gradient(135deg, var(--enercore-green-600), var(--enercore-green-500));
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 0.6rem 1.4rem;
                font-weight: 600;
                letter-spacing: 0.01em;
                box-shadow: 0 6px 16px var(--enercore-shadow);
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }

            div.stButton > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 10px 22px var(--enercore-shadow);
                color: #ffffff;
            }

            /* Inputs */
            div[data-baseweb="input"] > div,
            div[data-baseweb="select"] > div,
            textarea {
                border-radius: 10px !important;
                border: 1px solid var(--enercore-border) !important;
                background: rgba(255, 255, 255, 0.75) !important;
            }

            /* Headings */
            h1, h2, h3 {
                color: var(--enercore-green-900);
                font-weight: 700;
            }

            .enercore-subtitle {
                color: var(--enercore-muted);
                font-size: 0.95rem;
            }

            /* Hide default Streamlit chrome for a cleaner enterprise feel */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Session state initialization
# --------------------------------------------------------------------------- #
def init_session_state() -> None:
    """Ensure all required session state keys exist with safe defaults."""
    defaults = {
        "authenticated": False,
        "user": None,
        "active_page": "Dashboard",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# --------------------------------------------------------------------------- #
# Placeholder page renderer (real pages will be added module-by-module)
# --------------------------------------------------------------------------- #
def render_placeholder_page(page_name: str) -> None:
    """Render a placeholder body for pages not yet implemented as modules."""
    st.markdown(f"## {page_name}")
    st.markdown(
        '<p class="enercore-subtitle">This module is under construction. '
        "Placeholder content is shown until the backend and UI are connected.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="enercore-card">
            <h4 style="margin-top:0;">Coming soon</h4>
            <p style="color:#5b7267; margin-bottom:0;">
                This section will be built out in a later step of the project.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    load_global_styles()
    init_session_state()

    if not st.session_state.authenticated:
        render_login()
        return

    selected_page = render_sidebar()
    st.session_state.active_page = selected_page

    if selected_page == "Dashboard":
        render_dashboard()
    elif selected_page == "Clients":
        render_customers()
    elif selected_page == "New Proposal":
        render_proposal()
    elif selected_page == "Analytics":
        render_reports()
    elif selected_page == "Settings":
        render_settings()
    elif selected_page == "Pipeline":
        render_pipeline()
    elif selected_page == "Analysis":
        render_analysis()
    elif selected_page == "Proposal History":
        render_proposal_history()
    else:
        render_placeholder_page(selected_page)


if __name__ == "__main__":
    main()