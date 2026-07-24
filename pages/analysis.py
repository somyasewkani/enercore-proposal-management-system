"""
Enercore AI Solar Proposal Generator
pages/analysis.py

Solar Analysis page: ROI calculator, 25-year performance projections,
environmental impact metrics, and business model evaluation. All data is
placeholder until services/analysis_service.py is connected.
"""

import plotly.graph_objects as go
import streamlit as st

from components.cards import glass_card, inject_card_styles, kpi_card
from components.chatbot import render_chatbot
from components.topnav import render_topnav


def _render_header() -> None:
    """Render the page header."""
    st.markdown(
        """
        <span style="color:#1c7c4f; font-weight:700; font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase;">Pipeline</span>
        <div style="font-weight:700; font-size:1.5rem; color:#0b3d2e; margin-bottom:0.1rem;">AI Solar Performance Analysis</div>
        <div style="font-size:0.85rem; color:#5b7267; margin-bottom:1rem;">Feasibility and ROI results for Site: North-Western Industrial Hub.</div>
        """,
        unsafe_allow_html=True,
    )

    nav_col, action_col = st.columns([1.5, 1])
    with action_col:
        st.button("⬇ Export Data", use_container_width=True)

    with st.columns(1)[0]:
        st.button("Generate Final Proposal →", use_container_width=True, type="primary")


def _render_hero_card() -> None:
    """Render the recommended plant size card."""
    with glass_card():
        st.markdown(
            """
            <span style="background:#e6f5ec; color:#006b1b; padding:4px 12px; border-radius:999px; font-size:12px; font-weight:700;">AI OPTIMIZED SIZE</span>
            <h3 style="font-size:18px; color:#3f4a3d; margin-top:0.5rem;">Recommended Plant Size</h3>
            <div style="margin-top:1rem;">
                <span style="font-size:60px; font-weight:800; color:#006b1b; line-height:1;">250</span>
                <span style="font-size:32px; color:#191c1e;"> kWp</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(
                '<div style="font-size:14px; color:#5b7267;">Daily Average Yield</div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                '<span style="font-size:24px; font-weight:700; color:#191c1e;">1,125 kWh</span>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div style="width:100%; background:#e6e8ea; height:8px; border-radius:999px; margin:1rem 0;"><div style="width:75%; background:#006b1b; height:8px; border-radius:999px;"></div></div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<p style="font-size:11px; color:#6f7a6b; font-style:italic;">Based on 10 years of solar irradiation data for this coordinate.</p>',
            unsafe_allow_html=True,
        )


def _render_financial_analysis() -> None:
    """Render the financial analysis/ROI card."""
    with glass_card():
        st.markdown(
            """
            <div style="font-weight:700; font-size:20px; color:#0b3d2e; margin-bottom:0.5rem;">Financial Analysis (ROI)</div>
            <div style="font-size:13px; color:#5b7267; margin-bottom:1rem;">Project financial returns and savings projection</div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                """
                <div style="font-size:14px; color:#3f4a3d; margin-bottom:0.25rem;">Est. Annual Savings</div>
                <div style="font-size:28px; font-weight:700; color:#ff8f06;">$42,500</div>
                <p style="font-size:12px; color:#006b1b; margin-top:0.25rem; font-weight:600;">↑ 12% vs Local Grid</p>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                """
                <div style="border-left:1px solid #e6e8ea; border-right:1px solid #e6e8ea; padding:0 2rem; font-size:14px; color:#3f4a3d; margin-bottom:0.25rem;">Payback Period</div>
                <div style="font-size:28px; font-weight:700; color:#191c1e;">3.8 Years</div>
                <p style="font-size:12px; color:#5b7267; margin-top:0.25rem; font-style:italic;">Accelerated depreciation included</p>
                """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                """
                <div style="font-size:14px; color:#3f4a3d; margin-bottom:0.25rem;">Project IRR</div>
                <div style="font-size:28px; font-weight:700; color:#005ea4;">24.6%</div>
                <p style="font-size:12px; color:#5b7267; margin-top:0.25rem; font-weight:600;">Risk-Adjusted Index</p>
                """,
                unsafe_allow_html=True,
            )


def _render_performance_chart() -> None:
    """Render the 25-year performance chart using Plotly."""
    with glass_card():
        st.markdown(
            """
            <div style="font-weight:700; font-size:20px; color:#0b3d2e; margin-bottom:0.5rem;">25-Year Performance & Generation Curve</div>
            """,
            unsafe_allow_html=True,
        )

        # Create sample data for 25 years
        years = list(range(0, 26))
        optimized_yield = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 85, 85, 85, 85, 85, 85, 85, 85, 85, 85]
        standard_yield = [100, 95, 92, 89, 87, 85, 84, 82, 81, 79, 78, 77, 76, 75, 74, 73, 72, 71, 70, 69, 68, 67, 66, 65, 64, 63]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=optimized_yield,
            mode='lines',
            name='Optimized Yield',
            line=dict(color='#006b1b', width=3),
            fill='tozeroy',
            fillcolor='rgba(0, 107, 27, 0.1)',
        ))
        fig.add_trace(go.Scatter(
            x=years, y=standard_yield,
            mode='lines',
            name='Standard Panel',
            line=dict(color='#bfcab9', width=2, dash='dash'),
        ))

        fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Performance (%)",
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#191c1e', size=12),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='left',
                x=0,
            ),
        )
        fig.update_xaxes(gridcolor='rgba(0,0,0,0.05)')
        fig.update_yaxes(gridcolor='rgba(0,0,0,0.05)')

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_environmental_impact() -> None:
    """Render the environmental impact card."""
    with glass_card():
        st.markdown(
            """
            <div style="font-weight:700; font-size:20px; color:#0b3d2e; margin-bottom:1rem;">Environmental Footprint</div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                """
                <div style="display:flex; align-items:center; gap:1.5rem;">
                    <div style="width:64px; height:64px; border-radius:16px; background:rgba(0, 94, 164, 0.1); display:flex; align-items:center; justify-content:center;">
                        <span style="font-size:48px; color:#005ea4;">🌍</span>
                    </div>
                    <div>
                        <p style="font-size:12px; color:#3f4a3d; font-weight:600;">Carbon Reduction</p>
                        <p style="font-size:32px; font-weight:700; color:#0b3d2e;">320 Tons / Year</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                """
                <div style="display:flex; align-items:center; gap:1.5rem;">
                    <div style="width:64px; height:64px; border-radius:16px; background:rgba(0, 107, 27, 0.1); display:flex; align-items:center; justify-content:center;">
                        <span style="font-size:48px; color:#006b1b;">🌳</span>
                    </div>
                    <div>
                        <p style="font-size:12px; color:#3f4a3d; font-weight:600;">Equivalent Trees Planted</p>
                        <p style="font-size:32px; font-weight:700; color:#006b1b;">15,400 Trees</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div style="margin-top:1.5rem; background:rgba(230, 238, 240, 0.4); padding:1rem 1.5rem; border-radius:12px; display:flex; align-items:center; gap:0.75rem;">
                <span style="font-size:20px; color:#ff8f06;">✓</span>
                <p style="font-size:13px; color:#3f4a3d; margin:0;">This data is certified under the Global ESG Framework V2.0 for sustainability reporting.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_model_evaluation() -> None:
    """Render the business model evaluation cards."""
    with glass_card():
        st.markdown(
            """
            <div style="font-weight:700; font-size:20px; color:#0b3d2e; margin-bottom:1rem;">Model Suitability Evaluation</div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)

        models = [
            {"name": "CAPEX", "desc": "Highest long-term savings but requires upfront liquidity", "score": 95, "recommended": True},
            {"name": "OPEX / PPA", "desc": "Immediate savings without investment risk", "score": 70},
            {"name": "Open Access", "desc": "Best for remote generation with complex grid policy", "score": 45},
        ]

        for col, model in zip([col1, col2, col3], models):
            with col:
                st.markdown(
                    f"""
                    <div style="border:1px solid rgba(11,61,46,0.15); border-radius:12px; padding:1.5rem; background:rgba(242,244,246,0.5);">
                        <div style="display:flex; justify-content:space-between; margin-bottom:1rem;">
                            <span style="font-size:14px; font-weight:600; color:#3f4a3d;">{model["name"]}</span>
                            <span style="font-size:20px; color:#006b1b;">{"★" if model.get("recommended") else "→"}</span>
                        </div>
                        <p style="font-size:16px; font-weight:700; color:#0b3d2e; margin-bottom:0.5rem;">{"High Yield" if model["name"] == "CAPEX" else "Zero Capital" if model["name"] == "OPEX / PPA" else "Multi-Site"}</p>
                        <p style="font-size:13px; color:#5b7267; margin-bottom:1rem;">{model["desc"]}</p>
                        <div style="background:#e6e8ea; height:6px; border-radius:999px;"><div style="background:#006b1b; height:6px; border-radius:999px; width:{model["score"]}%"></div></div>
                        <p style="font-size:11px; margin-top:0.5rem; font-weight:600; color:#006b1b;">RECOMMENDED (Score {model["score"]}/100)</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_analysis() -> None:
    """Render the full Solar Analysis page."""
    inject_card_styles()

    # Top navigation bar
    render_topnav(search_placeholder="Search projects or clients...", breadcrumbs=["Pipeline", "Project Phoenix", "Analysis Results"])

    _render_header()
    st.write("")

    # Bento grid layout
    col1, col2 = st.columns([1, 2])

    with col1:
        _render_hero_card()

    with col2:
        _render_financial_analysis()

    st.write("")

    col1, col2 = st.columns([2, 1])

    with col1:
        _render_performance_chart()

    with col2:
        _render_environmental_impact()

    st.write("")
    _render_model_evaluation()

    # Floating AI Chatbot
    render_chatbot()