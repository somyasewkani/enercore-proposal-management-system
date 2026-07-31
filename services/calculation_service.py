import json
import sqlite3
from typing import Dict, Any, List, Tuple, Optional
from database.connection import get_connection
from services.proposal_service import get_bill_details, log_site_activity

def run_solar_calculations(bill_id: str, actor: str = "System") -> Tuple[bool, List[str]]:
    """Loads bill details and latest OCR outputs, executes solar feasibility, and stores result."""
    bill = get_bill_details(bill_id)
    if not bill:
        return False, ["Utility bill statement not found."]
    
    site_id = bill["site_id"]
    
    # 1. Validation Checks
    if bill.get("ocr_status") != "Completed":
        return False, ["OCR extraction is not completed for this bill. Please run OCR analysis first."]

    # Load normalized OCR JSON
    ocr_json_str = bill.get("normalized_json")
    if not ocr_json_str:
        return False, ["No extracted OCR data found for this statement."]
    
    try:
        ocr_data = json.loads(ocr_json_str)
    except Exception:
        return False, ["Extracted OCR response is not valid JSON."]
    
    # Load system settings
    from services.proposal_service import get_system_settings
    settings = get_system_settings()
    
    # Check Units Consumed
    units_consumed = ocr_data.get("units_consumed")
    if units_consumed is None:
        return False, ["Units consumed (kWh) is missing from the extracted bill data."]
    
    try:
        units_consumed = float(units_consumed)
    except ValueError:
        return False, ["Units consumed value is invalid."]

    # Check Tariff Rate
    tariff_val = settings.get("electricity_tariff")
    if not tariff_val:
        return False, ["Electricity tariff rate is not configured in settings."]
    
    try:
        tariff = float(tariff_val)
        if tariff <= 0:
            return False, ["Electricity tariff rate must be greater than zero."]
    except ValueError:
        return False, ["Electricity tariff rate configured in settings is invalid."]

    # Verify billing period validity
    period_start = bill.get("billing_period_start")
    period_end = bill.get("billing_period_end")
    warnings = []
    
    if not period_start or not period_end:
        warnings.append("Billing cycle start/end dates are missing. Defaulting calculations to a standard 30-day period.")
    else:
        try:
            from datetime import datetime
            fmt = "%Y-%m-%d"
            start_dt = datetime.strptime(period_start, fmt)
            end_dt = datetime.strptime(period_end, fmt)
            days = (end_dt - start_dt).days
            if days <= 0:
                warnings.append(f"Billing cycle end date ({period_end}) must be after start date ({period_start}). Using 30 days.")
        except Exception:
            warnings.append("Billing cycle dates are not in valid format. Using 30 days.")

    # 2. Retrieve solar assumptions from settings with standard fallbacks
    peak_sun_hours = float(settings.get("peak_sun_hours", "4.5"))
    performance_ratio = float(settings.get("performance_ratio", "0.75"))
    inverter_efficiency = float(settings.get("inverter_efficiency", "0.97"))
    system_loss = float(settings.get("system_loss", "0.14"))
    installation_cost_per_kw = float(settings.get("installation_cost_per_kw", "50000.0"))
    co2_conversion_factor = float(settings.get("co2_conversion_factor", "0.82"))
    tree_conversion_factor = float(settings.get("tree_conversion_factor", "0.04"))

    # 3. Calculate Recommended Solar Plant Size (kW)
    # Plant Size (kW) = (Units Consumed / 30) / (Peak Sun Hours * Performance Ratio)
    recommended_size = (units_consumed / 30.0) / (peak_sun_hours * performance_ratio)
    
    # Cap recommended size at connected or sanctioned load if specified in OCR or Site
    site_conn_load = ocr_data.get("connected_load") or ocr_data.get("sanctioned_load")
    # If not in OCR, check site info via connection query
    if not site_conn_load:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT connected_load, sanctioned_load FROM sites WHERE id = ?;", (site_id,))
            s_row = cur.fetchone()
            if s_row:
                site_conn_load = s_row[0] or s_row[1]
        except Exception:
            pass
        finally:
            conn.close()

    if site_conn_load:
        try:
            site_conn_load_val = float(site_conn_load)
            if site_conn_load_val > 0 and recommended_size > site_conn_load_val:
                recommended_size = site_conn_load_val
                warnings.append(f"Recommended solar plant size capped at the site's load capacity limit of {site_conn_load_val} kW.")
        except ValueError:
            pass

    # Standard inverter selection (1.0 ratio sizing)
    recommended_inverter = recommended_size * 1.0

    # 4. Generate Production Estimations
    # Monthly Gen = Plant Size * Peak Sun Hours * 30 * Performance Ratio
    estimated_monthly_gen = recommended_size * peak_sun_hours * 30.0 * performance_ratio
    # Annual Gen = Plant Size * Peak Sun Hours * 365 * Performance Ratio
    estimated_annual_gen = recommended_size * peak_sun_hours * 365.0 * performance_ratio

    # 5. Financial Feasibility calculations
    # Capped savings at actual consumption (net metering limit check)
    monthly_savings = min(estimated_monthly_gen, units_consumed) * tariff
    annual_savings = monthly_savings * 12.0

    system_cost = recommended_size * installation_cost_per_kw
    
    payback_years = 0.0
    if annual_savings > 0:
        payback_years = round(system_cost / annual_savings, 2)

    # 6. Environmental offset factors
    co2_offset = estimated_annual_gen * co2_conversion_factor
    trees_equivalent = co2_offset * tree_conversion_factor

    # 7. Database persistence
    conn = get_connection()
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        
        # Save results in calculation_results
        query = """
            INSERT INTO calculation_results (
                bill_id, plant_size_kw, recommended_inverter_kw, estimated_monthly_generation,
                estimated_annual_generation, monthly_savings, annual_savings, system_cost,
                payback_years, co2_offset, trees_equivalent, calculation_version, calculation_status, warnings
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """ if is_sqlite else """
            INSERT INTO calculation_results (
                bill_id, plant_size_kw, recommended_inverter_kw, estimated_monthly_generation,
                estimated_annual_generation, monthly_savings, annual_savings, system_cost,
                payback_years, co2_offset, trees_equivalent, calculation_version, calculation_status, warnings
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        status_label = "Warning" if warnings else "Success"
        warnings_json = json.dumps(warnings) if warnings else None
        
        cur.execute(query, (
            bill_id,
            round(recommended_size, 2),
            round(recommended_inverter, 2),
            round(estimated_monthly_gen, 2),
            round(estimated_annual_gen, 2),
            round(monthly_savings, 2),
            round(annual_savings, 2),
            round(system_cost, 2),
            payback_years,
            round(co2_offset, 2),
            round(trees_equivalent, 1),
            "1.0",
            status_label,
            warnings_json
        ))
        
        # Get result id
        calc_id = cur.lastrowid
        if not is_sqlite:
            cur.execute("SELECT currval(pg_get_serial_sequence('calculation_results','id'));")
            calc_id = cur.fetchone()[0]

        # Update parent record
        upd_bill = """
            UPDATE electricity_bills
            SET latest_calculation_id = ?, bill_status = 'Verified'
            WHERE id = ?;
        """ if is_sqlite else """
            UPDATE electricity_bills
            SET latest_calculation_id = %s, bill_status = 'Verified'
            WHERE id = %s;
        """
        cur.execute(upd_bill, (calc_id, bill_id))
        conn.commit()

        # Log timeline action
        log_site_activity(
            site_id, 
            "Calculations Performed", 
            f"Solar feasibility analysis generated. Size: {round(recommended_size, 2)} kW, Payback: {payback_years} years.", 
            actor
        )
        return True, warnings
    except Exception as e:
        conn.rollback()
        print(f"Error persisting calculation results: {e}")
        return False, [str(e)]
    finally:
        conn.close()
