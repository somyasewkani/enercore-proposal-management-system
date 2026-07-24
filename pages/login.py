"""
Enercore AI Solar Proposal Generator
Login page.

Renders a full-bleed, premium glassmorphism login screen. Authentication is
currently backed by placeholder credentials until the database/auth service
is connected (see services/auth_service.py in a later step).
"""

import streamlit as st

# --------------------------------------------------------------------------- #
# Placeholder user store (to be replaced by database/services layer)
# --------------------------------------------------------------------------- #
_PLACEHOLDER_USERS = {
    "admin@enercore.ai": {
        "password": "Enercore@123",
        "full_name": "Ava Whitfield",
        "role": "Solar Proposal Admin",
    },
    "sales@enercore.ai": {
        "password": "Solar@2026",
        "full_name": "Marcus Lee",
        "role": "Sales Engineer",
    },
}


def _authenticate(email: str, password: str) -> dict | None:
    """Validate credentials against the placeholder user store.

    Returns the matching user record on success, otherwise None.
    This will be swapped for services/auth_service.py once the
    database layer is connected.
    """
    user = _PLACEHOLDER_USERS.get(email.strip().lower())
    if user and user["password"] == password:
        return {"email": email.strip().lower(), **user}
    return None


def _inject_login_styles() -> None:
    """Scoped CSS for the login screen only — full-bleed backdrop + glass card."""
    st.markdown(
        """
        <style>
            [data-testid="stAppViewContainer"] {
                background:
                    radial-gradient(circle at 8% 8%, rgba(79, 199, 133, 0.35), transparent 40%),
                    radial-gradient(circle at 92% 88%, rgba(47, 166, 106, 0.30), transparent 45%),
                    repeating-linear-gradient(
                        115deg,
                        rgba(255, 255, 255, 0.05) 0px,
                        rgba(255, 255, 255, 0.05) 2px,
                        transparent 2px,
                        transparent 34px
                    ),
                    linear-gradient(160deg, #06251b 0%, #0b3d2e 38%, #14532d 68%, #1c7c4f 100%);
                background-attachment: fixed;
            }

            [data-testid="stSidebar"] { display: none; }
            [data-testid="stHeader"] { background: rgba(0,0,0,0); }

            .enercore-login-shell { padding-top: 4.5vh; }

            .enercore-login-card {
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(255, 255, 255, 0.55);
                border-radius: 22px;
                padding: 2.4rem 2.4rem 1.8rem 2.4rem;
                backdrop-filter: blur(18px);
                -webkit-backdrop-filter: blur(18px);
                box-shadow: 0 25px 60px rgba(6, 37, 27, 0.45);
            }

            .enercore-login-badge {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                background: rgba(20, 83, 45, 0.08);
                border: 1px solid rgba(20, 83, 45, 0.15);
                border-radius: 999px;
                padding: 0.3rem 0.8rem;
                font-size: 0.72rem;
                font-weight: 600;
                letter-spacing: 0.06em;
                color: #14532d;
                text-transform: uppercase;
            }

            .enercore-login-title {
                font-size: 1.7rem;
                font-weight: 800;
                color: #0b3d2e;
                margin: 0.6rem 0 0.15rem 0;
                line-height: 1.2;
            }

            .enercore-login-subtitle {
                color: #5b7267;
                font-size: 0.9rem;
                margin-bottom: 1.4rem;
            }

            .enercore-field-label {
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                color: #3f5a4e;
                text-transform: uppercase;
                margin-bottom: 0.15rem;
            }

            .enercore-login-footer {
                text-align: center;
                font-size: 0.78rem;
                color: rgba(255,255,255,0.75);
                margin-top: 1.6rem;
            }

            div.stButton > button[kind="secondary"] {
                background: #ffffff !important;
                color: #14532d !important;
                border: 1px solid rgba(20, 83, 45, 0.2) !important;
                box-shadow: none !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_login() -> None:
    """Render the login screen and handle the auth form submission."""

    _inject_login_styles()

    st.markdown('<div class="enercore-login-shell">', unsafe_allow_html=True)
    left, center, right = st.columns([1, 1.15, 1])

    with center:
        st.markdown('<div class="enercore-login-card">', unsafe_allow_html=True)

        st.markdown(
            """
            <span class="enercore-login-badge">🔆 Enercore Group</span>
            <div class="enercore-login-title">Welcome to the<br>Enercore Portal</div>
            <div class="enercore-login-subtitle">Sign in to access your solar intelligence workspace.</div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            st.markdown(
                '<div class="enercore-field-label">✉️ Email address</div>',
                unsafe_allow_html=True,
            )
            email = st.text_input(
                "Email address",
                placeholder="name@company.com",
                label_visibility="collapsed",
            )

            top_row_a, top_row_b = st.columns([1, 1])
            with top_row_a:
                st.markdown(
                    '<div class="enercore-field-label">🔒 Password</div>',
                    unsafe_allow_html=True,
                )
            with top_row_b:
                st.markdown(
                    '<div style="text-align:right;">'
                    '<a href="#" style="color:#1c7c4f; font-size:0.78rem; font-weight:600; text-decoration:none;">'
                    "Forgot password?</a></div>",
                    unsafe_allow_html=True,
                )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••",
                label_visibility="collapsed",
            )

            remember_me = st.checkbox("Keep me logged in", value=True)

            submitted = st.form_submit_button(
                "Login to Portal  →", use_container_width=True
            )

        google_clicked = st.button(
            "🔵 Sign in with Google",
            use_container_width=True,
            type="secondary",
        )

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                user = _authenticate(email, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.session_state.remember_me = remember_me
                    st.success(f"Welcome, {user['full_name']}!")
                    st.rerun()
                else:
                    st.error("Invalid email or password. Please try again.")

        if google_clicked:
            st.info("Google SSO is not connected yet. Use the demo credentials below.")

        st.markdown(
            '<p style="text-align:center; font-size:0.76rem; color:#5b7267; '
            'margin-top:1rem; margin-bottom:0;">'
            "Demo access — admin@enercore.ai / Enercore@123</p>",
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            '<p class="enercore-login-footer">⚡ Powered by Enercore AI &nbsp;·&nbsp; '
            "Enterprise Solar Intelligence Suite</p>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)