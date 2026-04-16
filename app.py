import io
import os
import textwrap

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

st.set_page_config(
    page_title="Cost Estimate for New Build Storage Tanks",
    layout="wide",
    page_icon="verwater_logo.png",   # 👈 ADD THIS LINE
)

st.markdown(
    """
    <link rel="apple-touch-icon" href="verwater_logo.png">
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <style>
    .main > div { padding-top: 1.1rem; }

    div[data-testid="stDataFrame"] {
        border: 1px solid #d9d9d9;
        padding: 6px;
        background-color: white;
        border-radius: 10px;
    }

    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(90deg, #F37021 0%, #E85D04 100%);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.80rem 1rem;
        font-size: 15px;
        box-shadow: 0 4px 12px rgba(243,112,33,0.28);
    }

    div[data-testid="stDownloadButton"] > button:hover {
        background: linear-gradient(90deg, #d85a12 0%, #c94f00 100%);
        color: white;
    }

    div[data-testid="stButton"] > button {
        border-radius: 10px;
    }

    .metric-card {
        border: 1px solid #e5e7eb;
        background: white;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border-top: 4px solid #1F4E79;
        margin-bottom: 10px;
        min-height: 118px;
    }

    .metric-label {
        font-size: 12px;
        color: #667085;
        margin-bottom: 7px;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        font-weight: 700;
    }

    .metric-value {
        font-size: 24px;
        font-weight: 800;
        color: #163a5a;
        line-height: 1.15;
    }

    .metric-sub {
        font-size: 12px;
        color: #777;
        margin-top: 6px;
        line-height: 1.35;
    }

    .section-card {
        border: 1px solid #dfe5eb;
        border-radius: 12px;
        padding: 14px;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 10px;
    }

    .section-title {
        font-size: 18px;
        font-weight: 800;
        color: #1F4E79;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------
# Helpers
# ----------------------------
def html_block(html: str):
    st.markdown(textwrap.dedent(html), unsafe_allow_html=True)


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


def safe_num(dct, key, default=0.0):
    if dct is None:
        return default
    try:
        value = dct.get(key, default)
        if value in (None, "N/A", ""):
            return default
        return float(value)
    except (TypeError, ValueError, AttributeError):
        return default


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
    html_block(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtext}</div>
        </div>
        """
    )


def section_card_title(title):
    html_block(
        f"""
        <div class="section-card">
            <div class="section-title">{title}</div>
        </div>
        """
    )


def safe_sum(*values):
    total = 0.0
    for v in values:
        try:
            if v is not None and v != "N/A":
                total += float(v)
        except Exception:
            pass
    return total


# ----------------------------
# Cached calculations
# ----------------------------
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

    return calculate_roof_cost(
        inputs=inputs,
        roof_result=roof_result,
        best_shell=best_shell,
    )


@st.cache_data
def run_site_erection_cost(inputs, bottom_cost_result, shell_cost_result, roof_cost_result):
    if shell_cost_result is None:
        return None
    return calculate_site_erection_cost(
        inputs=inputs,
        bottom_cost_result=bottom_cost_result,
        shell_cost_result=shell_cost_result,
        roof_cost_result=roof_cost_result,
    )


@st.cache_data
def run_ndt_cost(inputs):
    return calculate_ndt_cost(inputs)


@st.cache_data
def run_total_project_cost(
    bottom_cost_result,
    shell_cost_result,
    roof_cost_result,
    site_erection_cost_result,
    ndt_cost_result,
):
    return calculate_total_project_cost(
        bottom_cost_result=bottom_cost_result,
        shell_cost_result=shell_cost_result,
        roof_cost_result=roof_cost_result,
        site_erection_cost_result=site_erection_cost_result,
        ndt_cost_result=ndt_cost_result,
        accessories_cost_eur=ACCESSORIES_FIXED_COST_EUR,
    )


# ----------------------------
# PDF generation
# ----------------------------
def generate_pdf(
    inputs,
    bottom_result,
    bottom_cost_result,
    best_shell,
    shell_cost_result,
    roof_result,
    roof_cost_result,
    site_erection_cost_result,
    ndt_cost_result,
    total_project_cost_result,
    logo_path="verwater_logo.png",
):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12,
        rightMargin=12,
        topMargin=12,
        bottomMargin=12,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title_style",
        parent=styles["Normal"],
        fontName="Helvetica-BoldOblique",
        fontSize=10.5,
        leading=10.8,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=0,
    )
    normal_style = ParagraphStyle(
        "normal_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.1,
        leading=6.6,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=0,
    )
    tiny_style = ParagraphStyle(
        "tiny_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=5.5,
        leading=5.8,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=0,
    )
    centered_bold_style = ParagraphStyle(
        "centered_bold_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.1,
        leading=6.6,
        alignment=TA_CENTER,
        spaceBefore=0,
        spaceAfter=0,
    )
    section_style = ParagraphStyle(
        "section_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.0,
        leading=7.2,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=0,
    )

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

    total_annular_mass = safe_num(bottom_result, "total_annular_plate_mass_kg", 0)
    total_bottom_mass = safe_num(bottom_result, "total_bottom_plate_mass_kg", 0)
    bottom_weight_t = safe_sum(total_annular_mass, total_bottom_mass) / 1000.0

    shell_weight_t = safe_num(shell_cost_result, "total_shell_weight_kg", 0) / 1000.0
    roof_weight_t = safe_num(roof_cost_result, "total_roof_weight_kg", 0) / 1000.0
    final_weight_t = bottom_weight_t + shell_weight_t + roof_weight_t

    shell_materials = best_shell.get("shell_materials", []) if best_shell else []
    shell_course_count = len(shell_materials)
    shell_course_height = round(inputs["shell_height"] / shell_course_count, 1) if shell_course_count else "N/A"

    roof_rafter = val(safe_get(roof_result, "rafter_type"))
    annular_thk = val(safe_get(bottom_result, "annular_plate_corroded_thickness_mm"))
    annular_mat = val(safe_get(bottom_result, "annular_plate_material"))
    bottom_thk = val(safe_get(bottom_result, "minimum_nominal_bottom_plate_thickness"))
    bottom_mat = val(safe_get(bottom_result, "bottom_plate_material"))

    shell_primary_ring = (
        "Not Required"
        if safe_get(shell_cost_result, "number_of_stiffening_rings", 0) in [0, "N/A", None]
        else safe_get(shell_cost_result, "number_of_stiffening_rings")
    )

    live_roof_load = safe_sum(
        inputs.get("live_loads", 0),
        inputs.get("snow_loads", 0),
        inputs.get("insulation_loads", 0),
    )

    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=110, height=16)
        except Exception:
            logo = p("<b>VERWATER</b>", title_style)
    else:
        logo = p("<b>VERWATER</b>", title_style)

    header_rows = [
        [p("<b><i>Techno-Economical Specification</i></b>", title_style), logo],
        [p("<i>Thank you for considering Verwater, ENSURING SAFETY QUALITY & EXCELLENCE</i>", normal_style), ""],
        [p("requested. For more information, please contact <b>sales@verwater.com</b> and/or <b>e.slager@verwater.com</b>", normal_style), ""],
        [p("<i>Client:</i>", normal_style), p("<i>Project:</i>", normal_style)],
        [p("<i>RFQ:</i>", normal_style), p("<i>Date:</i>", normal_style)],
    ]
    header_table = Table(header_rows, colWidths=[245, 245], rowHeights=[20, 12, 16, 12, 12])
    header_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.55, colors.black),
                ("SPAN", (0, 1), (1, 1)),
                ("SPAN", (0, 2), (1, 2)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LINEABOVE", (0, 0), (-1, 0), 1.0, blue),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ]
        )
    )
    elements.append(header_table)

    final_rows = [
        [p("<b>FINAL CONSIDERATIONS</b>", section_style), "", ""],
        [
            p('<font color="#F37021"><b>Final Price of the Storage Tank*</b></font>', normal_style),
            p(
                f'<font color="#F37021"><b>{fmt_num(safe_get(total_project_cost_result, "total_project_cost_eur"), 0)}</b></font>',
                centered_bold_style,
            ),
            p('<font color="#F37021"><b>Euros</b></font>', centered_bold_style),
        ],
        [
            p("Final Weight of the Tank", normal_style),
            p(f"{fmt_num(final_weight_t, 0)}", centered_bold_style),
            p("Tonnes", centered_bold_style),
        ],
        [
            p(
                "'Disclosure. Certain items have not been included in the pricing calculation of the storage tank. "
                'This is a "quick and dirty" price estimate with a deviation of +/- 15% from the actual price of the storage tank. '
                "Travelling costs are not included in the estimate, together with out of the ordinary expenses "
                "(Civil, Piping, E&I, Detection). The Design is based on the EN 14015",
                tiny_style,
            ),
            "",
            "",
        ],
    ]
    final_table = Table(final_rows, colWidths=[175, 160, 155], rowHeights=[14, 14, 14, 30])
    final_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.55, colors.black),
                ("SPAN", (0, 0), (-1, 0)),
                ("SPAN", (0, 3), (-1, 3)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    elements.append(final_table)

    prelim_rows = [
        [p("<b>PRELIMINARY DESIGN CONDITIONS**</b>", section_style), "", "", ""],
        [p("Diameter of the tank (m)"), p(val(inputs["tank_diameter"])), p("Erection Method"), p(val(inputs["method_of_erection"]))],
        [p("Maximum design Liquid Height (m)"), p(val(inputs["design_liquid_height"])), p("Accessories"), p("Standard")],
        [p("Shell height (m)"), p(val(inputs["shell_height"])), p("Annular Plate thickness (Bottom) (mm)"), p(annular_thk)],
        [p("Design Code"), p("EN14015 : 2004"), p("Annular Plate Material (Bottom)"), p(annular_mat)],
        [p("Design pressure (mbar)"), p(val(inputs["design_pressure"])), p("Bottom Plate thickness (mm)"), p(bottom_thk)],
        [p("Design Vacuum (mbar)"), p(val(inputs["design_internal_negative_pressure"])), p("Bottom Plate Material"), p(bottom_mat)],
        [p("MDMT (DegC)"), p(val(inputs["mdmt"])), p("Shell Course Height (m)"), p(val(shell_course_height))],
        [p("Design Specific Gravity (kg/l)"), p(val(inputs["design_density_operating"])), p("Shell Course Number"), p(val(shell_course_count))],
        [p("Design Specific Gravity (Hydrotest) (kg/l)"), p(val(inputs["test_density"])), p("Number of Secondary Wind Girder(s)"), p(val(safe_get(shell_cost_result, "number_of_stiffening_rings", 0)))],
        [p("Corrosion allowance Bottom (mm)"), p(val(inputs["corrosion_allowance_bottom"])), p("Primary Stiffening Ring"), p(val(shell_primary_ring))],
        [p("Corrosion Allowance Shell (mm)"), p(val(inputs["shell_corrosion_allowance"])), p("Top Angle"), p("S355JR")],
        [p("Corrosion Allowance Roof (mm)"), p(val(inputs["corrosion_allowance_roof"])), p("Anchorage Requirement"), p("Anchorage Required")],
        [p("Windspeed (m/s)"), p(val(inputs["wind_gust_velocity"])), p("Number of Anchors"), p(val(safe_get(bottom_cost_result, "number_of_anchor_points")))],
        [p("Seismic Design"), p("Not Applicable"), p("Live Roof Load (kN/m²)"), p(val(live_roof_load))],
        [p("Roof Type"), p(val(inputs["roof_type"])), p("Roof Supp. Structure Material"), p(val(inputs["supporting_material"]))],
        [p("NDT according to EN 14015"), p("Included"), p("Roof Plates Material"), p(val(inputs["roof_plate_material"]))],
        [p("Painting"), p("Included"), p("Roof rafter Type"), p(roof_rafter)],
        [p(""), p(""), p("Roof Slope"), p(val(inputs["roof_slope"]))],
        [p("The design can be subject to change if the detailed engineering differs", tiny_style), "", "", ""],
    ]
    prelim_table = Table(prelim_rows, colWidths=[185, 70, 155, 80], rowHeights=[14] + [12] * 18 + [12])
    prelim_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.55, colors.black),
                ("SPAN", (0, 0), (-1, 0)),
                ("SPAN", (0, 19), (-1, 19)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    elements.append(prelim_table)

    cost_rows = [
        [p("<b>COST CONSIDERATIONS</b>", section_style), "", "", ""],
        [p("Engineering Hourly Cost (/hr)"), p("82"), p("Shop Manforce"), p("3")],
        [p("Welders Hourly Cost (/hr)"), p("67.7"), p("Site Manforce"), p("8")],
        [p("Electricity price (kWh/hr)"), p("0.33"), p("Coefficient for workers (Shop and Site)"), p("1.1")],
    ]
    cost_table = Table(cost_rows, colWidths=[185, 70, 155, 80], rowHeights=[14, 12, 12, 12])
    cost_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.55, colors.black),
                ("SPAN", (0, 0), (-1, 0)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    elements.append(cost_table)

    ass_rows = [
        [p("<b>ASSUMPTIONS AND CONSIDERATIONS</b>", section_style)],
        [p("a. In case of a lump sum second tank, the engineering pricing of the second tank will only be 25% of the first.", tiny_style)],
        [p("b. As aforementioned, this is a budget model price, and deviates by 15% in excess or deficit of the true tank price, which will be calculated following the confirmation of the project.", tiny_style)],
        [p("c. Verwater B.V has a Silver EcoVadis sustainability rating (Top 15%) making sustainability, one of our priorities", tiny_style)],
    ]
    ass_table = Table(ass_rows, colWidths=[490], rowHeights=[14, 12, 18, 12])
    ass_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.55, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    elements.append(ass_table)

    doc.build(elements)
    return buffer.getvalue()


# ----------------------------
# Sidebar inputs
# ----------------------------
with st.sidebar:
    st.header("Primary Input Parameters")

    tank_diameter = st.number_input("Diameter of the tank (m)", min_value=0.1, value=15.0, step=0.1)
    material_type = st.selectbox(
        "Material type",
        ["Carbon Steel Lap Welded", "Carbon Steel Butt Welded", "Stainless Steel Lap Welded"],
        index=0,
    )
    design_liquid_height = st.number_input("Maximum design liquid height (m)", min_value=0.1, value=29.0, step=0.1)
    shell_height = st.number_input("Shell height (m)", min_value=0.1, value=29.0, step=0.1)

    design_density_operating = st.number_input(
        "Maximum design density of contained liquid under storage conditions (kg/l)",
        min_value=0.0,
        value=1.02,
        step=0.01,
    )
    test_density = st.number_input(
        "Maximum design density of test medium (kg/l)",
        min_value=0.0,
        value=1.00,
        step=0.01,
    )
    design_internal_negative_pressure = st.number_input("Design internal negative pressure (mBar)", value=5.0, step=1.0)
    test_pressure = st.number_input("Test pressure (mBar)", value=10.0, step=1.0)
    design_pressure = st.number_input("Design pressure (mBar)", value=10.0, step=1.0)

    roof_type = st.selectbox("Roof type", ["Cone"], index=0)

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

inputs = {
    "tank_diameter": tank_diameter,
    "material_type": material_type,
    "design_liquid_height": design_liquid_height,
    "shell_height": shell_height,
    "liquid_temperature": 25.0,
    "liquid_stored": "N/A",
    "roof_plate_material": "S235JR",
    "supporting_material": "S235JR",
    "roof_slope": 0.20,
    "shell_design_n18": 9.0,
    "shell_search_mode": "two_zone",
    "design_density_operating": design_density_operating,
    "test_density": test_density,
    "design_internal_negative_pressure": design_internal_negative_pressure,
    "test_pressure": test_pressure,
    "design_pressure": design_pressure,
    "roof_type": roof_type,
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
}


# ----------------------------
# Run calculations
# ----------------------------
bottom_result = None
bottom_cost_result = None
best_shell = None
optimized_shell_result = None
shell_cost_result = None
roof_result = None
roof_cost_result = None
site_erection_cost_result = None
ndt_cost_result = None
total_project_cost_result = None
pdf_file_bytes = None

try:
    bottom_result = run_bottom_design(inputs)
    bottom_cost_result = run_bottom_cost(inputs, bottom_result)
    best_shell = run_shell_optimizer(inputs)
    optimized_shell_result, shell_cost_result = run_shell_cost(inputs, best_shell)
    roof_result = run_roof_optimizer(inputs)
    roof_cost_result = run_roof_cost(inputs, roof_result, best_shell)
    site_erection_cost_result = run_site_erection_cost(inputs, bottom_cost_result, shell_cost_result, roof_cost_result)
    ndt_cost_result = run_ndt_cost(inputs)
    total_project_cost_result = run_total_project_cost(
        bottom_cost_result,
        shell_cost_result,
        roof_cost_result,
        site_erection_cost_result,
        ndt_cost_result,
    )
except ValueError as e:
    st.error(f"Input error: {e}")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error during calculations: {e}")
    st.stop()

if all(
    [
        best_shell is not None,
        bottom_result is not None,
        bottom_cost_result is not None,
        total_project_cost_result is not None,
    ]
):
    try:
        pdf_file_bytes = generate_pdf(
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
        st.session_state["pdf_file_bytes"] = pdf_file_bytes
    except Exception as e:
        st.warning(f"PDF generation failed: {e}")
        pdf_file_bytes = None


# ----------------------------
# Top header
# ----------------------------
header_left, header_center, header_right = st.columns([5, 2.2, 1.8])

with header_left:
    st.markdown("## Cost Estimate for New Build Storage Tanks")
    st.caption("Verwater — Engineering Cost Estimation Tool")
    st.caption(
        "Preliminary techno-economical estimate for bottom, shell, fixed cone roof, "
        "site erection and related project costs."
    )

with header_center:
    html_block("<div style='padding-top: 8px;'></div>")

    if st.session_state.get("pdf_file_bytes"):
        st.download_button(
            label="Download PDF Report",
            data=st.session_state["pdf_file_bytes"],
            file_name="Verwater_Techno_Economical_Specification.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="download_pdf_report",
        )
    else:
        st.button(
            "Download PDF Report",
            disabled=True,
            use_container_width=True,
            key="download_pdf_report_disabled",
        )

    html_block(
        """
        <div style="
            font-size: 12px;
            color: #6b7280;
            margin-top: 8px;
            line-height: 1.35;
        ">
            Export the latest techno-economical specification in client-ready format.
        </div>
        """
    )

with header_right:
    html_block("<div style='padding-top: 10px; text-align: center;'></div>")

    if os.path.exists("verwater_logo.png"):
        st.image("verwater_logo.png", use_container_width=True)
    else:
        html_block(
            "<div style='font-weight:700;color:#1F4E79;font-size:28px;'>VERWATER</div>"
        )

st.markdown("<hr style='margin-top:12px;margin-bottom:20px;'>", unsafe_allow_html=True)
st.caption("All values are indicative and based on preliminary engineering assumptions.")


# ----------------------------
# Derived display values
# ----------------------------
total_annular_mass = safe_num(bottom_result, "total_annular_plate_mass_kg", 0)
total_bottom_mass = safe_num(bottom_result, "total_bottom_plate_mass_kg", 0)
bottom_weight_tonnes = (total_annular_mass + total_bottom_mass) / 1000
shell_weight_tonnes = safe_num(shell_cost_result, "total_shell_weight_kg", 0) / 1000
roof_weight_tonnes = safe_num(roof_cost_result, "total_roof_weight_kg", 0) / 1000
total_tank_weight_tonnes = bottom_weight_tonnes + shell_weight_tonnes + roof_weight_tonnes

other_cost_eur = (
    safe_num(site_erection_cost_result, "total_site_related_costs", 0)
    + safe_num(ndt_cost_result, "total_ndt_cost_eur", 0)
    + ACCESSORIES_FIXED_COST_EUR
)


# ----------------------------
# Main output
# ----------------------------
if best_shell is None:
    st.error("No valid optimized shell design found.")
else:
    html_block(
        """
        <div style="
            margin-top: 18px;
            margin-bottom: 18px;
            background: white;
            border: 1px solid #e4e7eb;
            border-left: 8px solid #F37021;
            border-radius: 12px;
            padding: 16px 18px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        ">
            <div style="
                font-size: 22px;
                font-weight: 800;
                color: #163a5a;
                margin-bottom: 4px;
            ">
                Design Output Summary
            </div>
            <div style="
                font-size: 13px;
                color: #667085;
                line-height: 1.4;
            ">
                Optimized preliminary configuration for bottom, shell, and fixed cone roof.
            </div>
        </div>
        """
    )

    shell_df = pd.DataFrame(
        {
            "Shell Course": list(range(1, len(best_shell["shell_materials"]) + 1)),
            "Material": [val(x) for x in best_shell["shell_materials"]],
            "Thickness (mm)": [val(x) for x in best_shell["course_thicknesses"]],
        }
    )

    bottom_df = pd.DataFrame(
        [
            {
                "Component": "Annular Plate",
                "Material": val(safe_get(bottom_result, "annular_plate_material")),
                "Thickness (mm)": val(safe_get(bottom_result, "annular_plate_corroded_thickness_mm")),
            },
            {
                "Component": "Bottom Plate",
                "Material": val(safe_get(bottom_result, "bottom_plate_material")),
                "Thickness (mm)": val(safe_get(bottom_result, "minimum_nominal_bottom_plate_thickness")),
            },
        ]
    )

    roof_df = pd.DataFrame(
        [
            {"Parameter": "Rafter Type", "Value": val(safe_get(roof_result, "rafter_type"))},
            {"Parameter": "Number of Rafters", "Value": val(safe_get(roof_result, "number_of_rafters"))},
            {"Parameter": "Status", "Value": val(safe_get(roof_result, "status"))},
            {"Parameter": "Crown Ring Type", "Value": val(safe_get(roof_result, "crown_ring_type"))},
        ]
    )

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

    html_block(
        """
        <div style="
            margin-top: 22px;
            margin-bottom: 18px;
            background: white;
            border: 1px solid #e4e7eb;
            border-left: 8px solid #1F4E79;
            border-radius: 12px;
            padding: 16px 18px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        ">
            <div style="
                font-size: 22px;
                font-weight: 800;
                color: #163a5a;
                margin-bottom: 4px;
            ">
                Cost Output Summary
            </div>
            <div style="
                font-size: 13px;
                color: #667085;
                line-height: 1.4;
            ">
                Overview of estimated costs for bottom, shell, roof and other project-related items.
            </div>
        </div>
        """
    )

    top1, top2, top3 = st.columns(3)
    with top1:
        metric_card("Final Total", fmt_eur(safe_num(total_project_cost_result, "total_project_cost_eur", 0)), "Full project estimate")
    with top2:
        metric_card("Other Costs", fmt_eur(other_cost_eur), "Site erection + NDT + accessories")
    with top3:
        metric_card("Total Tank Weight", fmt_tonnes(total_tank_weight_tonnes), "Bottom + shell + roof")

    html_block(
        """
        <div style="
            margin-top: 18px;
            margin-bottom: 10px;
            background: white;
            border: 1px solid #e4e7eb;
            border-left: 8px solid #1F4E79;
            border-radius: 12px;
            padding: 14px 18px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        ">
            <div style="font-size: 20px; font-weight: 800; color: #163a5a;">Bottom</div>
        </div>
        """
    )
    b1, b2 = st.columns(2)
    with b1:
        metric_card("Total Cost", fmt_eur(safe_num(bottom_cost_result, "total_cost", 0)))
    with b2:
        metric_card("Weight", fmt_tonnes(bottom_weight_tonnes))

    html_block(
        """
        <div style="
            margin-top: 18px;
            margin-bottom: 10px;
            background: white;
            border: 1px solid #e4e7eb;
            border-left: 8px solid #1F4E79;
            border-radius: 12px;
            padding: 14px 18px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        ">
            <div style="font-size: 20px; font-weight: 800; color: #163a5a;">Shell</div>
        </div>
        """
    )
    s1, s2, s3 = st.columns(3)
    with s1:
        metric_card("Total Cost", fmt_eur(safe_num(shell_cost_result, "total_shell_cost_eur", 0)))
    with s2:
        metric_card("Weight", fmt_tonnes(shell_weight_tonnes))
    with s3:
        metric_card("Stiffening Rings", str(val(safe_get(shell_cost_result, "number_of_stiffening_rings"))))

    html_block(
        """
        <div style="
            margin-top: 18px;
            margin-bottom: 10px;
            background: white;
            border: 1px solid #e4e7eb;
            border-left: 8px solid #1F4E79;
            border-radius: 12px;
            padding: 14px 18px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        ">
            <div style="font-size: 20px; font-weight: 800; color: #163a5a;">Roof</div>
        </div>
        """
    )
    r1, r2, r3 = st.columns(3)
    with r1:
        metric_card("Total Cost", fmt_eur(safe_num(roof_cost_result, "total_roof_cost_eur", 0)))
    with r2:
        metric_card("Weight", fmt_tonnes(roof_weight_tonnes))
    with r3:
        metric_card("N° Rafters", str(val(safe_get(roof_cost_result, "number_of_rafters"))))

    html_block(
        """
        <div style="
            margin-top: 18px;
            margin-bottom: 10px;
            background: white;
            border: 1px solid #e4e7eb;
            border-left: 8px solid #1F4E79;
            border-radius: 12px;
            padding: 14px 18px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        ">
            <div style="font-size: 20px; font-weight: 800; color: #163a5a;">Other Costs</div>
        </div>
        """
    )
    o1, o2, o3 = st.columns(3)
    with o1:
        metric_card("Site Erection", fmt_eur(safe_num(site_erection_cost_result, "total_site_related_costs", 0)))
    with o2:
        metric_card("NDT", fmt_eur(safe_num(ndt_cost_result, "total_ndt_cost_eur", 0)))
    with o3:
        metric_card("Accessories", fmt_eur(ACCESSORIES_FIXED_COST_EUR))

    st.success("Bottom, shell, roof and other core costs are included.")