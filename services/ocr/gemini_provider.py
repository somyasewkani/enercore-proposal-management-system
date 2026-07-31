import os
import google.generativeai as genai
from typing import Dict, Any

class GeminiProvider:
    """Interfaces with Gemini 2.5 Flash to extract information from uploaded bills."""
    
    def __init__(self):
        self.model_name = "gemini-2.5-flash"
        # We fetch the API key on initialization or execution
        self.api_key = os.environ.get("GEMINI_API_KEY")

    def run_ocr(self, file_path: str) -> str:
        """Reads file bytes, determines mime-type, and executes multimodal Gemini extraction."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set. Please configure it in your environment.")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Utility bill statement file not found: {file_path}")

        # Map file extension to MIME type
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        mime_types = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg"
        }
        
        if ext not in mime_types:
            raise ValueError(f"Unsupported file format: '.{ext}'. Supported formats: PDF, PNG, JPG, JPEG")

        mime_type = mime_types[ext]

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        # Configure model client
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)

        prompt = """
You are an expert OCR utility bill parser. Extract information from the provided utility statement (particularly matching Indian electricity bills).
Produce a JSON response containing exactly the following keys. If a value is not present, set it to null. Do not guess values.

Keys to extract:
- customer_name: Full name of the customer.
- consumer_number: Consumer number or customer identifier.
- account_number: Account number or billing account ID.
- bill_number: Invoice number or statement reference ID.
- billing_month: Month of the statement (e.g. "January" or 1).
- billing_year: Year of the statement (e.g. 2026).
- billing_period_start: Start date of the billing cycle.
- billing_period_end: End date of the billing cycle.
- bill_date: Date the statement was generated.
- due_date: Payment deadline date.
- units_consumed: Total energy consumption in kWh (kilowatt-hours).
- maximum_demand: Maximum load demand measured.
- connected_load: Connected utility load.
- sanctioned_load: Sanctioned load capacity.
- contract_demand: Contracted demand capacity.
- tariff_category: Tariff class code (e.g. Commercial, Industrial, Residential, LT-II, etc.).
- discom_name: Name of the electricity distribution utility company (e.g. MSEDCL, BESCOM, TPADL, BSES Rajdhani, KSEB, PGVCL, etc.).
- meter_number: Meter identifier.
- total_amount: Total billing amount due.
- energy_charges: Pure energy charges.
- fixed_charges: Flat rate or fixed charges.
- taxes: Tax amount or utility duties.
- subsidy: Subsidy credits.
- late_fee: Surcharge penalty for late payments.
- power_factor: Measured power factor value (float between 0 and 1).

Provide ONLY a clean, valid JSON object matching these keys. Do not include markdown code block formatting (like ```json).
"""

        response = model.generate_content(
            [
                {
                    "mime_type": mime_type,
                    "data": file_bytes
                },
                prompt
            ],
            generation_config={"response_mime_type": "application/json"}
        )

        if not response or not response.text:
            raise RuntimeError("Gemini returned an empty or invalid OCR response.")

        return response.text
