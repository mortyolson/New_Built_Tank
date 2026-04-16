# main.py
# Module 1: Bottom Design + Shell Design + Fixed Cone Roof Design
# + Bottom Cost + Shell Cost + Roof Cost + Site Erection + Accessories + NDT + Total Project Cost

import math
from itertools import product

from backend_data import (
    get_steel_density,
    get_allowable_test_stress,
    get_allowable_design_stress,
    get_shell_course_material_names,
    get_steel_yield,
    get_ipe_profile_names,
    get_ipe_profile,
    get_unp_profile,
    get_crown_ring_for_rafter,
    get_youngs_modulus_mpa,
)

ACCESSORIES_FIXED_COST_EUR = 100000.0


# ----------------------------
# Validation helpers
# ----------------------------
def _require_positive(name, value):
    if value is None or value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")


def _require_non_negative(name, value):
    if value is None or value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")


def safe_number(value, default=0.0):
    try:
        if value is None or value == "N/A":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


# ----------------------------
# Bottom Design
# ----------------------------
def calculate_bottom_design(
    tank_diameter,
    design_liquid_height,
    corrosion_allowance_bottom,
    shell_design_n18,
):
    _require_positive("tank_diameter", tank_diameter)
    _require_positive("design_liquid_height", design_liquid_height)
    _require_non_negative("corrosion_allowance_bottom", corrosion_allowance_bottom)
    _require_non_negative("shell_design_n18", shell_design_n18)

    minimum_nominal_bottom_plate_thickness = 6  # mm
    bottom_plate_width = 2.5  # m
    bottom_plate_length = 10  # m
    annular_plate_length = 10  # m
    annular_plate_width = 2.5  # m  # stock/purchase width

    annular_plate_material = "S355JR"
    bottom_plate_material = "S355JR"

    annular_plate_density = get_steel_density(annular_plate_material)
    bottom_plate_density = get_steel_density(bottom_plate_material)

    bottom_annular_plate_thickness = max(3 + shell_design_n18 / 3, 6)
    annular_plate_corroded_thickness_mm = math.ceil(
        bottom_annular_plate_thickness + corrosion_allowance_bottom
    )

    minimum_width_ia = max(
        (240 / math.sqrt(design_liquid_height)) * annular_plate_corroded_thickness_mm,
        500,
    )  # mm

    circumference = math.pi * tank_diameter
    number_of_annular_plates = math.ceil(circumference / annular_plate_length)

    single_annular_plate_volume_m3 = (
        annular_plate_width
        * annular_plate_length
        * annular_plate_corroded_thickness_mm
        * 0.001
    )
    total_annular_plate_volume_m3 = single_annular_plate_volume_m3 * number_of_annular_plates

    tank_area = math.pi * (tank_diameter / 2) ** 2
    bottom_plate_area = bottom_plate_width * bottom_plate_length
    number_of_bottom_plates = math.ceil(tank_area / bottom_plate_area) if tank_area > 0 else 0

    bottom_plate_volume_m3 = (
        number_of_bottom_plates
        * bottom_plate_width
        * bottom_plate_length
        * minimum_nominal_bottom_plate_thickness
        * 0.001
    )

    total_annular_plate_mass_kg = total_annular_plate_volume_m3 * annular_plate_density
    total_bottom_plate_mass_kg = bottom_plate_volume_m3 * bottom_plate_density

    return {
        "minimum_nominal_bottom_plate_thickness": minimum_nominal_bottom_plate_thickness,
        "bottom_plate_width": bottom_plate_width,
        "bottom_plate_length": bottom_plate_length,
        "annular_plate_length": annular_plate_length,
        "annular_plate_width": annular_plate_width,
        "annular_plate_material": annular_plate_material,
        "bottom_plate_material": bottom_plate_material,
        "annular_plate_density": annular_plate_density,
        "bottom_plate_density": bottom_plate_density,
        "bottom_annular_plate_thickness": bottom_annular_plate_thickness,
        "annular_plate_corroded_thickness_mm": annular_plate_corroded_thickness_mm,
        "minimum_width_ia": minimum_width_ia,
        "single_annular_plate_volume_m3": single_annular_plate_volume_m3,
        "total_annular_plate_volume_m3": total_annular_plate_volume_m3,
        "number_of_bottom_plates": number_of_bottom_plates,
        "number_of_annular_plates": number_of_annular_plates,
        "bottom_plate_volume_m3": bottom_plate_volume_m3,
        "total_annular_plate_mass_kg": total_annular_plate_mass_kg,
        "total_bottom_plate_mass_kg": total_bottom_plate_mass_kg,
    }


# ----------------------------
# Shell Design
# ----------------------------
def get_shell_material_difference_flags(shell_materials):
    flags = []
    for i, material in enumerate(shell_materials):
        if i == 0:
            flags.append("DIFFERENT MATERIAL")
        elif material != shell_materials[i - 1]:
            flags.append("DIFFERENT MATERIAL")
        else:
            flags.append("SAME MATERIAL")
    return flags


def get_specified_nominal_thickness(tank_diameter, material_type, number_of_courses):
    if material_type in ["Carbon Steel Lap Welded", "Carbon Steel Butt Welded"]:
        if tank_diameter < 30:
            tabulated = 6 if tank_diameter >= 15 else 5
        elif tank_diameter < 60:
            tabulated = 8
        elif tank_diameter < 90:
            tabulated = 10
        else:
            tabulated = 12

    elif material_type == "Stainless Steel Lap Welded":
        if tank_diameter < 4:
            tabulated = 2
        elif tank_diameter < 10:
            tabulated = 3
        elif tank_diameter < 15:
            tabulated = 4
        elif tank_diameter < 30:
            tabulated = 5
        elif tank_diameter < 45:
            tabulated = 6
        else:
            tabulated = None
    else:
        tabulated = None

    if tabulated is None:
        return [None] * number_of_courses

    return [tabulated] * number_of_courses


def is_non_increasing(values):
    clean = [v for v in values if v is not None]
    return all(clean[i + 1] <= clean[i] for i in range(len(clean) - 1))


def get_material_max_thickness(material_name):
    max_thickness_table = {
        "S235JR": 12,
        "S235JO": 30,
        "S275JR": 12,
        "S275JO": 30,
        "S275J2": 40,
        "S275N": 40,
        "S275NL": 40,
        "S275M": 40,
        "S275ML": 40,
        "S355JR": 10,
        "S355JO": 15,
        "P265GH": 30,
        "P295GH": 40,
        "P355GH": 40,
    }

    if material_name not in max_thickness_table:
        raise ValueError(f"No max thickness defined for material: {material_name}")

    return max_thickness_table[material_name]


def _build_shell_geometry(shell_height):
    _require_positive("shell_height", shell_height)

    number_of_courses = math.ceil(shell_height / 3)
    course_height = shell_height / number_of_courses
    course_rows = list(range(1, number_of_courses + 1))
    course_heights = [course_height] * number_of_courses

    bottom_heights = []
    running = 0.0
    for h in course_heights:
        bottom_heights.append(running)
        running += h

    distance_921 = [shell_height - bh for bh in bottom_heights]

    return {
        "number_of_courses": number_of_courses,
        "course_height": course_height,
        "course_rows": course_rows,
        "course_heights": course_heights,
        "distance_921": distance_921,
        "shell_course_plate_length": 3,
    }


def _calculate_shell_core(
    tank_diameter,
    shell_height,
    material_type,
    design_density_operating,
    test_density,
    design_pressure,
    test_pressure,
    shell_corrosion_allowance,
    wind_gust_velocity,
    shell_materials,
):
    _require_positive("tank_diameter", tank_diameter)
    _require_positive("shell_height", shell_height)
    _require_non_negative("design_density_operating", design_density_operating)
    _require_non_negative("test_density", test_density)
    _require_non_negative("design_pressure", design_pressure)
    _require_non_negative("test_pressure", test_pressure)
    _require_non_negative("shell_corrosion_allowance", shell_corrosion_allowance)
    _require_positive("wind_gust_velocity", wind_gust_velocity)

    geometry = _build_shell_geometry(shell_height)
    number_of_courses = geometry["number_of_courses"]
    course_heights = geometry["course_heights"]
    distance_921 = geometry["distance_921"]

    if len(shell_materials) != number_of_courses:
        raise ValueError(
            f"shell_materials length ({len(shell_materials)}) must equal "
            f"number_of_courses ({number_of_courses})"
        )

    densities = [get_steel_density(m) for m in shell_materials]
    allowable_test_stresses = [get_allowable_test_stress(m) for m in shell_materials]
    allowable_design_stresses = [get_allowable_design_stress(m) for m in shell_materials]
    material_flags = get_shell_material_difference_flags(shell_materials)

    test_course_thicknesses = []
    for flag, stress, hc in zip(material_flags, allowable_test_stresses, distance_921):
        hydro_part = hc if flag == "DIFFERENT MATERIAL" else (hc - 0.3)
        value = (tank_diameter / (20 * stress)) * (
            98 * test_density * hydro_part + test_pressure
        )
        test_course_thicknesses.append(value)

    design_course_thicknesses = []
    for flag, stress, hc in zip(material_flags, allowable_design_stresses, distance_921):
        effective_pressure = 0 if design_pressure <= 10 else design_pressure
        hydro_part = hc if flag == "DIFFERENT MATERIAL" else (hc - 0.3)

        value = (
            (tank_diameter / (20 * stress))
            * (98 * design_density_operating * hydro_part + effective_pressure)
            + shell_corrosion_allowance
        )
        design_course_thicknesses.append(value)

    specified_nominal_thicknesses = get_specified_nominal_thickness(
        tank_diameter=tank_diameter,
        material_type=material_type,
        number_of_courses=number_of_courses,
    )

    nominal_thicknesses = []
    for t_test, t_design, t_spec in zip(
        test_course_thicknesses,
        design_course_thicknesses,
        specified_nominal_thicknesses,
    ):
        values = [v for v in [t_test, t_design, t_spec] if v is not None]
        nominal_thicknesses.append(max(values) if values else None)

    course_thicknesses = [
        math.ceil(val) if val is not None else None for val in nominal_thicknesses
    ]

    valid_nominal = [e for e in nominal_thicknesses if e is not None]
    if valid_nominal:
        e_min = valid_nominal[-1]
        q_values = [
            1000 * h * (e_min / e) ** 2.5
            for h, e in zip(course_heights, nominal_thicknesses)
        ]
    else:
        q_values = [None] * number_of_courses

    valid_q = [q for q in q_values if q is not None]
    he = sum(valid_q) * 0.001 if valid_q else None

    denominator = 3.563 * (wind_gust_velocity ** 2) + 580 * test_pressure
    k_factor = 95000 / denominator if denominator != 0 else None

    valid_p = [p for p in course_thicknesses if p is not None]
    if valid_p and k_factor is not None:
        e_min_hp = min(valid_p)
        hp = k_factor * math.sqrt((e_min_hp ** 5) / (tank_diameter ** 3))
    else:
        hp = None

    if hp is None or he is None:
        number_of_2_stiff_rings = None
    elif he < hp:
        number_of_2_stiff_rings = 0
    else:
        number_of_2_stiff_rings = max(1, math.ceil(he / hp) - 1)

    if number_of_2_stiff_rings == 0:
        stiff_ring_locations = []
    elif number_of_2_stiff_rings is None or he is None:
        stiff_ring_locations = None
    else:
        stiff_ring_locations = [
            he * step / (number_of_2_stiff_rings + 1)
            for step in range(1, number_of_2_stiff_rings + 1)
        ]

    return {
        "number_of_courses": geometry["number_of_courses"],
        "course_height": geometry["course_height"],
        "shell_course_plate_length": geometry["shell_course_plate_length"],
        "course_rows": geometry["course_rows"],
        "course_heights": geometry["course_heights"],
        "shell_materials": shell_materials,
        "densities": densities,
        "allowable_test_stresses": allowable_test_stresses,
        "allowable_design_stresses": allowable_design_stresses,
        "distance_921": distance_921,
        "material_flags": material_flags,
        "test_course_thicknesses": test_course_thicknesses,
        "design_course_thicknesses": design_course_thicknesses,
        "specified_nominal_thicknesses": specified_nominal_thicknesses,
        "nominal_thicknesses": nominal_thicknesses,
        "course_thicknesses": course_thicknesses,
        "q_values": q_values,
        "HE": he,
        "K": k_factor,
        "Hp": hp,
        "number_of_2_stiff_rings": number_of_2_stiff_rings,
        "stiff_ring_locations": stiff_ring_locations,
        "material_of_2_stiff_ring": "S355JR",
    }


def calculate_shell_design(
    tank_diameter,
    shell_height,
    material_type,
    design_density_operating,
    test_density,
    design_pressure,
    test_pressure,
    shell_corrosion_allowance,
    wind_gust_velocity,
    shell_materials=None,
):
    _require_positive("shell_height", shell_height)
    number_of_courses = math.ceil(shell_height / 3)

    if shell_materials is None:
        shell_materials = ["S355JR"] * number_of_courses

    return _calculate_shell_core(
        tank_diameter=tank_diameter,
        shell_height=shell_height,
        material_type=material_type,
        design_density_operating=design_density_operating,
        test_density=test_density,
        design_pressure=design_pressure,
        test_pressure=test_pressure,
        shell_corrosion_allowance=shell_corrosion_allowance,
        wind_gust_velocity=wind_gust_velocity,
        shell_materials=shell_materials,
    )


def calculate_shell_for_materials(
    tank_diameter,
    shell_height,
    material_type,
    design_density_operating,
    test_density,
    design_pressure,
    test_pressure,
    shell_corrosion_allowance,
    wind_gust_velocity,
    shell_materials,
):
    result = _calculate_shell_core(
        tank_diameter=tank_diameter,
        shell_height=shell_height,
        material_type=material_type,
        design_density_operating=design_density_operating,
        test_density=test_density,
        design_pressure=design_pressure,
        test_pressure=test_pressure,
        shell_corrosion_allowance=shell_corrosion_allowance,
        wind_gust_velocity=wind_gust_velocity,
        shell_materials=shell_materials,
    )

    course_thicknesses = result["course_thicknesses"]

    if not is_non_increasing(course_thicknesses):
        return None

    for material, thickness in zip(shell_materials, course_thicknesses):
        if thickness is None or thickness > get_material_max_thickness(material):
            return None

    price_factors = {
        "S235JR": 0.85,
        "S235JO": 0.90,
        "S275JR": 0.95,
        "S275JO": 0.96,
        "S275J2": 0.99,
        "S275N": 1.05,
        "S275NL": 1.08,
        "S275M": 1.10,
        "S275ML": 1.12,
        "S355JR": 1.15,
        "S355JO": 1.18,
        "P265GH": 1.12,
        "P295GH": 1.14,
        "P355GH": 1.16,
    }

    cost_score = sum(
        thickness * price_factors[material]
        for material, thickness in zip(shell_materials, course_thicknesses)
    )

    return {
        "shell_materials": shell_materials,
        "course_thicknesses": course_thicknesses,
        "cost_score": cost_score,
    }


def find_cheapest_shell_material_combination(
    tank_diameter,
    shell_height,
    material_type,
    design_density_operating,
    test_density,
    design_pressure,
    test_pressure,
    shell_corrosion_allowance,
    wind_gust_velocity,
    search_mode="two_zone",
):
    """
    search_mode:
        - "uniform": same material in all courses
        - "two_zone": one split between bottom and top materials
        - "full": all per-course combinations (guarded)
    """
    _require_positive("shell_height", shell_height)
    number_of_courses = math.ceil(shell_height / 3)
    allowed_materials = get_shell_course_material_names()
    candidates = []

    if search_mode == "full" and number_of_courses > 5:
        raise ValueError(
            "search_mode='full' is too computationally expensive for this shell height. "
            "Use 'two_zone' or 'uniform'."
        )

    if search_mode == "uniform":
        combinations = ([material] * number_of_courses for material in allowed_materials)

    elif search_mode == "two_zone":
        combo_set = set()

        for material in allowed_materials:
            combo_set.add(tuple([material] * number_of_courses))

        for split in range(1, number_of_courses):
            for bottom_material in allowed_materials:
                for top_material in allowed_materials:
                    combo = tuple(
                        [bottom_material] * split
                        + [top_material] * (number_of_courses - split)
                    )
                    combo_set.add(combo)

        combinations = combo_set

    elif search_mode == "full":
        combinations = product(allowed_materials, repeat=number_of_courses)

    else:
        raise ValueError(
            f"Unknown search_mode '{search_mode}'. Use 'uniform', 'two_zone', or 'full'."
        )

    for combo in combinations:
        combo = list(combo)
        result = calculate_shell_for_materials(
            tank_diameter=tank_diameter,
            shell_height=shell_height,
            material_type=material_type,
            design_density_operating=design_density_operating,
            test_density=test_density,
            design_pressure=design_pressure,
            test_pressure=test_pressure,
            shell_corrosion_allowance=shell_corrosion_allowance,
            wind_gust_velocity=wind_gust_velocity,
            shell_materials=combo,
        )
        if result is not None:
            candidates.append(result)

    if not candidates:
        return None

    return min(candidates, key=lambda x: x["cost_score"])


# ----------------------------
# Fixed Cone Roof Design
# ----------------------------
def _ceiling_to_multiple(value, multiple):
    if multiple <= 0:
        raise ValueError("multiple must be > 0")
    return math.ceil(value / multiple) * multiple


def _roof_geometry(tank_diameter, roof_slope):
    _require_positive("tank_diameter", tank_diameter)
    _require_positive("roof_slope", roof_slope)

    roof_height = roof_slope * tank_diameter / 2
    angle_between_horizontal_and_cone_rad = math.atan(roof_height / (tank_diameter / 2))
    slanted_height = math.sqrt(roof_height ** 2 + (tank_diameter / 2) ** 2)
    roof_area = math.pi * (tank_diameter / 2) * slanted_height

    return {
        "roof_height": roof_height,
        "angle_between_horizontal_and_cone_rad": angle_between_horizontal_and_cone_rad,
        "slanted_height": slanted_height,
        "roof_area": roof_area,
    }


def _roof_plate_design(
    tank_diameter,
    roof_area,
    angle_between_horizontal_and_cone_rad,
    design_pressure,
    live_loads,
    snow_loads,
    insulation_loads,
    roof_plate_material="S235JR",
):
    _require_positive("tank_diameter", tank_diameter)
    _require_non_negative("design_pressure", design_pressure)
    _require_non_negative("live_loads", live_loads)
    _require_non_negative("snow_loads", snow_loads)
    _require_non_negative("insulation_loads", insulation_loads)

    roof_plate_thickness = 5  # mm
    roof_plate_width = 2  # m
    roof_plate_length = 8  # m
    joint_efficiency_factor = 0.5

    allowable_design_stress_roof_plate = (2 / 3) * get_steel_yield(roof_plate_material)
    distributed_load_case = live_loads + snow_loads + insulation_loads

    number_of_plates = math.ceil(roof_area / (roof_plate_width * roof_plate_length))

    density = get_steel_density(roof_plate_material)
    weight_of_roof_plates = (roof_plate_thickness * 0.001 * density * 9.81) / 1000

    angle_deg = math.degrees(angle_between_horizontal_and_cone_rad)
    denom = 120 * angle_deg

    compression_area = None
    if denom != 0:
        compression_area = 50 * (design_pressure - weight_of_roof_plates * 10) / denom

    return {
        "roof_plate_material": roof_plate_material,
        "roof_plate_thickness": roof_plate_thickness,
        "allowable_design_stress_roof_plate": allowable_design_stress_roof_plate,
        "distributed_load_case": distributed_load_case,
        "roof_area": roof_area,
        "roof_plate_width": roof_plate_width,
        "roof_plate_length": roof_plate_length,
        "joint_efficiency_factor": joint_efficiency_factor,
        "number_of_plates": number_of_plates,
        "weight_of_roof_plates": weight_of_roof_plates,
        "compression_area": compression_area,
    }


def _bracing_design(tank_diameter):
    _require_positive("tank_diameter", tank_diameter)

    is_bracing_necessary = "YES" if tank_diameter > 15 else "NO"

    if tank_diameter <= 30:
        number_of_wind_bracing_sections = 4
    elif tank_diameter <= 40:
        number_of_wind_bracing_sections = 5
    elif tank_diameter <= 48:
        number_of_wind_bracing_sections = 6
    else:
        number_of_wind_bracing_sections = 8

    return {
        "is_bracing_necessary": is_bracing_necessary,
        "number_of_wind_bracing_sections": number_of_wind_bracing_sections,
    }


def _rafter_design(
    tank_diameter,
    slanted_height,
    ipe_name,
    supporting_material="S235JR",
):
    _require_positive("tank_diameter", tank_diameter)
    _require_positive("slanted_height", slanted_height)

    profile = get_ipe_profile(ipe_name)
    allowable_design_stress_supporting_material = (2 / 3) * get_steel_yield(supporting_material)

    number_of_rafters = _ceiling_to_multiple(tank_diameter * math.pi / 2, 4)
    angle_between_rafters_deg = 360 / number_of_rafters if number_of_rafters else None

    actual_distance_between_support_beams = (
        math.pi * tank_diameter / number_of_rafters if number_of_rafters else None
    )

    rafter_length = slanted_height
    rafter_cross_section_area = profile["area_m2"]

    density = get_steel_density(supporting_material)
    mass_of_one_rafter = rafter_length * rafter_cross_section_area * density
    total_rafter_mass = mass_of_one_rafter * number_of_rafters

    return {
        "supporting_material": supporting_material,
        "allowable_design_stress_supporting_material": allowable_design_stress_supporting_material,
        "number_of_rafters": number_of_rafters,
        "angle_between_rafters_deg": angle_between_rafters_deg,
        "actual_distance_between_support_beams": actual_distance_between_support_beams,
        "rafter_length": rafter_length,
        "rafter_cross_section_area": rafter_cross_section_area,
        "mass_of_one_rafter": mass_of_one_rafter,
        "total_rafter_mass": total_rafter_mass,
        "profile": profile,
    }


def _rafter_bending_analysis(
    roof_area,
    distributed_load_case,
    rafter_design,
):
    number_of_rafters = rafter_design["number_of_rafters"]
    load_bearing_length = rafter_design["rafter_length"]
    mass_of_one_rafter = rafter_design["mass_of_one_rafter"]
    wel_z_mm3 = rafter_design["profile"]["wel_z_mm3"]
    allowable_stress = rafter_design["allowable_design_stress_supporting_material"]

    roof_area_per_beam = roof_area / number_of_rafters if number_of_rafters else None
    total_load_per_roof_area = (
        roof_area_per_beam * distributed_load_case
        if roof_area_per_beam is not None
        else None
    )

    force_per_length = (
        2 * total_load_per_roof_area / load_bearing_length
        if total_load_per_roof_area is not None and load_bearing_length not in [0, None]
        else None
    )

    weight_of_support_beam_per_length = (
        (mass_of_one_rafter * 9.81 / load_bearing_length) / 1000
        if load_bearing_length not in [0, None]
        else None
    )

    total_load_on_support_beam = (
        force_per_length + weight_of_support_beam_per_length
        if force_per_length is not None and weight_of_support_beam_per_length is not None
        else None
    )

    vertical_force_on_support_beam = (
        total_load_on_support_beam * load_bearing_length / 2
        if total_load_on_support_beam is not None and load_bearing_length is not None
        else None
    )

    reaction_force_a = (
        total_load_on_support_beam * load_bearing_length / 6
        if total_load_on_support_beam is not None and load_bearing_length is not None
        else None
    )

    reaction_force_b = (
        total_load_on_support_beam * load_bearing_length / 3
        if total_load_on_support_beam is not None and load_bearing_length is not None
        else None
    )

    bending_moment_nmm = (
        0.128 * vertical_force_on_support_beam * 1_000_000 * load_bearing_length
        if vertical_force_on_support_beam is not None and load_bearing_length is not None
        else None
    )

    bending_stress_mpa = (
        bending_moment_nmm / wel_z_mm3
        if bending_moment_nmm is not None and wel_z_mm3 not in [0, None]
        else None
    )

    bending_status = (
        "SAFE"
        if bending_stress_mpa is not None and bending_stress_mpa < allowable_stress
        else "NOT SAFE"
    )

    return {
        "roof_area_per_beam": roof_area_per_beam,
        "load_bearing_length": load_bearing_length,
        "total_load_per_roof_area": total_load_per_roof_area,
        "force_per_length": force_per_length,
        "weight_of_support_beam_per_length": weight_of_support_beam_per_length,
        "total_load_on_support_beam": total_load_on_support_beam,
        "vertical_force_on_support_beam": vertical_force_on_support_beam,
        "reaction_force_a": reaction_force_a,
        "reaction_force_b": reaction_force_b,
        "bending_moment_nmm": bending_moment_nmm,
        "bending_stress_mpa": bending_stress_mpa,
        "bending_status": bending_status,
    }


def _rafter_buckling_analysis(
    angle_between_horizontal_and_cone_rad,
    rafter_design,
    bending_analysis,
    bracing_design,
):
    profile = rafter_design["profile"]
    allowable_stress = rafter_design["allowable_design_stress_supporting_material"]
    provided_bracing = bracing_design["number_of_wind_bracing_sections"]
    supporting_factor = 0.7
    rafter_length = rafter_design["rafter_length"]

    buckling_length_mm = (
        supporting_factor * rafter_length * 1000 / (provided_bracing + 1)
        if provided_bracing is not None
        else None
    )

    vertical_force_on_support_beam = bending_analysis["vertical_force_on_support_beam"]

    buckling_force_in_beam_n = (
        vertical_force_on_support_beam * 1000 / (2 * math.sin(angle_between_horizontal_and_cone_rad))
        if vertical_force_on_support_beam not in [None, 0]
        and math.sin(angle_between_horizontal_and_cone_rad) != 0
        else None
    )

    slenderness_z_mm = math.sqrt(profile["iz_mm4"] / profile["area_mm2"])
    slenderness_y_mm = math.sqrt(profile["iy_mm4"] / profile["area_mm2"])

    lambda_y = (
        buckling_length_mm / slenderness_y_mm
        if buckling_length_mm not in [None, 0]
        else None
    )

    lambda_z = (
        buckling_length_mm / slenderness_z_mm
        if buckling_length_mm not in [None, 0]
        else None
    )

    omega_yy = profile["omega_yy"]
    omega_zz = profile["omega_zz"]

    buckling_stress_y_mpa = (
        omega_yy * buckling_force_in_beam_n / profile["area_mm2"]
        if buckling_force_in_beam_n is not None
        else None
    )

    buckling_stress_z_mpa = (
        omega_zz * buckling_force_in_beam_n / profile["area_mm2"]
        if buckling_force_in_beam_n is not None
        else None
    )

    youngs_modulus = get_youngs_modulus_mpa()

    critical_buckling_stress_y_mpa = (
        (math.pi ** 2) * youngs_modulus / (lambda_y ** 2)
        if lambda_y not in [None, 0]
        else None
    )

    critical_buckling_stress_z_mpa = (
        (math.pi ** 2) * youngs_modulus / (lambda_z ** 2)
        if lambda_z not in [None, 0]
        else None
    )

    buckling_y_status = (
        "SAFE"
        if buckling_stress_y_mpa is not None
        and critical_buckling_stress_y_mpa is not None
        and buckling_stress_y_mpa < critical_buckling_stress_y_mpa
        else "NOT SAFE"
    )

    buckling_z_status = (
        "SAFE"
        if buckling_stress_z_mpa is not None
        and critical_buckling_stress_z_mpa is not None
        and buckling_stress_z_mpa < critical_buckling_stress_z_mpa
        else "NOT SAFE"
    )

    bending_stress = bending_analysis["bending_stress_mpa"]

    interaction_y = None
    if (
        bending_stress is not None
        and allowable_stress not in [None, 0]
        and buckling_stress_y_mpa is not None
        and critical_buckling_stress_y_mpa not in [None, 0]
    ):
        interaction_y = (bending_stress / allowable_stress) + (
            buckling_stress_y_mpa / critical_buckling_stress_y_mpa
        )

    interaction_z = None
    if (
        bending_stress is not None
        and allowable_stress not in [None, 0]
        and buckling_stress_z_mpa is not None
        and critical_buckling_stress_z_mpa not in [None, 0]
    ):
        interaction_z = (bending_stress / allowable_stress) + (
            buckling_stress_z_mpa / critical_buckling_stress_z_mpa
        )

    interaction_y_status = "SAFE" if interaction_y is not None and interaction_y < 1 else "NOT SAFE"
    interaction_z_status = "SAFE" if interaction_z is not None and interaction_z < 1 else "NOT SAFE"

    overall_roof_safety = (
        "SAFE"
        if (
            bending_analysis["bending_status"] == "SAFE"
            and buckling_y_status == "SAFE"
            and buckling_z_status == "SAFE"
            and interaction_y_status == "SAFE"
            and interaction_z_status == "SAFE"
        )
        else "NOT SAFE"
    )

    return {
        "provided_bracing": provided_bracing,
        "supporting_factor": supporting_factor,
        "buckling_length_mm": buckling_length_mm,
        "buckling_force_in_beam_n": buckling_force_in_beam_n,
        "slenderness_z_mm": slenderness_z_mm,
        "slenderness_y_mm": slenderness_y_mm,
        "lambda_y": lambda_y,
        "lambda_z": lambda_z,
        "omega_yy": omega_yy,
        "omega_zz": omega_zz,
        "buckling_stress_y_mpa": buckling_stress_y_mpa,
        "critical_buckling_stress_y_mpa": critical_buckling_stress_y_mpa,
        "buckling_y_status": buckling_y_status,
        "buckling_stress_z_mpa": buckling_stress_z_mpa,
        "critical_buckling_stress_z_mpa": critical_buckling_stress_z_mpa,
        "buckling_z_status": buckling_z_status,
        "interaction_y": interaction_y,
        "interaction_y_status": interaction_y_status,
        "interaction_z": interaction_z,
        "interaction_z_status": interaction_z_status,
        "overall_roof_safety": overall_roof_safety,
    }


def calculate_fixed_cone_roof(
    tank_diameter,
    design_pressure,
    live_loads,
    snow_loads,
    insulation_loads,
    roof_slope=0.2,
    roof_plate_material="S235JR",
    supporting_material="S235JR",
    rafter_type=None,
):
    geometry = _roof_geometry(
        tank_diameter=tank_diameter,
        roof_slope=roof_slope,
    )

    roof_plate = _roof_plate_design(
        tank_diameter=tank_diameter,
        roof_area=geometry["roof_area"],
        angle_between_horizontal_and_cone_rad=geometry["angle_between_horizontal_and_cone_rad"],
        design_pressure=design_pressure,
        live_loads=live_loads,
        snow_loads=snow_loads,
        insulation_loads=insulation_loads,
        roof_plate_material=roof_plate_material,
    )

    bracing = _bracing_design(tank_diameter=tank_diameter)

    if rafter_type is None:
        rafter_type = "IPE200"

    rafter = _rafter_design(
        tank_diameter=tank_diameter,
        slanted_height=geometry["slanted_height"],
        ipe_name=rafter_type,
        supporting_material=supporting_material,
    )

    bending = _rafter_bending_analysis(
        roof_area=geometry["roof_area"],
        distributed_load_case=roof_plate["distributed_load_case"],
        rafter_design=rafter,
    )

    buckling = _rafter_buckling_analysis(
        angle_between_horizontal_and_cone_rad=geometry["angle_between_horizontal_and_cone_rad"],
        rafter_design=rafter,
        bending_analysis=bending,
        bracing_design=bracing,
    )

    crown_ring_type = get_crown_ring_for_rafter(rafter_type)
    crown_ring_diameter_mm = tank_diameter * 0.1 * 1000

    return {
        "rafter_type": rafter_type,
        "number_of_rafters": rafter["number_of_rafters"],
        "status": buckling["overall_roof_safety"],
        "crown_ring_type": crown_ring_type,
        "crown_ring_diameter_mm": crown_ring_diameter_mm,
        "geometry": geometry,
        "roof_plate": roof_plate,
        "bracing": bracing,
        "rafter": rafter,
        "bending": bending,
        "buckling": buckling,
    }


def find_lightest_safe_fixed_cone_roof_rafter(
    tank_diameter,
    design_pressure,
    live_loads,
    snow_loads,
    insulation_loads,
    roof_slope=0.2,
    roof_plate_material="S235JR",
    supporting_material="S235JR",
):
    candidates = []

    for ipe_name in get_ipe_profile_names():
        result = calculate_fixed_cone_roof(
            tank_diameter=tank_diameter,
            design_pressure=design_pressure,
            live_loads=live_loads,
            snow_loads=snow_loads,
            insulation_loads=insulation_loads,
            roof_slope=roof_slope,
            roof_plate_material=roof_plate_material,
            supporting_material=supporting_material,
            rafter_type=ipe_name,
        )

        if result["status"] == "SAFE":
            mass = result["rafter"]["profile"]["mass_kg_m"]
            candidates.append((mass, result))

    if not candidates:
        return {
            "rafter_type": None,
            "number_of_rafters": None,
            "status": "NOT SAFE",
        }

    _, best = min(candidates, key=lambda x: x[0])

    return {
        "rafter_type": best["rafter_type"],
        "number_of_rafters": best["number_of_rafters"],
        "status": best["status"],
        "crown_ring_type": best["crown_ring_type"],
        "details": best,
    }


# ----------------------------
# Bottom Cost Design
# ----------------------------
def _roundup_excel(value, digits=0):
    factor = 10 ** digits
    return math.ceil(value * factor) / factor


def _get_material_price_factor(material_name):
    material_price_factors = {
        "S235JR": 0.85,
        "S235JO": 0.90,
        "S235J2G3": 0.92,
        "S235J2G4": 0.93,
        "S275JR": 0.95,
        "S275JO": 0.96,
        "S275J2": 0.98,
        "S275N": 1.05,
        "S275NL": 1.08,
        "S275M": 1.10,
        "S275ML": 1.12,
        "S355JR": 1.15,
        "S355JO": 1.18,
        "S355J2": 1.20,
        "S355K2": 1.24,
        "S355N": 1.30,
        "S355NL": 1.32,
        "S355M": 1.35,
        "S355ML": 1.38,
        "S420N": 1.45,
        "S420NL": 1.48,
        "S420M": 1.50,
        "S420ML": 1.52,
        "P235GH": 1.10,
        "P265GH": 1.12,
        "P295GH": 1.14,
        "P355GH": 1.16,
        "P275NH": 1.18,
        "P275NL2": 1.20,
        "P355NH": 1.22,
        "P355NL2": 1.25,
    }
    return material_price_factors.get(material_name, 1.0)


def _xlookup_weld_time_butt(thickness_mm):
    butt_weld_hours_per_meter = {
        6: 0.7,
        7: 0.8,
        8: 1.0,
        9: 1.1,
        10: 1.4,
        11: 1.7,
        12: 1.9,
        13: 2.2,
        14: 2.0,
        15: 2.2,
        16: 2.4,
        17: 2.6,
        18: 2.9,
        19: 3.1,
        20: 3.4,
        21: 3.7,
        22: 4.0,
        23: 4.3,
        24: 4.6,
        25: 4.9,
        26: 5.3,
        27: 5.6,
        28: 5.9,
        29: 6.3,
        30: 6.7,
        31: 7.1,
        32: 7.5,
    }

    t = int(_roundup_excel(thickness_mm, 0))
    keys = sorted(butt_weld_hours_per_meter.keys())
    eligible = [k for k in keys if k <= t]
    if not eligible:
        return butt_weld_hours_per_meter[keys[0]]
    return butt_weld_hours_per_meter[max(eligible)]


def _xlookup_weld_time_lap(a_mm):
    lap_weld_hours_per_meter = {
        3: 0.25,
        4: 0.40,
        5: 0.50,
        6: 0.75,
        7: 1.00,
        8: 1.30,
        9: 1.60,
        10: 1.90,
        11: 2.30,
    }

    a = int(_roundup_excel(a_mm, 0))
    keys = sorted(lap_weld_hours_per_meter.keys())
    eligible = [k for k in keys if k <= a]
    if not eligible:
        return lap_weld_hours_per_meter[keys[0]]
    return lap_weld_hours_per_meter[max(eligible)]


def _get_welding_factor(label):
    welding_factors = {
        "L1": 1.0,
        "L2": 1.3,
        "L3": 1.9,
        "L4": 2.0,
    }
    return welding_factors.get(str(label).strip().upper(), 1.0)


def calculate_bottom_cost(inputs, bottom_result):
    base_steel_cost_eur_per_kg = 0.85
    welder_hourly_rate_eur_per_hour = 67.7
    shop_hourly_rate_eur_per_hour = 82.0
    shop_hours_bottom_sketch_hour_per_tonne = 1.66
    shop_hours_bottom_annular_hour_per_tonne = 3.26
    price_per_anchor_point_eur = 550.0
    cutting_cost_eur_per_tonne = 150.0

    annular_weld_class = "L1"
    shell_bottom_weld_class = "L1"

    tank_diameter = inputs["tank_diameter"]
    _require_positive("tank_diameter", tank_diameter)

    annular_material = bottom_result["annular_plate_material"]
    bottom_material = bottom_result["bottom_plate_material"]

    annular_density = get_steel_density(annular_material)
    bottom_density = get_steel_density(bottom_material)

    annular_material_factor = _get_material_price_factor(annular_material)
    bottom_material_factor = _get_material_price_factor(bottom_material)

    annular_material_cost_per_kg = base_steel_cost_eur_per_kg * annular_material_factor
    bottom_material_cost_per_kg = base_steel_cost_eur_per_kg * bottom_material_factor

    number_of_bottom_plates = _roundup_excel(
        math.pi * (tank_diameter / 2) ** 2
        / (bottom_result["bottom_plate_width"] * bottom_result["bottom_plate_length"]),
        0,
    )

    annular_plate_thickness = bottom_result["annular_plate_corroded_thickness_mm"]

    number_of_annular_plates = _roundup_excel(
        (math.pi * tank_diameter) / bottom_result["annular_plate_length"],
        0,
    )

    bottom_plate_width = bottom_result["bottom_plate_width"]
    bottom_plate_length = bottom_result["bottom_plate_length"]
    bottom_plate_thickness = bottom_result["minimum_nominal_bottom_plate_thickness"]

    annular_plate_width = bottom_result["annular_plate_width"]
    annular_plate_length = bottom_result["annular_plate_length"]

    volume_of_annular_plates = (
        number_of_annular_plates
        * annular_plate_width
        * annular_plate_length
        * annular_plate_thickness
        * 0.001
    )

    volume_of_bottom_plates = (
        number_of_bottom_plates
        * bottom_plate_width
        * bottom_plate_length
        * bottom_plate_thickness
        * 0.001
    )

    cost_of_bottom_plates = bottom_density * bottom_material_cost_per_kg * volume_of_bottom_plates
    cost_of_annular_plates = annular_density * annular_material_cost_per_kg * volume_of_annular_plates
    total_material_cost = cost_of_bottom_plates + cost_of_annular_plates

    mass_of_bottom_plates_kg = bottom_density * volume_of_bottom_plates
    mass_of_annular_plates_kg = annular_density * volume_of_annular_plates

    cutting_cost_bottom_plates = cutting_cost_eur_per_tonne * mass_of_bottom_plates_kg / 1000
    cutting_cost_annular_plates = cutting_cost_eur_per_tonne * mass_of_annular_plates_kg / 1000

    shop_hours_annular = shop_hours_bottom_annular_hour_per_tonne * mass_of_annular_plates_kg / 1000
    shop_hours_bottom = shop_hours_bottom_sketch_hour_per_tonne * mass_of_bottom_plates_kg / 1000

    bottom_shop_hours = shop_hours_annular + shop_hours_bottom
    bottom_shop_cost = bottom_shop_hours * shop_hourly_rate_eur_per_hour

    total_shop_cost = (
        cutting_cost_bottom_plates
        + cutting_cost_annular_plates
        + bottom_shop_cost
    )

    number_of_anchor_points = _roundup_excel((1 / 3) * math.pi * tank_diameter, 0)
    total_anchor_price = number_of_anchor_points * price_per_anchor_point_eur

    annular_weld_meters = number_of_annular_plates * annular_plate_width
    annular_time_per_meter = _xlookup_weld_time_butt(annular_plate_thickness)
    annular_welding_factor = _get_welding_factor(annular_weld_class)
    annular_total_welding_time = (
        annular_weld_meters * annular_time_per_meter * annular_welding_factor
    )

    annular_to_bottom_weld_meters = math.pi * tank_diameter
    annular_to_bottom_a = _roundup_excel(0.5 * annular_plate_thickness * math.sqrt(2), 0)
    annular_to_bottom_time_per_meter = _xlookup_weld_time_lap(annular_to_bottom_a)
    annular_to_bottom_total_welding_time = (
        annular_to_bottom_weld_meters * annular_to_bottom_time_per_meter
    )

    bottom_weld_meters = (
        0.5 * (bottom_plate_width + bottom_plate_length) * number_of_bottom_plates
        + math.pi * tank_diameter
    )
    bottom_weld_a = _roundup_excel(0.5 * bottom_plate_thickness * math.sqrt(2), 0)
    bottom_weld_time_per_meter = _xlookup_weld_time_lap(bottom_weld_a)
    bottom_total_welding_time = bottom_weld_meters * bottom_weld_time_per_meter

    shell_bottom_a = _roundup_excel(0.5 * annular_plate_thickness * math.sqrt(2), 0)
    shell_bottom_time_per_meter = _xlookup_weld_time_lap(shell_bottom_a)
    shell_bottom_factor = _get_welding_factor(shell_bottom_weld_class)
    shell_bottom_total_welding_time = (
        2 * shell_bottom_time_per_meter * math.pi * tank_diameter * shell_bottom_factor
    )

    total_welding_time = (
        annular_total_welding_time
        + annular_to_bottom_total_welding_time
        + bottom_total_welding_time
        + shell_bottom_total_welding_time
    )

    cost_of_welding = total_welding_time * welder_hourly_rate_eur_per_hour

    total_cost = (
        total_material_cost
        + total_shop_cost
        + total_anchor_price
        + cost_of_welding
    )

    total_bottom_hours = total_welding_time + bottom_shop_hours
    total_bottom_site_hours = total_welding_time
    total_bottom_shop_hours = bottom_shop_hours

    return {
        "annular_material_cost_per_kg": annular_material_cost_per_kg,
        "bottom_material_cost_per_kg": bottom_material_cost_per_kg,
        "annular_material_factor": annular_material_factor,
        "bottom_material_factor": bottom_material_factor,
        "annular_density": annular_density,
        "bottom_density": bottom_density,
        "number_of_bottom_plates": number_of_bottom_plates,
        "number_of_annular_plates": number_of_annular_plates,
        "volume_of_annular_plates": volume_of_annular_plates,
        "volume_of_bottom_plates": volume_of_bottom_plates,
        "cost_of_bottom_plates": cost_of_bottom_plates,
        "cost_of_annular_plates": cost_of_annular_plates,
        "total_material_cost": total_material_cost,
        "mass_of_bottom_plates_kg": mass_of_bottom_plates_kg,
        "cutting_cost_bottom_plates": cutting_cost_bottom_plates,
        "mass_of_annular_plates_kg": mass_of_annular_plates_kg,
        "cutting_cost_annular_plates": cutting_cost_annular_plates,
        "shop_hours_annular": shop_hours_annular,
        "shop_hours_bottom": shop_hours_bottom,
        "bottom_shop_hours": bottom_shop_hours,
        "bottom_shop_cost": bottom_shop_cost,
        "total_shop_cost": total_shop_cost,
        "number_of_anchor_points": number_of_anchor_points,
        "price_per_anchor_point_eur": price_per_anchor_point_eur,
        "total_anchor_price": total_anchor_price,
        "annular_weld_meters": annular_weld_meters,
        "annular_time_per_meter": annular_time_per_meter,
        "annular_welding_factor": annular_welding_factor,
        "annular_total_welding_time": annular_total_welding_time,
        "annular_to_bottom_weld_meters": annular_to_bottom_weld_meters,
        "annular_to_bottom_a": annular_to_bottom_a,
        "annular_to_bottom_time_per_meter": annular_to_bottom_time_per_meter,
        "annular_to_bottom_total_welding_time": annular_to_bottom_total_welding_time,
        "bottom_weld_meters": bottom_weld_meters,
        "bottom_weld_a": bottom_weld_a,
        "bottom_weld_time_per_meter": bottom_weld_time_per_meter,
        "bottom_total_welding_time": bottom_total_welding_time,
        "shell_bottom_a": shell_bottom_a,
        "shell_bottom_time_per_meter": shell_bottom_time_per_meter,
        "shell_bottom_factor": shell_bottom_factor,
        "shell_bottom_total_welding_time": shell_bottom_total_welding_time,
        "total_welding_time": total_welding_time,
        "cost_of_welding": cost_of_welding,
        "total_bottom_hours": total_bottom_hours,
        "total_bottom_site_hours": total_bottom_site_hours,
        "total_bottom_shop_hours": total_bottom_shop_hours,
        "total_cost": total_cost,
    }


# ----------------------------
# Shell Cost Design
# ----------------------------
def _xlookup_material_density_and_price(material_name):
    material_data = {
        "S235JR": {"density": 7850, "price_factor": 0.85},
        "S235JO": {"density": 7850, "price_factor": 0.90},
        "S235J2G3": {"density": 7800, "price_factor": 0.92},
        "S235J2G4": {"density": 7800, "price_factor": 0.93},
        "S275JR": {"density": 7800, "price_factor": 0.95},
        "S275JO": {"density": 7900, "price_factor": 0.96},
        "S275J2": {"density": 7850, "price_factor": 0.98},
        "S275N": {"density": 7850, "price_factor": 1.05},
        "S275NL": {"density": 7850, "price_factor": 1.08},
        "S275M": {"density": 7850, "price_factor": 1.10},
        "S275ML": {"density": 7850, "price_factor": 1.12},
        "S355JR": {"density": 7800, "price_factor": 1.15},
        "S355JO": {"density": 7800, "price_factor": 1.18},
        "S355J2": {"density": 7850, "price_factor": 1.20},
        "S355K2": {"density": 7850, "price_factor": 1.24},
        "S355N": {"density": 7850, "price_factor": 1.30},
        "S355NL": {"density": 7850, "price_factor": 1.32},
        "S355M": {"density": 7850, "price_factor": 1.35},
        "S355ML": {"density": 7850, "price_factor": 1.38},
        "S420N": {"density": 7850, "price_factor": 1.45},
        "S420NL": {"density": 7850, "price_factor": 1.48},
        "S420M": {"density": 7850, "price_factor": 1.50},
        "S420ML": {"density": 7850, "price_factor": 1.52},
        "P235GH": {"density": 7850, "price_factor": 1.10},
        "P265GH": {"density": 7850, "price_factor": 1.12},
        "P295GH": {"density": 7850, "price_factor": 1.14},
        "P355GH": {"density": 7850, "price_factor": 1.16},
        "P275NH": {"density": 7850, "price_factor": 1.18},
        "P275NL2": {"density": 7850, "price_factor": 1.20},
        "P355NH": {"density": 7850, "price_factor": 1.22},
        "P355NL2": {"density": 7850, "price_factor": 1.25},
    }

    if material_name not in material_data:
        return {
            "density": get_steel_density(material_name),
            "price_factor": _get_material_price_factor(material_name),
        }

    return material_data[material_name]


def get_top_angle_dimensions(tank_diameter):
    if tank_diameter in [None, ""]:
        return {"leg_a_mm": None, "leg_b_mm": None, "thickness_mm": None}

    _require_positive("tank_diameter", tank_diameter)

    if tank_diameter <= 20:
        leg_a_mm = 60
        leg_b_mm = 60
    elif tank_diameter <= 36:
        leg_a_mm = 80
        leg_b_mm = 80
    elif tank_diameter <= 48:
        leg_a_mm = 100
        leg_b_mm = 100
    else:
        leg_a_mm = 150
        leg_b_mm = 150

    if tank_diameter <= 10:
        thickness_mm = 6
    elif tank_diameter <= 20:
        thickness_mm = 8
    elif tank_diameter <= 36:
        thickness_mm = 10
    elif tank_diameter <= 48:
        thickness_mm = 12
    else:
        thickness_mm = 12

    return {
        "leg_a_mm": leg_a_mm,
        "leg_b_mm": leg_b_mm,
        "thickness_mm": thickness_mm,
    }


def get_wind_girder_dimensions(tank_diameter):
    if tank_diameter in [None, ""]:
        return {"leg_a_mm": None, "leg_b_mm": None, "thickness_mm": None}

    _require_positive("tank_diameter", tank_diameter)

    if tank_diameter <= 20:
        leg_a_mm = 100
        leg_b_mm = 65
        thickness_mm = 8
    elif tank_diameter <= 36:
        leg_a_mm = 120
        leg_b_mm = 80
        thickness_mm = 10
    elif tank_diameter <= 48:
        leg_a_mm = 150
        leg_b_mm = 90
        thickness_mm = 10
    else:
        leg_a_mm = 200
        leg_b_mm = 100
        thickness_mm = 12

    return {
        "leg_a_mm": leg_a_mm,
        "leg_b_mm": leg_b_mm,
        "thickness_mm": thickness_mm,
    }


def calculate_shell_cost(inputs, best_shell, shell_result):
    base_steel_cost_eur_per_kg = 0.85
    welder_hourly_rate_eur_per_hour = 67.7
    shop_hourly_rate_eur_per_hour = 82.0
    course_manipulation_hours_per_tonne = 4.0
    secondary_ring_shop_hours_per_tonne = 67.0
    top_angle_shop_hours_per_tonne = 43.0
    shell_plate_shop_hours_per_tonne = 3.16
    vertical_weld_factor = 1.3
    shell_course_plate_length = 3.0
    vertical_plate_count_per_course = 7

    tank_diameter = inputs["tank_diameter"]
    shell_height = inputs["shell_height"]

    _require_positive("tank_diameter", tank_diameter)
    _require_positive("shell_height", shell_height)

    shell_materials = best_shell["shell_materials"]
    course_thicknesses = best_shell["course_thicknesses"]
    course_heights = shell_result["course_heights"]

    if not (len(shell_materials) == len(course_thicknesses) == len(course_heights)):
        raise ValueError("Shell cost input lengths do not match.")

    circumference = math.pi * tank_diameter

    course_rows = []
    total_material_cost = 0.0
    total_circ_weld_cost = 0.0
    total_vertical_weld_cost = 0.0
    total_manipulation_hours = 0.0
    total_shell_weight_kg = 0.0
    total_circ_weld_hours = 0.0
    total_vertical_weld_hours = 0.0

    for i, (material, thickness, course_height) in enumerate(
        zip(shell_materials, course_thicknesses, course_heights), start=1
    ):
        props = _xlookup_material_density_and_price(material)
        density = props["density"]
        price_factor = props["price_factor"]
        price_per_kg = base_steel_cost_eur_per_kg * price_factor

        weight_kg = circumference * course_height * (thickness * 0.001) * density
        course_material_cost = weight_kg * price_per_kg

        weld_factor_per_meter = _xlookup_weld_time_butt(thickness)

        circumferential_weld_length_m = (
            circumference * ((course_height / shell_course_plate_length) + 1)
        )
        circumferential_weld_hours = weld_factor_per_meter * circumferential_weld_length_m
        circumferential_weld_cost = circumferential_weld_hours * welder_hourly_rate_eur_per_hour

        vertical_weld_length_m = course_height * vertical_plate_count_per_course
        vertical_weld_hours = weld_factor_per_meter * vertical_weld_length_m * vertical_weld_factor
        vertical_weld_cost = vertical_weld_hours * welder_hourly_rate_eur_per_hour

        manipulation_hours = course_manipulation_hours_per_tonne * weight_kg / 1000

        total_material_cost += course_material_cost
        total_circ_weld_cost += circumferential_weld_cost
        total_vertical_weld_cost += vertical_weld_cost
        total_manipulation_hours += manipulation_hours
        total_shell_weight_kg += weight_kg
        total_circ_weld_hours += circumferential_weld_hours
        total_vertical_weld_hours += vertical_weld_hours

        course_rows.append(
            {
                "course_number": i,
                "material": material,
                "thickness_mm": thickness,
                "density_kg_m3": density,
                "price_factor": price_factor,
                "price_per_kg_eur": price_per_kg,
                "weight_kg": weight_kg,
                "material_cost_eur": course_material_cost,
                "weld_factor_hr_per_m": weld_factor_per_meter,
                "circ_weld_length_m": circumferential_weld_length_m,
                "circ_weld_hours": circumferential_weld_hours,
                "circ_weld_cost_eur": circumferential_weld_cost,
                "vertical_weld_length_m": vertical_weld_length_m,
                "vertical_weld_hours": vertical_weld_hours,
                "vertical_weld_cost_eur": vertical_weld_cost,
                "manipulation_hours": manipulation_hours,
            }
        )

    top_angle_dims = get_top_angle_dimensions(tank_diameter)
    top_angle_leg_a_mm = top_angle_dims["leg_a_mm"]
    top_angle_leg_b_mm = top_angle_dims["leg_b_mm"]
    top_angle_thickness_mm = top_angle_dims["thickness_mm"]

    top_angle_material = "S355JR"
    top_angle_props = _xlookup_material_density_and_price(top_angle_material)
    top_angle_density = top_angle_props["density"]
    top_angle_price_per_kg = base_steel_cost_eur_per_kg * top_angle_props["price_factor"]

    top_angle_mass_kg = (
        math.pi
        * tank_diameter
        * (((top_angle_thickness_mm + top_angle_leg_b_mm) * 0.001) * (top_angle_leg_a_mm * 0.001))
        * top_angle_density
    )

    top_angle_material_cost_eur = top_angle_mass_kg * top_angle_price_per_kg

    top_angle_lap_weld_hours = (
        2 * math.pi * tank_diameter * _xlookup_weld_time_lap(top_angle_thickness_mm)
    )
    top_angle_weld_cost_eur = top_angle_lap_weld_hours * welder_hourly_rate_eur_per_hour
    total_top_angle_cost_eur = top_angle_material_cost_eur + top_angle_weld_cost_eur

    number_of_stiffening_rings = shell_result.get("number_of_2_stiff_rings", 0) or 0

    wind_girder_dims = get_wind_girder_dimensions(tank_diameter)
    secondary_ring_leg_a_mm = wind_girder_dims["leg_a_mm"]
    secondary_ring_leg_b_mm = wind_girder_dims["leg_b_mm"]
    secondary_ring_thickness_mm = wind_girder_dims["thickness_mm"]

    secondary_ring_mass_single_kg = (
        math.pi
        * tank_diameter
        * (((secondary_ring_thickness_mm + secondary_ring_leg_b_mm) * 0.001) * (secondary_ring_leg_a_mm * 0.001))
        * top_angle_density
    )

    secondary_ring_unit_price_per_kg = top_angle_price_per_kg
    secondary_ring_material_cost_single_eur = (
        secondary_ring_mass_single_kg * secondary_ring_unit_price_per_kg
    )

    secondary_ring_bending_cost_single_eur = (
        math.pi * tank_diameter * 2 * welder_hourly_rate_eur_per_hour
    )

    secondary_ring_site_weld_hours_single = (
        2 * math.pi * tank_diameter * _xlookup_weld_time_lap(secondary_ring_thickness_mm)
    )
    secondary_ring_site_weld_cost_single_eur = (
        secondary_ring_site_weld_hours_single * welder_hourly_rate_eur_per_hour
    )

    total_secondary_ring_cost_eur = (
        secondary_ring_material_cost_single_eur
        + secondary_ring_bending_cost_single_eur
        + secondary_ring_site_weld_cost_single_eur
    ) * number_of_stiffening_rings

    shell_plate_weight_tonnes = (
        total_shell_weight_kg
        + top_angle_mass_kg
        + secondary_ring_mass_single_kg * number_of_stiffening_rings
    ) / 1000

    shop_hours_shell_plates = shell_plate_weight_tonnes * shell_plate_shop_hours_per_tonne
    top_angle_shop_hours = top_angle_mass_kg * 0.001 * top_angle_shop_hours_per_tonne
    secondary_ring_shop_hours = (
        secondary_ring_mass_single_kg
        * 0.001
        * secondary_ring_shop_hours_per_tonne
        * number_of_stiffening_rings
    )

    total_shop_hours = (
        shop_hours_shell_plates
        + top_angle_shop_hours
        + secondary_ring_shop_hours
        + total_manipulation_hours
    )

    total_shop_cost_eur = total_shop_hours * shop_hourly_rate_eur_per_hour

    total_site_hours = (
        total_circ_weld_hours
        + total_vertical_weld_hours
        + top_angle_lap_weld_hours
        + secondary_ring_site_weld_hours_single * number_of_stiffening_rings
    )

    total_welding_hours = total_site_hours

    total_shell_cost_eur = (
        total_material_cost
        + total_circ_weld_cost
        + total_vertical_weld_cost
        + total_top_angle_cost_eur
        + total_secondary_ring_cost_eur
        + total_shop_cost_eur
    )

    return {
        "courses": course_rows,
        "total_material_cost_eur": total_material_cost,
        "total_circumferential_weld_cost_eur": total_circ_weld_cost,
        "total_vertical_weld_cost_eur": total_vertical_weld_cost,
        "total_top_angle_cost_eur": total_top_angle_cost_eur,
        "total_secondary_ring_cost_eur": total_secondary_ring_cost_eur,
        "total_shop_cost_eur": total_shop_cost_eur,
        "total_shell_weight_kg": total_shell_weight_kg + top_angle_mass_kg + secondary_ring_mass_single_kg * number_of_stiffening_rings,
        "total_welding_hours": total_welding_hours,
        "total_site_hours": total_site_hours,
        "total_manipulation_hours": total_manipulation_hours,
        "total_shop_hours": total_shop_hours,
        "total_shell_cost_eur": total_shell_cost_eur,
        "number_of_stiffening_rings": number_of_stiffening_rings,
        "top_angle_leg_a_mm": top_angle_leg_a_mm,
        "top_angle_leg_b_mm": top_angle_leg_b_mm,
        "top_angle_thickness_mm": top_angle_thickness_mm,
        "wind_girder_leg_a_mm": secondary_ring_leg_a_mm,
        "wind_girder_leg_b_mm": secondary_ring_leg_b_mm,
        "wind_girder_thickness_mm": secondary_ring_thickness_mm,
        "top_angle_mass_kg": top_angle_mass_kg,
        "secondary_ring_mass_single_kg": secondary_ring_mass_single_kg,
        "top_angle_material_cost_eur": top_angle_material_cost_eur,
        "top_angle_weld_cost_eur": top_angle_weld_cost_eur,
        "secondary_ring_material_cost_single_eur": secondary_ring_material_cost_single_eur,
        "secondary_ring_bending_cost_single_eur": secondary_ring_bending_cost_single_eur,
        "secondary_ring_site_weld_cost_single_eur": secondary_ring_site_weld_cost_single_eur,
    }


# ----------------------------
# Roof Cost Design
# ----------------------------
def _lookup_section_price_per_m(section_name):
    section_price_per_m = {
        "IPE 80": 10.6925,
        "IPE 100": 14.455,
        "IPE 120": 18.55,
        "IPE 140": 22.925,
        "IPE 160": 28.175,
        "IPE 180": 33.6,
        "IPE 200": 39.9,
        "IPE 220": 46.725,
        "IPE 240": 54.425,
        "IPE 270": 64.4,
        "IPE 300": 75.25,
        "UPN 80": 15.435,
        "UPN 100": 18.9,
        "UPN 120": 23.8,
        "UPN 140": 28.525,
        "UPN 160": 33.6,
        "UPN 180": 39.2,
        "UPN 200": 44.975,
        "UPN 220": 52.5,
        "UPN 240": 59.15,
        "UPN 260": 67.55,
        "UPN 280": 74.725,
        "UPN 300": 82.25,
        "UPN 320": 106.05,
        "UPN 350": 108.15,
        "UPN 380": 112.525,
        "UPN 400": 128.1,
    }

    if section_name not in section_price_per_m:
        raise ValueError(f"No roof price-per-meter defined for section: {section_name}")

    return section_price_per_m[section_name]


def _lookup_crown_bending_cost(section_name, crown_length_m):
    bending_costs = {
        "UPN 160": {"one": 285, "two": 235, "three": 205},
        "UPN 180": {"one": 310, "two": 260, "three": 220},
        "UPN 200": {"one": 330, "two": 280, "three": 250},
        "UPN 220": {"one": 340, "two": 290, "three": 260},
        "UPN 240": {"one": 340, "two": 290, "three": 260},
        "UPN 260": {"one": 350, "two": 300, "three": 270},
        "UPN 280": {"one": 370, "two": 320, "three": 290},
        "UPN 300": {"one": 390, "two": 340, "three": 310},
        "UPN 320": {"one": 420, "two": 370, "three": 340},
        "UPN 350": {"one": 450, "two": 400, "three": 370},
    }

    if section_name not in bending_costs:
        return 0.0

    data = bending_costs[section_name]

    if crown_length_m <= 6:
        return data["one"]
    elif crown_length_m <= 12:
        return data["two"] * 2
    else:
        return data["three"] * 3


def _normalize_ipe_name_for_excel(ipe_name):
    return ipe_name.replace("IPE", "IPE ")


def _normalize_unp_name_for_excel(unp_name):
    return unp_name.replace("UNP", "UPN ")


def calculate_roof_cost(inputs, roof_result, best_shell):
    base_steel_cost_eur_per_kg = 0.85
    welder_hourly_rate_eur_per_hour = 67.7
    shop_hourly_rate_eur_per_hour = 82.0
    roof_support_shop_hours_per_kg = 0.01671
    roof_plates_shop_hours_per_tonne = 1.75
    roof_plate_waste_factor = 1.3

    roof_plate_material = inputs["roof_plate_material"]
    tank_diameter = inputs["tank_diameter"]

    _require_positive("tank_diameter", tank_diameter)

    geometry = roof_result["details"]["geometry"]
    roof_plate = roof_result["details"]["roof_plate"]
    rafter = roof_result["details"]["rafter"]
    bracing = roof_result["details"]["bracing"]

    roof_plate_props = _xlookup_material_density_and_price(roof_plate_material)
    roof_plate_density = roof_plate_props["density"]
    roof_plate_price_per_kg = base_steel_cost_eur_per_kg * roof_plate_props["price_factor"]

    roof_plate_count = roof_plate["number_of_plates"]
    roof_plate_thickness_mm = roof_plate["roof_plate_thickness"]
    roof_plate_width_m = roof_plate["roof_plate_width"]
    roof_plate_length_m = roof_plate["roof_plate_length"]

    roof_plate_mass_kg = (
        roof_plate_count
        * roof_plate_thickness_mm
        * roof_plate_width_m
        * roof_plate_length_m
        * 0.001
        * roof_plate_density
    )

    total_roof_plate_cost_eur = roof_plate_mass_kg * roof_plate_price_per_kg * roof_plate_waste_factor

    valid_thicknesses = [t for t in best_shell["course_thicknesses"] if t is not None]
    shell_min_thickness = min(valid_thicknesses) if valid_thicknesses else roof_plate_thickness_mm

    roof_shell_weld_meters = 2 * math.pi * tank_diameter
    roof_shell_weld_time_per_meter = _xlookup_weld_time_lap(shell_min_thickness)
    roof_shell_welding_factor = 1.9
    roof_shell_weld_hours = roof_shell_weld_meters * roof_shell_weld_time_per_meter * roof_shell_welding_factor
    roof_shell_weld_cost_eur = roof_shell_weld_hours * welder_hourly_rate_eur_per_hour

    rafter_type_excel = _normalize_ipe_name_for_excel(roof_result["rafter_type"])
    number_of_rafters = rafter["number_of_rafters"]
    total_rafter_mass_kg = rafter["total_rafter_mass"]
    rafter_length_m = rafter["rafter_length"]

    price_per_rafter_eur = rafter_length_m * _lookup_section_price_per_m(rafter_type_excel)
    total_rafters_cost_eur = price_per_rafter_eur * number_of_rafters

    ipe_width_lookup_mm = {
        "IPE 80": 46,
        "IPE 100": 55,
        "IPE 120": 64,
        "IPE 140": 73,
        "IPE 160": 82,
        "IPE 180": 91,
        "IPE 200": 100,
        "IPE 220": 110,
        "IPE 240": 120,
        "IPE 270": 135,
        "IPE 300": 150,
    }

    rafter_weld_length_m = number_of_rafters * 8 * ipe_width_lookup_mm[rafter_type_excel] * 0.001
    rafter_weld_factor = 1.3
    rafter_weld_hours = rafter_weld_factor * rafter_weld_length_m
    rafter_weld_cost_eur = rafter_weld_hours * welder_hourly_rate_eur_per_hour

    crown_ring_type_excel = _normalize_unp_name_for_excel(roof_result["crown_ring_type"])
    crown_ring_diameter_m = roof_result["details"]["crown_ring_diameter_mm"] / 1000
    crown_ring_length_m = math.pi * crown_ring_diameter_m

    crown_ring_price_no_bending_eur = crown_ring_length_m * _lookup_section_price_per_m(crown_ring_type_excel)
    crown_ring_bending_cost_eur = 4 * _lookup_crown_bending_cost(crown_ring_type_excel, crown_ring_length_m)
    total_crown_ring_cost_eur = crown_ring_price_no_bending_eur + crown_ring_bending_cost_eur

    crown_ring_mass_kg = crown_ring_length_m * get_unp_profile(roof_result["crown_ring_type"])["mass_kg_m"]

    number_of_bracing_sections = bracing["number_of_wind_bracing_sections"]
    bracing_ring_total_length_m = math.pi * tank_diameter / 2 * (number_of_bracing_sections + 1)
    bracing_material_price_per_m = _lookup_section_price_per_m(rafter_type_excel)
    bracing_material_cost_eur = bracing_ring_total_length_m * bracing_material_price_per_m
    bracing_mass_kg = bracing_ring_total_length_m * rafter["profile"]["mass_kg_m"]

    bracing_weld_count = 4 * number_of_rafters * number_of_bracing_sections
    bracing_each_weld_length_m = ipe_width_lookup_mm[rafter_type_excel] * 0.001
    bracing_total_weld_length_m = bracing_weld_count * bracing_each_weld_length_m
    bracing_weld_thickness_mm = max(roof_plate_thickness_mm, 6)
    bracing_weld_factor = _xlookup_weld_time_lap(bracing_weld_thickness_mm)
    bracing_position_factor = 1.3
    bracing_weld_hours = bracing_total_weld_length_m * bracing_weld_factor * bracing_position_factor
    bracing_weld_cost_eur = bracing_weld_hours * welder_hourly_rate_eur_per_hour

    roof_weld_meters = (
        0.5
        * (roof_plate_length_m + roof_plate_width_m)
        * (math.pi * (tank_diameter / 2) ** 2)
        / (roof_plate_width_m * roof_plate_length_m)
    )
    roof_plate_weld_hours = roof_weld_meters * _xlookup_weld_time_lap(roof_plate_thickness_mm) * 1.9
    roof_plate_weld_cost_eur = roof_plate_weld_hours * welder_hourly_rate_eur_per_hour

    roof_plate_shop_hours = roof_plate_mass_kg * roof_plates_shop_hours_per_tonne / 1000
    roof_plate_shop_cost = roof_plate_shop_hours * shop_hourly_rate_eur_per_hour

    roof_support_shop_hours = total_rafter_mass_kg * roof_support_shop_hours_per_kg
    roof_support_shop_cost = roof_support_shop_hours * shop_hourly_rate_eur_per_hour

    total_roof_site_hours = (
        roof_shell_weld_hours
        + roof_plate_weld_hours
        + rafter_weld_hours
        + bracing_weld_hours
    )
    total_roof_shop_hours = roof_plate_shop_hours + roof_support_shop_hours
    total_roof_welding_hours = total_roof_site_hours

    total_roof_material_cost_eur = (
        total_roof_plate_cost_eur
        + total_rafters_cost_eur
        + total_crown_ring_cost_eur
        + bracing_material_cost_eur
    )

    total_roof_welding_cost_eur = (
        roof_shell_weld_cost_eur
        + roof_plate_weld_cost_eur
        + rafter_weld_cost_eur
        + bracing_weld_cost_eur
    )

    total_roof_shop_cost_eur = roof_plate_shop_cost + roof_support_shop_cost

    total_roof_cost_eur = (
        total_roof_material_cost_eur
        + total_roof_welding_cost_eur
        + total_roof_shop_cost_eur
    )

    total_roof_weight_kg = (
        roof_plate_mass_kg
        + total_rafter_mass_kg
        + crown_ring_mass_kg
        + bracing_mass_kg
    )

    return {
        "roof_plate_count": roof_plate_count,
        "roof_plate_thickness_mm": roof_plate_thickness_mm,
        "roof_plate_mass_kg": roof_plate_mass_kg,
        "roof_plate_cost_eur": total_roof_plate_cost_eur,
        "roof_shell_weld_meters": roof_shell_weld_meters,
        "roof_shell_weld_hours": roof_shell_weld_hours,
        "roof_shell_weld_cost_eur": roof_shell_weld_cost_eur,
        "number_of_rafters": number_of_rafters,
        "total_rafter_mass_kg": total_rafter_mass_kg,
        "price_per_rafter_eur": price_per_rafter_eur,
        "total_rafters_cost_eur": total_rafters_cost_eur,
        "rafter_weld_hours": rafter_weld_hours,
        "rafter_weld_cost_eur": rafter_weld_cost_eur,
        "crown_ring_type": crown_ring_type_excel,
        "crown_ring_length_m": crown_ring_length_m,
        "crown_ring_mass_kg": crown_ring_mass_kg,
        "crown_ring_price_no_bending_eur": crown_ring_price_no_bending_eur,
        "crown_ring_bending_cost_eur": crown_ring_bending_cost_eur,
        "total_crown_ring_cost_eur": total_crown_ring_cost_eur,
        "number_of_bracing_sections": number_of_bracing_sections,
        "bracing_material_cost_eur": bracing_material_cost_eur,
        "bracing_mass_kg": bracing_mass_kg,
        "bracing_weld_hours": bracing_weld_hours,
        "bracing_weld_cost_eur": bracing_weld_cost_eur,
        "roof_plate_field_weld_hours": roof_plate_weld_hours,
        "roof_plate_field_weld_cost_eur": roof_plate_weld_cost_eur,
        "roof_plate_shop_hours": roof_plate_shop_hours,
        "roof_plate_shop_cost_eur": roof_plate_shop_cost,
        "roof_support_shop_hours": roof_support_shop_hours,
        "roof_support_shop_cost_eur": roof_support_shop_cost,
        "total_roof_material_cost_eur": total_roof_material_cost_eur,
        "total_roof_welding_cost_eur": total_roof_welding_cost_eur,
        "total_roof_shop_cost_eur": total_roof_shop_cost_eur,
        "total_roof_site_hours": total_roof_site_hours,
        "total_roof_shop_hours": total_roof_shop_hours,
        "total_roof_welding_hours": total_roof_welding_hours,
        "total_roof_weight_kg": total_roof_weight_kg,
        "total_roof_cost_eur": total_roof_cost_eur,
    }


# ----------------------------
# Site Erection Equipment Cost
# ----------------------------
def calculate_site_erection_cost(inputs, bottom_cost_result, shell_cost_result, roof_cost_result):
    """
    Equipment for Site Erection.
    Uses site-related hours rather than shop hours.
    """

    tank_diameter = inputs["tank_diameter"]
    method_of_erection = inputs.get("method_of_erection", "")
    _require_positive("tank_diameter", tank_diameter)

    manforce_site_erection = 8
    electricity_cost_per_hour = 1800 / 40
    scaffold_cost_per_meter = 70

    temp_erection_clips = 706
    gas_burner_oven_blue_belts_winch = 713
    lighting_cost_per_week = 157.4
    other_cost_per_person_per_week = 16.525
    climbing_poles_cost_per_week = 29
    pump_cost_per_week = 188.6
    circo_support_cost_per_person_per_week = 8.68
    temp_beams_bottom_fixed = 10000
    electrical_equipment_per_week = 1800
    crane_cost_per_hour = 150

    bottom_hours = safe_number(bottom_cost_result.get("total_bottom_site_hours", 0)) if bottom_cost_result else 0.0
    shell_hours = safe_number(shell_cost_result.get("total_site_hours", 0)) if shell_cost_result else 0.0
    roof_hours = safe_number(roof_cost_result.get("total_roof_site_hours", 0)) if roof_cost_result else 0.0

    total_weeks_on_site = ((bottom_hours + shell_hours + roof_hours) / (manforce_site_erection * 40)) * 1.25
    hours_working_on_site = total_weeks_on_site * 40

    temp_support_cost = total_weeks_on_site * temp_erection_clips
    gas_burner_cost = total_weeks_on_site * gas_burner_oven_blue_belts_winch
    lighting_cost = lighting_cost_per_week * total_weeks_on_site
    other_cost = total_weeks_on_site * other_cost_per_person_per_week * manforce_site_erection
    climbing_poles_cost = climbing_poles_cost_per_week * total_weeks_on_site
    pump_cost = pump_cost_per_week * total_weeks_on_site
    circo_support_cost = (
        circo_support_cost_per_person_per_week
        * total_weeks_on_site
        * manforce_site_erection
    )

    total_temporary_erection_equipment_cost = (
        temp_support_cost
        + gas_burner_cost
        + lighting_cost
        + other_cost
        + climbing_poles_cost
        + pump_cost
        + circo_support_cost
    )

    method_clean = str(method_of_erection).strip().lower()

    if method_clean == "jacking":
        number_of_jacks = math.ceil((math.pi * tank_diameter) / 10)
    else:
        number_of_jacks = 0

    if number_of_jacks == 0:
        total_price_of_jacks = 0
    else:
        total_price_of_jacks = (43 * number_of_jacks * total_weeks_on_site) + (57 * total_weeks_on_site * 8)

    if method_clean == "stacking":
        scaffold_length = math.pi * tank_diameter
    else:
        scaffold_length = 0

    total_stacking_cost = scaffold_length * scaffold_cost_per_meter
    cost_of_electricity_for_site_erection = hours_working_on_site * electricity_cost_per_hour
    temporary_beams_and_towers_cost = temp_beams_bottom_fixed
    electrical_equipment_cost = electrical_equipment_per_week * total_weeks_on_site
    crane_costs = total_weeks_on_site * 40 * 0.7 * crane_cost_per_hour

    cost_of_equipment_for_site_erection = (
        total_temporary_erection_equipment_cost
        + temporary_beams_and_towers_cost
        + electrical_equipment_cost
        + crane_costs
    )

    total_site_related_costs = (
        cost_of_equipment_for_site_erection
        + cost_of_electricity_for_site_erection
        + total_price_of_jacks
        + total_stacking_cost
    )

    return {
        "total_weeks_on_site": total_weeks_on_site,
        "hours_working_on_site": hours_working_on_site,
        "manforce_working_on_erection": manforce_site_erection,
        "temp_support_cost": temp_support_cost,
        "gas_burner_cost": gas_burner_cost,
        "lighting_cost": lighting_cost,
        "other_cost": other_cost,
        "climbing_poles_cost": climbing_poles_cost,
        "pump_cost": pump_cost,
        "circo_support_cost": circo_support_cost,
        "total_temporary_erection_equipment_cost": total_temporary_erection_equipment_cost,
        "number_of_jacks": number_of_jacks,
        "total_price_of_jacks": total_price_of_jacks,
        "scaffold_length": scaffold_length,
        "total_stacking_cost": total_stacking_cost,
        "temporary_beams_and_towers_cost": temporary_beams_and_towers_cost,
        "electrical_equipment_cost": electrical_equipment_cost,
        "crane_costs": crane_costs,
        "cost_of_equipment_for_site_erection": cost_of_equipment_for_site_erection,
        "cost_of_electricity_for_site_erection": cost_of_electricity_for_site_erection,
        "total_site_related_costs": total_site_related_costs,
    }


# ----------------------------
# NDT Cost
# ----------------------------
def calculate_ndt_cost(inputs):
    tank_diameter = inputs["tank_diameter"]
    _require_positive("tank_diameter", tank_diameter)

    if tank_diameter <= 10:
        total_ndt_cost_eur = 7500.0
    elif tank_diameter <= 20:
        total_ndt_cost_eur = 12500.0
    elif tank_diameter <= 30:
        total_ndt_cost_eur = 18500.0
    elif tank_diameter <= 40:
        total_ndt_cost_eur = 26000.0
    elif tank_diameter <= 50:
        total_ndt_cost_eur = 34000.0
    else:
        total_ndt_cost_eur = 42000.0

    return {
        "tank_diameter": tank_diameter,
        "total_ndt_cost_eur": total_ndt_cost_eur,
    }


# ----------------------------
# Total Project Cost
# ----------------------------
def calculate_total_project_cost(
    bottom_cost_result,
    shell_cost_result,
    roof_cost_result,
    site_erection_cost_result,
    ndt_cost_result,
    accessories_cost_eur=0.0,
):
    bottom_cost_eur = safe_number(
        bottom_cost_result.get("total_cost", 0) if bottom_cost_result else 0
    )
    shell_cost_eur = safe_number(
        shell_cost_result.get("total_shell_cost_eur", 0) if shell_cost_result else 0
    )
    roof_cost_eur = safe_number(
        roof_cost_result.get("total_roof_cost_eur", 0) if roof_cost_result else 0
    )
    site_erection_cost_eur = safe_number(
        site_erection_cost_result.get("total_site_related_costs", 0)
        if site_erection_cost_result
        else 0
    )
    ndt_cost_eur = safe_number(
        ndt_cost_result.get("total_ndt_cost_eur", 0) if ndt_cost_result else 0
    )
    accessories_cost_eur = safe_number(accessories_cost_eur, 0)

    total_project_cost_eur = (
        bottom_cost_eur
        + shell_cost_eur
        + roof_cost_eur
        + site_erection_cost_eur
        + ndt_cost_eur
        + accessories_cost_eur
    )

    return {
        "bottom_cost_eur": bottom_cost_eur,
        "shell_cost_eur": shell_cost_eur,
        "roof_cost_eur": roof_cost_eur,
        "site_erection_cost_eur": site_erection_cost_eur,
        "ndt_cost_eur": ndt_cost_eur,
        "accessories_cost_eur": accessories_cost_eur,
        "total_project_cost_eur": total_project_cost_eur,
    }


# ----------------------------
# Main test runner
# ----------------------------
def main():
    inputs = {
        "tank_diameter": 15,
        "shell_height": 29,
        "design_liquid_height": 29,
        "corrosion_allowance_bottom": 2,
        "shell_design_n18": 9,
        "material_type": "Carbon Steel Lap Welded",
        "design_density_operating": 1.02,
        "test_density": 1.0,
        "design_pressure": 10,
        "test_pressure": 10,
        "shell_corrosion_allowance": 1,
        "wind_gust_velocity": 45,
        "live_loads": 1.25,
        "snow_loads": 2.5,
        "insulation_loads": 0.0,
        "roof_plate_material": "S235JR",
        "supporting_material": "S235JR",
        "roof_slope": 0.2,
        "method_of_erection": "Jacking",
    }

    bottom_result = calculate_bottom_design(
        tank_diameter=inputs["tank_diameter"],
        design_liquid_height=inputs["design_liquid_height"],
        corrosion_allowance_bottom=inputs["corrosion_allowance_bottom"],
        shell_design_n18=inputs["shell_design_n18"],
    )

    bottom_cost_result = calculate_bottom_cost(inputs, bottom_result)

    shell_result = calculate_shell_design(
        tank_diameter=inputs["tank_diameter"],
        shell_height=inputs["shell_height"],
        material_type=inputs["material_type"],
        design_density_operating=inputs["design_density_operating"],
        test_density=inputs["test_density"],
        design_pressure=inputs["design_pressure"],
        test_pressure=inputs["test_pressure"],
        shell_corrosion_allowance=inputs["shell_corrosion_allowance"],
        wind_gust_velocity=inputs["wind_gust_velocity"],
    )

    best_shell = find_cheapest_shell_material_combination(
        tank_diameter=inputs["tank_diameter"],
        shell_height=inputs["shell_height"],
        material_type=inputs["material_type"],
        design_density_operating=inputs["design_density_operating"],
        test_density=inputs["test_density"],
        design_pressure=inputs["design_pressure"],
        test_pressure=inputs["test_pressure"],
        shell_corrosion_allowance=inputs["shell_corrosion_allowance"],
        wind_gust_velocity=inputs["wind_gust_velocity"],
        search_mode="two_zone",
    )

    roof_result = find_lightest_safe_fixed_cone_roof_rafter(
        tank_diameter=inputs["tank_diameter"],
        design_pressure=inputs["design_pressure"],
        live_loads=inputs["live_loads"],
        snow_loads=inputs["snow_loads"],
        insulation_loads=inputs["insulation_loads"],
        roof_slope=inputs["roof_slope"],
        roof_plate_material=inputs["roof_plate_material"],
        supporting_material=inputs["supporting_material"],
    )

    shell_cost_result = None
    if best_shell is not None:
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

    roof_cost_result = None
    if best_shell is not None and roof_result["status"] == "SAFE":
        roof_cost_result = calculate_roof_cost(
            inputs=inputs,
            roof_result=roof_result,
            best_shell=best_shell,
        )

    site_erection_cost_result = None
    if shell_cost_result is not None:
        site_erection_cost_result = calculate_site_erection_cost(
            inputs=inputs,
            bottom_cost_result=bottom_cost_result,
            shell_cost_result=shell_cost_result,
            roof_cost_result=roof_cost_result,
        )

    ndt_cost_result = calculate_ndt_cost(inputs)

    total_project_cost_result = calculate_total_project_cost(
        bottom_cost_result=bottom_cost_result,
        shell_cost_result=shell_cost_result,
        roof_cost_result=roof_cost_result,
        site_erection_cost_result=site_erection_cost_result,
        ndt_cost_result=ndt_cost_result,
        accessories_cost_eur=ACCESSORIES_FIXED_COST_EUR,
    )

    print("BOTTOM DESIGN RESULTS")
    for key, value in bottom_result.items():
        print(f"{key}: {value}")

    print("\nSHELL DESIGN RESULTS")
    for key, value in shell_result.items():
        print(f"{key}: {value}")

    print("\nOPTIMIZED SHELL RESULT")
    if best_shell is None:
        print("No valid design found")
    else:
        for key, value in best_shell.items():
            print(f"{key}: {value}")

    print("\nFIXED CONE ROOF RESULT")
    for key, value in roof_result.items():
        if key != "details":
            print(f"{key}: {value}")

    print("\nBOTTOM COST RESULT")
    for key, value in bottom_cost_result.items():
        print(f"{key}: {value}")

    print("\nSHELL COST RESULT")
    if shell_cost_result is None:
        print("No valid shell cost result")
    else:
        for key, value in shell_cost_result.items():
            if key != "courses":
                print(f"{key}: {value}")

        print("\nSHELL COST PER COURSE")
        for row in shell_cost_result["courses"]:
            print(row)

    print("\nROOF COST RESULT")
    if roof_cost_result is None:
        print("No valid roof cost result")
    else:
        for key, value in roof_cost_result.items():
            print(f"{key}: {value}")

    print("\nSITE ERECTION COST RESULT")
    if site_erection_cost_result is None:
        print("No valid site erection cost result")
    else:
        for key, value in site_erection_cost_result.items():
            print(f"{key}: {value}")

    print("\nNDT COST RESULT")
    for key, value in ndt_cost_result.items():
        print(f"{key}: {value}")

    print("\nACCESSORIES COST")
    print(ACCESSORIES_FIXED_COST_EUR)

    print("\nTOTAL PROJECT COST")
    print(total_project_cost_result["total_project_cost_eur"])


if __name__ == "__main__":
    main()