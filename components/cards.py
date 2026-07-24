"""
Enercore AI Solar Proposal Generator
components/cards.py

Reusable glassmorphism UI building blocks shared across pages:
- glass_card()      : generic container context manager
- kpi_card()         : metric summary tile
- status_pill()      : inline colored status label (html string)
- render_status_pill(): status_pill(), rendered directly
- client_card()      : client/customer summary tile
- empty_state()      : placeholder for empty lists/tables

Import these instead of re-writing card markup + CSS in every page.
"""

from contextlib import contextmanager

import streamlit as st

STATUS_TONES = {
    "success": ("#e6f5ec", "#14532d"),
    "warning": ("#fff4e5", "#b06a00"),
    "info": ("#eaf1ff", "#2456c9"),
    "neutral": ("#eef1ef", "#5b7267"),
    "danger": ("#fdecea", "#b3261e"),
}


def inject_card_styles() -> None:
    """CSS shared by every card component in this module. Safe to call multiple times."""
    st.markdown(
        """
        <style>
            .enercore-card {
                background: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 16px;
                padding: 1.1rem 1.2rem;
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                box-shadow: 0 6px 20px rgba(11, 61, 46, 0.10);
            }

            .enercore-stats-card {
                background: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 16px;
                padding: 1.5rem 1.25rem;
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                box-shadow: 0 6px 20px rgba(11, 61, 46, 0.10);
            }

            .enercore-deal-card {
                background: rgba(255, 255, 255, 0.62);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 16px;
                padding: 1.25rem;
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                box-shadow: 0 6px 18px rgba(11, 61, 46, 0.09);
                margin-bottom: 1rem;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }

            .enercore-deal-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 24px rgba(11, 61, 46, 0.14);
            }

            .enercore-kpi-icon {
                width: 34px;
                height: 34px;
                border-radius: 10px;
                background: rgba(28, 124, 79, 0.12);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1rem;
                margin-bottom: 0.5rem;
            }

            .enercore-kpi-label {
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                color: #5b7267;
            }

            .enercore-kpi-value {
                font-size: 1.55rem;
                font-weight: 800;
                color: #0b3d2e;
                line-height: 1.15;
            }

            .enercore-kpi-delta-up {
                display: inline-block;
                margin-top: 0.3rem;
                font-size: 0.72rem;
                font-weight: 700;
                color: #1c7c4f;
                background: rgba(28, 124, 79, 0.10);
                border-radius: 999px;
                padding: 0.1rem 0.55rem;
            }

            .enercore-kpi-delta-neutral {
                display: inline-block;
                margin-top: 0.3rem;
                font-size: 0.72rem;
                font-weight: 700;
                color: #5b7267;
                background: rgba(91, 114, 103, 0.10);
                border-radius: 999px;
                padding: 0.1rem 0.55rem;
            }

            .enercore-status-pill {
                display: inline-block;
                font-size: 0.72rem;
                font-weight: 700;
                border-radius: 999px;
                padding: 0.15rem 0.65rem;
            }

            .enercore-client-card {
                background: rgba(255, 255, 255, 0.62);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 16px;
                padding: 1rem 1.1rem;
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                box-shadow: 0 6px 18px rgba(11, 61, 46, 0.09);
                margin-bottom: 0.9rem;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }

            .enercore-client-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 24px rgba(11, 61, 46, 0.14);
            }

            .enercore-client-header {
                display: flex;
                align-items: center;
                gap: 0.65rem;
                margin-bottom: 0.6rem;
            }

            .enercore-client-avatar {
                width: 40px;
                height: 40px;
                min-width: 40px;
                border-radius: 12px;
                background: linear-gradient(135deg, #4fc785, #1c7c4f);
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 0.85rem;
                color: #ffffff;
            }

            .enercore-client-name {
                font-weight: 700;
                font-size: 0.92rem;
                color: #10241d;
                line-height: 1.15;
            }

            .enercore-client-segment {
                font-size: 0.75rem;
                color: #5b7267;
            }

            .enercore-client-meta-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.78rem;
                color: #5b7267;
                margin-top: 0.35rem;
            }

            .enercore-client-value {
                font-weight: 700;
                color: #0b3d2e;
                font-size: 0.95rem;
            }

            .enercore-empty-state {
                text-align: center;
                padding: 2.4rem 1rem;
                color: #5b7267;
            }

            .enercore-empty-state-icon {
                font-size: 2.2rem;
                margin-bottom: 0.6rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def glass_card():
    """Context manager that wraps arbitrary Streamlit content in a glass card.

    Usage:
        with glass_card():
            st.markdown("### Title")
            st.write("Body content rendered inside the glass card.")
    """
    st.markdown('<div class="enercore-card">', unsafe_allow_html=True)
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str | None = None, icon: str = "📊", tone: str = "neutral") -> None:
    """Render a single KPI summary tile (icon, label, value, optional delta badge)."""
    delta_class = "enercore-kpi-delta-up" if tone == "up" else "enercore-kpi-delta-neutral"
    delta_html = f'<div class="{delta_class}">{delta}</div>' if delta else ""
    st.markdown(
        f"""
        <div class="enercore-card">
            <div class="enercore-kpi-icon">{icon}</div>
            <div class="enercore-kpi-label">{label}</div>
            <div class="enercore-kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(label: str, tone: str = "neutral") -> str:
    """Return an inline HTML snippet for a colored status pill (for embedding in f-strings)."""
    bg, fg = STATUS_TONES.get(tone, STATUS_TONES["neutral"])
    return f'<span class="enercore-status-pill" style="background:{bg}; color:{fg};">{label}</span>'


def render_status_pill(label: str, tone: str = "neutral") -> None:
    """Render a status pill directly (when not embedding inside a larger block)."""
    st.markdown(status_pill(label, tone), unsafe_allow_html=True)


def _initials(name: str) -> str:
    parts = [p for p in name.strip().split(" ") if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def client_card(
    name: str,
    segment: str,
    value: str,
    status_label: str,
    status_tone: str = "neutral",
    contact: str | None = None,
) -> None:
    """Render a single client/customer summary card."""
    contact_html = (
        f'<div style="font-size:0.78rem; color:#5b7267; margin-top:0.3rem;">✉️ {contact}</div>'
        if contact
        else ""
    )
    st.markdown(
        f"""
        <div class="enercore-client-card">
            <div class="enercore-client-header">
                <div class="enercore-client-avatar">{_initials(name)}</div>
                <div>
                    <div class="enercore-client-name">{name}</div>
                    <div class="enercore-client-segment">{segment}</div>
                </div>
            </div>
            <div class="enercore-client-meta-row">
                <span class="enercore-client-value">{value}</span>
                {status_pill(status_label, status_tone)}
            </div>
            {contact_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, message: str) -> None:
    """Render a friendly empty-state placeholder for empty lists/tables/filters."""
    st.markdown(
        f"""
        <div class="enercore-empty-state">
            <div class="enercore-empty-state-icon">{icon}</div>
            <div style="font-weight:700; color:#10241d; margin-bottom:0.3rem;">{title}</div>
            <div style="font-size:0.85rem;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )