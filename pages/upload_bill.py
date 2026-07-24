"""
Enercore AI Solar Proposal Generator
pages/upload_bill.py

Step 1 of the New Proposal wizard: upload a customer's electricity bill
and preview the extracted usage data. OCR/bill-parsing is not connected
yet, so extraction results shown here are placeholder data returned by
_extract_bill_data(). Swap that function for a real parser/service call
once available (e.g. services/bill_parser_service.py).
"""

import streamlit as st

from components.cards import glass_card, inject_card_styles, status_pill

# --------------------------------------------------------------------------- #
# Placeholder "extracted" bill data (to be replaced by a real OCR/parser service)
# --------------------------------------------------------------------------- #
def _extract_bill_data(filename: str) -> dict:
    """Return placeholder extraction results for an uploaded bill file.

    TODO: replace with a call into services/bill_parser_service.py that
    runs OCR + parsing against the uploaded file and returns real values.
    """
    return {
        "utility_provider": "Pacific Coast Energy Co.",
        "account_number": "PCE-88213-4471",
        "billing_period": "Sep 12 – Oct 11, 2023",
        "avg_monthly_usage_kwh": 1180,
        "avg_monthly_bill": "$214.60",
        "rate_per_kwh": "$0.182",
        "service_address": "4821 Meadow Ridge Dr, Sacramento, CA",
        "source_file": filename,
    }


def render_upload_bill() -> None:
    """Render the upload-bill step. Advances the wizard on successful upload + confirm."""
    inject_card_styles()

    with glass_card():
        st.markdown(
            """
            <style>
                .upload-dashed {
                    background-image: url("data:image/svg+xml,%3csvg width='100%25' height='100%25' xmlns='http://www.w3.org/2000/svg'%3e%3crect width='100%25' height='100%25' fill='none' rx='16' ry='16' stroke='%23BFCCB9' stroke-width='2' stroke-dasharray='12%2c 12' stroke-dashoffset='0' stroke-linecap='square'/%3e%3c/svg%3e");
                    border-radius: 16px;
                }
                .upload-dashed:hover {
                    background-image: url("data:image/svg+xml,%3csvg width='100%25' height='100%25' xmlns='http://www.w3.org/2000/svg'%3e%3crect width='100%25' height='100%25' fill='none' rx='16' ry='16' stroke='%23006B1B' stroke-width='2' stroke-dasharray='12%2c 12' stroke-dashoffset='0' stroke-linecap='square'/%3e%3c/svg%3e");
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "Upload utility bills (PDF, JPG, or PNG)",
            type=["pdf", "jpg", "jpeg", "png"],
        )

        if uploaded_file is not None:
            st.session_state.uploaded_bill_name = uploaded_file.name
            st.session_state.extracted_bill_data = _extract_bill_data(uploaded_file.name)

        if st.session_state.get("extracted_bill_data"):
            data = st.session_state.extracted_bill_data
            st.success(f"Bill processed: {data['source_file']}")

            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f"""
                    **Utility Provider**
                    {data['utility_provider']}

                    **Account Number**
                    {data['account_number']}

                    **Service Address**
                    {data['service_address']}
                    """
                )
            with col2:
                st.markdown(
                    f"""
                    **Billing Period**
                    {data['billing_period']}

                    **Avg. Monthly Usage**
                    {data['avg_monthly_usage_kwh']:,} kWh

                    **Avg. Monthly Bill**
                    {data['avg_monthly_bill']} &nbsp; ({data['rate_per_kwh']} / kWh)
                    """
                )

            st.markdown(
                f'<div style="margin-top:0.6rem;">{status_pill("Data extracted", "success")}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("No bill uploaded yet. Accepted formats: PDF, JPG, PNG.")

    st.write("")

    # Instructions section
    with glass_card():
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:1rem;">
                <span style="font-size:20px;">ℹ️</span>
                <h3 style="font-weight:700; font-size:1.2rem; color:#191c1e; margin:0;">Sales Representative Instructions</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                """
                <ol style="padding-left:1.2rem; margin:0;">
                    <li style="margin-bottom:0.75rem;">
                        <strong style="color:#191c1e;">Verify Full Year</strong>
                        <br><span style="font-size:0.85rem; color:#3f4a3d;">Ensure the bill includes a 12-month historical consumption chart for accurate ROI.</span>
                    </li>
                    <li style="margin-bottom:0.75rem;">
                        <strong style="color:#191c1e;">Check Quality</strong>
                        <br><span style="font-size:0.85rem; color:#3f4a3d;">Avoid blurry photos. Ensure account numbers and tariff names are clearly visible.</span>
                    </li>
                </ol>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                """
                <ol start="3" style="padding-left:1.2rem; margin:0;">
                    <li style="margin-bottom:0.75rem;">
                        <strong style="color:#191c1e;">Data Privacy</strong>
                        <br><span style="font-size:0.85rem; color:#3f4a3d;">Inform clients their data is encrypted and used only for energy analysis.</span>
                    </li>
                    <li>
                        <strong style="color:#191c1e;">Tariff Detail</strong>
                        <br><span style="font-size:0.85rem; color:#3f4a3d;">If the bill shows "Demand Charges," upload all pages of the statement.</span>
                    </li>
                </ol>
                """,
                unsafe_allow_html=True,
            )

    st.write("")

    # Summary and financials section
    col1, col2 = st.columns(2)

    with col1:
        with glass_card():
            st.markdown(
                """
                <h3 style="font-weight:700; font-size:1.1rem; color:#191c1e; margin-bottom:0.75rem;">Consumption Preview</h3>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <table style="width:100%; border-collapse:collapse;">
                    <thead>
                        <tr style="border-bottom:1px solid rgba(191,202,185,0.3);">
                            <th style="text-align:left; font-size:0.7rem; font-weight:700; color:#6f7a6b; text-transform:uppercase; padding:0.5rem;">Month</th>
                            <th style="text-align:right; font-size:0.7rem; font-weight:700; color:#6f7a6b; text-transform:uppercase; padding:0.5rem;">Usage (kWh)</th>
                            <th style="text-align:right; font-size:0.7rem; font-weight:700; color:#6f7a6b; text-transform:uppercase; padding:0.5rem;">Cost ($)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border-bottom:1px solid rgba(191,202,185,0.1);">
                            <td style="padding:0.5rem; font-size:0.85rem; color:#191c1e;">January</td>
                            <td style="padding:0.5rem; text-align:right; font-size:0.85rem;">1,650</td>
                            <td style="padding:0.5rem; text-align:right; font-size:0.85rem; font-weight:600;">$528.00</td>
                        </tr>
                        <tr style="border-bottom:1px solid rgba(191,202,185,0.1);">
                            <td style="padding:0.5rem; font-size:0.85rem; color:#191c1e;">February</td>
                            <td style="padding:0.5rem; text-align:right; font-size:0.85rem;">1,480</td>
                            <td style="padding:0.5rem; text-align:right; font-size:0.85rem; font-weight:600;">$473.60</td>
                        </tr>
                        <tr style="border-bottom:1px solid rgba(191,202,185,0.1);">
                            <td style="padding:0.5rem; font-size:0.85rem; color:#191c1e;">March</td>
                            <td style="padding:0.5rem; text-align:right; font-size:0.85rem;">1,320</td>
                            <td style="padding:0.5rem; text-align:right; font-size:0.85rem; font-weight:600;">$422.40</td>
                        </tr>
                        <tr style="background:rgba(0,107,27,0.05); border-left:4px solid #006b1b;">
                            <td colspan="3" style="padding:0.5rem; font-size:0.85rem; font-style:italic;">... 9 more months extracted</td>
                        </tr>
                    </tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )

            st.write("")
            if st.button("Start AI Analysis", use_container_width=True, type="primary"):
                st.info("Analysis will be performed once the AI service is connected.")

    with col2:
        with glass_card():
            st.markdown(
                """
                <h3 style="font-weight:700; font-size:1.1rem; color:#191c1e; margin-bottom:0.75rem;">Quick Summary</h3>
                """,
                unsafe_allow_html=True,
            )

            stat_col1, stat_col2 = st.columns(2)
            with stat_col1:
                st.markdown(
                    """
                    <div style="border-left:4px solid #005ea4; padding-left:0.75rem;">
                        <div style="font-size:0.75rem; color:#6f7a6b; text-transform:uppercase;">Average Usage</div>
                        <div style="font-size:1.8rem; font-weight:700; color:#191c1e;">1,420 kWh/mo</div>
                        <div style="font-size:0.75rem; color:#006b1b;">↑ 4% vs region</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with stat_col2:
                st.markdown(
                    """
                    <div style="border-left:4px solid #ff8f06; padding-left:0.75rem;">
                        <div style="font-size:0.75rem; color:#6f7a6b; text-transform:uppercase;">Tariff Est.</div>
                        <div style="font-size:1.8rem; font-weight:700; color:#191c1e;">$0.32 / kWh</div>
                        <div style="font-size:0.75rem; color:#ff8f06;">Tier 2 Pricing</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )