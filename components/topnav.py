"""
Enercore AI Solar Proposal Generator
components/topnav.py

Reusable top navigation bar component:
- Full-width search with icon
- Notification bell with indicator
- User profile dropdown
- Page breadcrumbs

Designed to be imported by all authenticated pages.
"""

import streamlit as st


def _inject_topnav_styles() -> None:
    """CSS for the top navigation bar with glassmorphism effects."""
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

            .enercore-topnav {
                position: sticky;
                top: 0;
                z-index: 100;
                background: rgba(247, 249, 251, 0.8);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-bottom: 1px solid rgba(191, 202, 185, 0.2);
                padding: 0.75rem 2rem;
                margin-bottom: 1.5rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .enercore-search-wrapper {
                position: relative;
                flex: 1;
                max-width: 480px;
            }

            .enercore-search-icon {
                position: absolute;
                left: 14px;
                top: 50%;
                transform: translateY(-50%);
                color: #6f7a6b;
                font-family: 'Material Symbols Outlined';
                font-size: 20px;
            }

            .enercore-search-input {
                width: 100%;
                background: #ffffff;
                border: 1px solid rgba(191, 202, 185, 0.3);
                border-radius: 999px;
                padding: 0.5rem 1rem 0.5rem 2.5rem;
                font-size: 0.85rem;
                color: #191c1e;
                outline: none;
                transition: all 0.2s ease;
            }

            .enercore-search-input:focus {
                border-color: #006b1b;
                box-shadow: 0 0 0 3px rgba(0, 107, 27, 0.15);
            }

            .enercore-topnav-actions {
                display: flex;
                align-items: center;
                gap: 1rem;
            }

            .enercore-notification-btn {
                position: relative;
                width: 40px;
                height: 40px;
                border-radius: 10px;
                background: rgba(236, 238, 240, 0.5);
                border: 1px solid rgba(191, 202, 185, 0.2);
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .enercore-notification-btn:hover {
                background: rgba(236, 238, 240, 0.8);
            }

            .enercore-notification-dot {
                position: absolute;
                top: 8px;
                right: 8px;
                width: 8px;
                height: 8px;
                background: #ff8f06;
                border-radius: 50%;
                border: 2px solid #ffffff;
            }

            .enercore-user-profile {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.4rem 0.75rem;
                background: rgba(236, 238, 240, 0.5);
                border-radius: 999px;
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .enercore-user-profile:hover {
                background: rgba(236, 238, 240, 0.8);
            }

            .enercore-user-avatar {
                width: 32px;
                height: 32px;
                border-radius: 50%;
                background: linear-gradient(135deg, #268630, #006b1b);
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 0.8rem;
                color: #ffffff;
            }

            .enercore-user-info {
                display: flex;
                flex-direction: column;
                font-size: 0.85rem;
                line-height: 1.2;
            }

            .enercore-user-name {
                font-weight: 700;
                color: #191c1e;
            }

            .enercore-user-badge {
                font-size: 0.7rem;
                color: #006b1b;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.04em;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_initials(full_name: str) -> str:
    """Derive up to two uppercase initials from a full name."""
    parts = [p for p in full_name.strip().split(" ") if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def render_topnav(search_placeholder: str = "Search leads, proposals, or assets...", breadcrumbs: list[str] | None = None) -> None:
    """
    Render the top navigation bar for authenticated pages.

    Args:
        search_placeholder: Placeholder text for the search input
        breadcrumbs: Optional list of breadcrumb items (e.g., ["PROPOSALS", "BILL UPLOAD"])
    """
    _inject_topnav_styles()

    user = st.session_state.get("user", {})
    full_name = user.get("full_name", "Guest")
    initials = get_initials(full_name)

    # Breadcrumbs
    if breadcrumbs:
        breadcrumb_html = " <span style='margin: 0 0.5rem; color: #6f7a6b;'>›</span> ".join(
            f"<span style='color: {\"#006b1b\" if i == len(breadcrumbs) - 1 else \"#6f7a6b\"}; "
            f"font-weight: {\"700\" if i == len(breadcrumbs) - 1 else \"500\"};'>{b}</span>"
            for i, b in enumerate(breadcrumbs)
        )
        st.markdown(
            f"<div style='font-size: 0.75rem; color: #8f4e00; margin-bottom: 0.25rem;'>{breadcrumb_html}</div>",
            unsafe_allow_html=True,
        )

    # Top navigation row
    cols = st.columns([3, 1])

    with cols[0]:
        search_value = st.text_input(
            "Search",
            placeholder=search_placeholder,
            label_visibility="collapsed",
            key="topnav_search",
        )

    with cols[1]:
        # Notification and user profile
        notif_col, user_col = st.columns([1, 2])

        with notif_col:
            st.markdown(
                """
                <div class="enercore-notification-btn" style="margin-top: 0.25rem;">
                    <span class="enercore-search-icon">notifications</span>
                    <div class="enercore-notification-dot"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with user_col:
            st.markdown(
                f"""
                <div class="enercore-user-profile" style="margin-top: 0.25rem;">
                    <span class="enercore-search-icon" style="position: static; transform: none; color: #006b1b; font-size: 20px;">
                        person
                    </span>
                    <div class="enercore-user-info">
                        <span class="enercore-user-name">{full_name}</span>
                        <span class="enercore-user-badge">PRO ACCOUNT</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )