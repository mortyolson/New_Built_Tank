import os
import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Table, TableStyle

from main import (
    ACCESSORIES_FIXED_COST_EUR,
    calculate_bottom_cost,
    calculate_bottom_design,
    calculate_ndt_cost,
    calculate_roof_cost,
    calculate_shell_cost,
    calculate_shell_design,
    calculate_site_erection_cost,
    calculate_total_project_cost,
    find_cheapest_shell_material_combination,
    find_lightest_safe_fixed_cone_roof_rafter,
)

st.set_page_config(page_title="Storage Tank Cost Estimate", layout="wide")

st.markdown(
    """
    <style>
    .main > div { padding-top: 1.1rem; }
    div[data-testid="stDataFrame"] {
        border: 1px solid #d9d9d9; padding: 6px; background-color: white; border-radius: 10px;
    }
    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(90deg, #F37021 0%, #E85D04 100%);
        color: white; border: none; border-radius: 10px; font-weight: 700; padding: 0.8rem 1rem;
    }
    .metric-card {
        border: 1px solid #e5e7eb; background: white; padding: 18px; border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-top: 4px solid #1F4E79; margin-bottom: 10px;
    }
    .metric-label { font-size: 12px; color: #667085; margin-bottom: 7px; text-transform: uppercase; font-weight: 700; }
    .metric-value { font-size: 24px; font-weight: 800; color: #163a5a; line-height: 1.15; }
    .metric-sub { font-size: 12px; color: #777; margin-top: 6px; line-height: 1.35; }
    .section-card { border: 1px solid #dfe5eb; border-radius: 12px; padding: 14px; background: white;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-bottom: 10px; }
    .section-title { font-size: 18px; font-weight: 800; color: #1F4E79; margin-bottom: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

def val(x):
    if x is None or x == "":
        return "N/A"
    if isinstance(x, float):
        return round(x, 2)
    return x

def safe_get(dct, key, default="N/A"):
    if dct is None:
        return default
    return dct.get(key, default)

def fmt_eur(x):
    if x is None or x == "N/A":
        return "N/A"
    return f"€ {x:,.2f}"

def fmt_tonnes(x):
    if x is None or x == "N/A":
        return "N/A"
    return f"{x:,.2f} t"

def fmt_hours(x):
    if x is None or x == "N/A":
        return "N/A"
    return f"{x:,.2f} h"

def metric_card(label, value, subtext=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def section_card_title(title):
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">{title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

@st.cache_data
def run_bottom_design(inputs):
    return calculate_bottom_design(
        tank_diameter=inputs["tank_diameter"],
        design_liquid_height=inputs["design_liquid_height"],
        corrosion_allowance_bottom=inputs["corrosion_allowance_bottom"],
        shell_design_n18=inputs["shell_design_n18"],
    )

@st.cache_data
def run_bottom_cost(inputs, bottom_result):
    return calculate_bottom_cost(inputs, bottom_result)

@st.cache_data
def run_shell_optimizer(inputs):
    return find_cheapest_shell_material_combination(
        tank_diameter=inputs["tank_diameter"],
        shell_height=inputs["shell_height"],
        material_type=inputs["material_type"],
        design_density_operating=inputs["design_density_operating"],
        test_density=inputs["test_density"],
        design_pressure=inputs["design_pressure"],
        test_pressure=inputs["test_pressure"],
        shell_corrosion_allowance=inputs["shell_corrosion_allowance"],
        wind_gust_velocity=inputs["wind_gust_velocity"],
        search_mode=inputs["shell_search_mode"],
    )

@st.cache_data
def run_shell_cost(inputs, best_shell):
    if best_shell is None:
        return None, None

    optimized_shell_result = calculate_shell_design(
        tank_diameter=inputs["tank_diameter"],
        shell_height=inputs["shell_height"],
        material_type=inputs["material_type"],
        design_density_operating=inputs["design_density_operating"],
        test_density=inputs["test_density"],
        design_pressure=inputs["design_pressure"],
        test_pressure=inputs["test_pressure"],
        shell_corrosion_allowance=inputs["shell_corrosion_allowance"],
        wind_gust_velocity=inputs["wind_gust_velocity"],
        shell_materials=best_shell["shell_materials"],
    )

    shell_cost_result = calculate_shell_cost(
        inputs=inputs,
        best_shell=best_shell,
        shell_result=optimized_shell_result,
    )

    return optimized_shell_result, shell_cost_result

@st.cache_data
def run_roof_optimizer(inputs):
    return find_lightest_safe_fixed_cone_roof_rafter(
        tank_diameter=inputs["tank_diameter"],
        design_pressure=inputs["design_pressure"],
        live_loads=inputs["live_loads"],
        snow_loads=inputs["snow_loads"],
        insulation_loads=inputs["insulation_loads"],
        roof_slope=inputs["roof_slope"],
        roof_plate_material=inputs["roof_plate_material"],
        supporting_material=inputs["supporting_material"],
    )

@st.cache_data
def run_roof_cost(inputs, roof_result, best_shell):
    if roof_result is None or best_shell is None:
        return None
    if safe_get(roof_result, "status") != "SAFE":
        return None
    if "details" not in roof_result:
        return None

    return calculate_roof_cost(inputs=inputs, roof_result=roof_result, best_shell=best_shell)

@st.cache_data
def run_site_erection_cost(inputs, bottom_cost_result, shell_cost_result, roof_cost_result):
    if shell_cost_result is None:
        return None
    return calculate_site_erection_cost(inputs, bottom_cost_result, shell_cost_result, roof_cost_result)

@st.cache_data
def run_ndt_cost(inputs):
    return calculate_ndt_cost(inputs)

@st.cache_data
def run_total_project_cost(bottom_cost_result, shell_cost_result, roof_cost_result, site_erection_cost_result, ndt_cost_result):
    return calculate_total_project_cost(
        bottom_cost_result=bottom_cost_result,
        shell_cost_result=shell_cost_result,
        roof_cost_result=roof_cost_result,
        site_erection_cost_result=site_erection_cost_result,
        ndt_cost_result=ndt_cost_result,
        accessories_cost_eur=ACCESSORIES_FIXED_COST_EUR,
    )

def generate_pdf(inputs, bottom_result, bottom_cost_result, best_shell, shell_cost_result, roof_result, roof_cost_result, site_erection_cost_result, ndt_cost_result, total_project_cost_result, logo_path="verwater_logo.png"):
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=10, rightMargin=10, topMargin=10, bottomMargin=10)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("title_style", parent=styles["Normal"], fontName="Helvetica-BoldOblique", fontSize=10.5, leading=10.8, alignment=TA_LEFT)
    normal_style = ParagraphStyle("normal_style", parent=styles["Normal"], fontName="Helvetica", fontSize=6.1, leading=6.6, alignment=TA_LEFT)
    centered_bold_style = ParagraphStyle("centered_bold_style", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=6.1, leading=6.6, alignment=TA_CENTER)
    section_style = ParagraphStyle("section_style", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.0, leading=7.2, alignment=TA_LEFT)

    blue = colors.HexColor("#1F4E79")

    def p(text, style=normal_style):
        return Paragraph(str(text), style)

    def fmt_num(x, digits=2):
        if x is None or x == "N/A":
            return "N/A"
        try:
            return f"{float(x):,.{digits}f}"
        except Exception:
            return str(x)

    elements = []

    logo = p("<b>VERWATER</b>", title_style)
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=110, height=16)
        except Exception:
            pass

    header_rows = [
        [p("<b><i>Techno-Economical Specification</i></b>", title_style), logo],
        [p("Storage tank preliminary estimate", normal_style), ""],
    ]
    header_table = Table(header_rows, colWidths=[260, 220])
    header_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.55, colors.black),
        ("SPAN", (0, 1), (1, 1)),
        ("LINEABOVE", (0, 0), (-1, 0), 1.0, blue),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(header_table)

    total = safe_get(total_project_cost_result, "total_project_cost_eur", 0)
    bottom = safe_get(bottom_cost_result, "total_cost", 0)
    shell = safe_get(shell_cost_result, "total_shell_cost_eur", 0)
    roof = safe_get(roof_cost_result, "total_roof_cost_eur", 0)
    site = safe_get(site_erection_cost_result, "total_site_related_costs", 0)
    ndt = safe_get(ndt_cost_result, "total_ndt_cost_eur", 0)

    summary_rows = [
        [p("<b>SUMMARY</b>", section_style), "", ""],
        [p("Bottom cost"), p(fmt_num(bottom, 2), centered_bold_style), p("EUR", centered_bold_style)],
        [p("Shell cost"), p(fmt_num(shell, 2), centered_bold_style), p("EUR", centered_bold_style)],
        [p("Roof cost"), p(fmt_num(roof, 2), centered_bold_style), p("EUR", centered_bold_style)],
        [p("Site erection"), p(fmt_num(site, 2), centered_bold_style), p("EUR", centered_bold_style)],
        [p("NDT"), p(fmt_num(ndt, 2), centered_bold_style), p("EUR", centered_bold_style)],
        [p("Accessories"), p(fmt_num(ACCESSORIES_FIXED_COST_EUR, 2), centered_bold_style), p("EUR", centered_bold_style)],
        [p("<b>Total project cost</b>"), p(f"<b>{fmt_num(total, 2)}</b>", centered_bold_style), p("<b>EUR</b>", centered_bold_style)],
    ]
    summary_table = Table(summary_rows, colWidths=[240, 140, 100])
    summary_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.55, colors.black),
        ("SPAN", (0, 0), (-1, 0)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(summary_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

with st.sidebar:
    st.header("Primary Input Parameters")
    tank_diameter = st.number_input("Diameter of the tank (m)", min_value=0.1, value=15.0, step=0.1)
    material_type = st.selectbox("Material type", ["Carbon Steel Lap Welded", "Carbon Steel Butt Welded", "Stainless Steel Lap Welded"], index=0)
    design_liquid_height = st.number_input("Maximum design liquid height (m)", min_value=0.1, value=29.0, step=0.1)
    shell_height = st.number_input("Shell height (m)", min_value=0.1, value=29.0, step=0.1)
    liquid_temperature = st.number_input("Temperature of the contained liquid (°C)", value=25.0, step=1.0)
    liquid_stored = st.text_input("Liquid stored", value="1-Decanol")
    design_density_operating = st.number_input("Maximum design density of contained liquid under storage conditions (kg/l)", min_value=0.0, value=1.02, step=0.01)
    test_density = st.number_input("Maximum design density of test medium (kg/l)", min_value=0.0, value=1.00, step=0.01)
    design_internal_negative_pressure = st.number_input("Design internal negative pressure (mBar)", value=5.0, step=1.0)
    test_pressure = st.number_input("Test pressure (mBar)", value=10.0, step=1.0)
    design_pressure = st.number_input("Design pressure (mBar)", value=10.0, step=1.0)
    roof_type = st.selectbox("Roof type", ["Cone"], index=0)
    roof_plate_material = st.selectbox("Roof plate material", ["S235JR", "S355JR"], index=0)
    supporting_material = st.selectbox("Supporting material", ["S235JR", "S355JR"], index=0)
    roof_slope = st.number_input("Roof slope", min_value=0.01, value=0.20, step=0.01)
    corrosion_allowance_bottom = st.number_input("Corrosion Allowance Bottom (mm)", min_value=0.0, value=2.0, step=1.0)
    shell_corrosion_allowance = st.number_input("Corrosion Allowance Shell (mm)", min_value=0.0, value=1.0, step=1.0)
    corrosion_allowance_roof = st.number_input("Corrosion Allowance Roof (mm)", min_value=0.0, value=0.0, step=1.0)
    wind_gust_velocity = st.number_input("Wind gust velocity (m/s)", min_value=0.1, value=45.0, step=1.0)
    live_loads = st.number_input("Live Loads (kN/m²)", min_value=0.0, value=1.25, step=0.05)
    snow_loads = st.number_input("Snow Loads (kN/m²)", min_value=0.0, value=2.5, step=0.1)
    insulation_loads = st.number_input("Insulation Loads (kN/m²)", min_value=0.0, value=0.0, step=0.1)
    mdmt = st.number_input("MDMT (°C)", value=-10.0, step=1.0)
    max_temp = st.number_input("Max Temp (°C)", value=50.0, step=1.0)
    method_of_erection = st.selectbox("Method of erection", ["Jacking", "Stacking"], index=0)
    shell_design_n18 = st.number_input("Shell design N18", min_value=0.0, value=9.0, step=1.0)
    shell_search_mode = st.selectbox("Shell optimization mode", ["two_zone", "uniform", "full"], index=0)

inputs = {
    "tank_diameter": tank_diameter,
    "material_type": material_type,
    "design_liquid_height": design_liquid_height,
    "shell_height": shell_height,
    "liquid_temperature": liquid_temperature,
    "liquid_stored": liquid_stored,
    "design_density_operating": design_density_operating,
    "test_density": test_density,
    "design_internal_negative_pressure": design_internal_negative_pressure,
    "test_pressure": test_pressure,
    "design_pressure": design_pressure,
    "roof_type": roof_type,
    "roof_plate_material": roof_plate_material,
    "supporting_material": supporting_material,
    "roof_slope": roof_slope,
    "corrosion_allowance_bottom": corrosion_allowance_bottom,
    "shell_corrosion_allowance": shell_corrosion_allowance,
    "corrosion_allowance_roof": corrosion_allowance_roof,
    "wind_gust_velocity": wind_gust_velocity,
    "live_loads": live_loads,
    "snow_loads": snow_loads,
    "insulation_loads": insulation_loads,
    "mdmt": mdmt,
    "max_temp": max_temp,
    "method_of_erection": method_of_erection,
    "shell_design_n18": shell_design_n18,
    "shell_search_mode": shell_search_mode,
}

try:
    bottom_result = run_bottom_design(inputs)
    bottom_cost_result = run_bottom_cost(inputs, bottom_result)
    best_shell = run_shell_optimizer(inputs)
    optimized_shell_result, shell_cost_result = run_shell_cost(inputs, best_shell)
    roof_result = run_roof_optimizer(inputs)
    roof_cost_result = run_roof_cost(inputs, roof_result, best_shell)
    site_erection_cost_result = run_site_erection_cost(inputs, bottom_cost_result, shell_cost_result, roof_cost_result)
    ndt_cost_result = run_ndt_cost(inputs)
    total_project_cost_result = run_total_project_cost(bottom_cost_result, shell_cost_result, roof_cost_result, site_erection_cost_result, ndt_cost_result)
except ValueError as e:
    st.error(f"Input error: {e}")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error: {e}")
    st.stop()

pdf_file = None
if best_shell is not None:
    pdf_file = generate_pdf(
        inputs=inputs,
        bottom_result=bottom_result,
        bottom_cost_result=bottom_cost_result,
        best_shell=best_shell,
        shell_cost_result=shell_cost_result,
        roof_result=roof_result,
        roof_cost_result=roof_cost_result,
        site_erection_cost_result=site_erection_cost_result,
        ndt_cost_result=ndt_cost_result,
        total_project_cost_result=total_project_cost_result,
    )

header_left, header_center, header_right = st.columns([5, 2.2, 1.8])

with header_left:
    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #143A5C 0%, #2E679B 100%); padding: 26px 28px 20px 28px;
                    border-radius: 14px; color: white; min-height: 122px;">
            <div style="font-size: 34px; font-weight: 800; line-height: 1.15; margin-bottom: 10px;">
                Cost Estimate for New Build Storage Tanks
            </div>
            <div style="font-size: 15px; opacity: 0.92; line-height: 1.4;">
                Verwater — Engineering Cost Estimation Tool
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with header_center:
    if pdf_file is not None:
        st.download_button(
            label="Download PDF Report",
            data=pdf_file,
            file_name="Verwater_Techno_Economical_Specification.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.button("Download PDF Report", disabled=True, use_container_width=True)

with header_right:
    if os.path.exists("verwater_logo.png"):
        st.image("verwater_logo.png", use_container_width=True)
    else:
        st.markdown("<div style='font-weight:700;color:#1F4E79;font-size:28px;'>VERWATER</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin-top:12px;margin-bottom:20px;'>", unsafe_allow_html=True)
st.caption("All values are indicative and based on preliminary engineering assumptions.")

total_annular_mass = safe_get(bottom_result, "total_annular_plate_mass_kg", 0)
total_bottom_mass = safe_get(bottom_result, "total_bottom_plate_mass_kg", 0)
bottom_weight_tonnes = ((total_annular_mass or 0) + (total_bottom_mass or 0)) / 1000

other_cost_eur = (
    safe_get(site_erection_cost_result, "total_site_related_costs", 0)
    + safe_get(ndt_cost_result, "total_ndt_cost_eur", 0)
    + ACCESSORIES_FIXED_COST_EUR
)

k1, k2, k3, k4 = st.columns(4)
with k1:
    metric_card("Bottom Cost", fmt_eur(safe_get(bottom_cost_result, "total_cost")))
with k2:
    metric_card("Shell Cost", fmt_eur(safe_get(shell_cost_result, "total_shell_cost_eur")))
with k3:
    metric_card("Roof Cost", fmt_eur(safe_get(roof_cost_result, "total_roof_cost_eur")))
with k4:
    metric_card("Final Total", fmt_eur(safe_get(total_project_cost_result, "total_project_cost_eur")))

if best_shell is None:
    st.error("No valid optimized shell design found.")
else:
    shell_df = pd.DataFrame({
        "Shell Course": list(range(1, len(best_shell["shell_materials"]) + 1)),
        "Material": [val(x) for x in best_shell["shell_materials"]],
        "Thickness (mm)": [val(x) for x in best_shell["course_thicknesses"]],
    })

    bottom_df = pd.DataFrame([
        {
            "Component": "Annular Plate",
            "Material": val(safe_get(bottom_result, "annular_plate_material")),
            "Thickness (mm)": val(safe_get(bottom_result, "annular_plate_corroded_thickness_mm")),
        },
        {
            "Component": "Sketch Bottom Plate",
            "Material": val(safe_get(bottom_result, "bottom_plate_material")),
            "Thickness (mm)": val(safe_get(bottom_result, "minimum_nominal_bottom_plate_thickness")),
        },
    ])

    roof_df = pd.DataFrame([
        {"Parameter": "Rafter Type", "Value": val(safe_get(roof_result, "rafter_type"))},
        {"Parameter": "Number of Rafters", "Value": val(safe_get(roof_result, "number_of_rafters"))},
        {"Parameter": "Status", "Value": val(safe_get(roof_result, "status"))},
        {"Parameter": "Crown Ring Type", "Value": val(safe_get(roof_result, "crown_ring_type"))},
    ])

    col1, col2 = st.columns([1.15, 1])
    with col1:
        section_card_title("Optimized Shell Courses")
        st.dataframe(shell_df, use_container_width=True, hide_index=True)
    with col2:
        section_card_title("Bottom Plates")
        st.dataframe(bottom_df, use_container_width=True, hide_index=True)
        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        section_card_title("Fixed Cone Roof")
        st.dataframe(roof_df, use_container_width=True, hide_index=True)

    if val(safe_get(roof_result, "status")) == "SAFE":
        st.success("Roof design is SAFE")
    else:
        st.error("Roof design is NOT SAFE")

    st.subheader("Cost Summary")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Bottom Total", fmt_eur(safe_get(bottom_cost_result, "total_cost")), fmt_tonnes(bottom_weight_tonnes))
    with c2:
        metric_card("Shell Total", fmt_eur(safe_get(shell_cost_result, "total_shell_cost_eur")), fmt_hours(safe_get(shell_cost_result, "total_shop_hours")))
    with c3:
        metric_card("Roof Total", fmt_eur(safe_get(roof_cost_result, "total_roof_cost_eur")), fmt_hours(safe_get(roof_cost_result, "total_roof_shop_hours")))
    with c4:
        metric_card("Other Costs", fmt_eur(other_cost_eur), "Site erection + NDT + accessories")

    st.subheader("Final Project Total")
    st.metric("Total Project Cost", fmt_eur(safe_get(total_project_cost_result, "total_project_cost_eur")))
