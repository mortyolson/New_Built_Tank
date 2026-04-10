MATERIALS = {
    "S235JR": {"density": 7850, "yield": 235},
    "S235JO": {"density": 7850, "yield": 235},
    "S275JR": {"density": 7800, "yield": 275},
    "S275JO": {"density": 7800, "yield": 275},
    "S275J2": {"density": 7800, "yield": 275},
    "S275N": {"density": 7800, "yield": 275},
    "S275NL": {"density": 7800, "yield": 275},
    "S275M": {"density": 7800, "yield": 275},
    "S275ML": {"density": 7800, "yield": 275},
    "S355JR": {"density": 7800, "yield": 355},
    "S355JO": {"density": 7800, "yield": 355},
    "P265GH": {"density": 7850, "yield": 265},
    "P295GH": {"density": 7850, "yield": 295},
    "P355GH": {"density": 7850, "yield": 355},
}

ALLOWED_SHELL_COURSE_MATERIALS = [
    "S235JR",
    "S235JO",
    "S275JR",
    "S275JO",
    "S275J2",
    "S275N",
    "S275NL",
    "S275M",
    "S275ML",
    "S355JR",
    "S355JO",
    "P265GH",
    "P295GH",
    "P355GH",
]


def _get_material(material_name: str) -> dict:
    if material_name not in MATERIALS:
        raise ValueError(f"Unknown material: {material_name}")
    return MATERIALS[material_name]


def get_steel_density(material_name: str) -> float:
    return _get_material(material_name)["density"]


def get_steel_yield(material_name: str) -> float:
    return _get_material(material_name)["yield"]


def get_allowable_test_stress(material_name: str) -> float:
    fy = get_steel_yield(material_name)
    return min(0.75 * fy, 260)


def get_allowable_design_stress(material_name: str) -> float:
    fy = get_steel_yield(material_name)
    return min((2 / 3) * fy, 260)


def get_shell_course_material_names():
    return ALLOWED_SHELL_COURSE_MATERIALS[:]


def get_material_properties(material_name: str) -> dict:
    material = _get_material(material_name)
    fy = material["yield"]
    return {
        "density": material["density"],
        "yield": fy,
        "allowable_test_stress": min(0.75 * fy, 260),
        "allowable_design_stress": min((2 / 3) * fy, 260),
    }


# ----------------------------
# Roof / Rafter backend data
# ----------------------------

IPE_PROFILES = {
    "IPE80": {
        "mass_kg_m": 6.11,
        "area_mm2": 760,
        "area_m2": 0.00076,
        "iy_mm4": 801000,
        "iz_mm4": 200000,
        "wel_z_mm3": 8490,
        "omega_yy": 1.589,
        "omega_zz": 5.501,
    },
    "IPE100": {
        "mass_kg_m": 8.26,
        "area_mm2": 1030,
        "area_m2": 0.00103,
        "iy_mm4": 1710000,
        "iz_mm4": 342000,
        "wel_z_mm3": 15920,
        "omega_yy": 1.643,
        "omega_zz": 5.521,
    },
    "IPE120": {
        "mass_kg_m": 10.60,
        "area_mm2": 1320,
        "area_m2": 0.00132,
        "iy_mm4": 3178000,
        "iz_mm4": 529600,
        "wel_z_mm3": 27670,
        "omega_yy": 1.637,
        "omega_zz": 5.266,
    },
    "IPE140": {
        "mass_kg_m": 13.10,
        "area_mm2": 1640,
        "area_m2": 0.00164,
        "iy_mm4": 5412000,
        "iz_mm4": 773200,
        "wel_z_mm3": 44920,
        "omega_yy": 1.628,
        "omega_zz": 5.098,
    },
    "IPE160": {
        "mass_kg_m": 16.10,
        "area_mm2": 2010,
        "area_m2": 0.00201,
        "iy_mm4": 8693000,
        "iz_mm4": 1087000,
        "wel_z_mm3": 68310,
        "omega_yy": 1.656,
        "omega_zz": 5.181,
    },
    "IPE180": {
        "mass_kg_m": 19.20,
        "area_mm2": 2390,
        "area_m2": 0.00239,
        "iy_mm4": 13170000,
        "iz_mm4": 1463000,
        "wel_z_mm3": 100900,
        "omega_yy": 1.641,
        "omega_zz": 5.063,
    },
    "IPE200": {
        "mass_kg_m": 22.80,
        "area_mm2": 2850,
        "area_m2": 0.00285,
        "iy_mm4": 19430000,
        "iz_mm4": 1943000,
        "wel_z_mm3": 142400,
        "omega_yy": 1.676,
        "omega_zz": 5.247,
    },
    "IPE220": {
        "mass_kg_m": 26.70,
        "area_mm2": 3340,
        "area_m2": 0.00334,
        "iy_mm4": 27720000,
        "iz_mm4": 2520000,
        "wel_z_mm3": 204900,
        "omega_yy": 1.650,
        "omega_zz": 5.225,
    },
    "IPE240": {
        "mass_kg_m": 31.10,
        "area_mm2": 3910,
        "area_m2": 0.00391,
        "iy_mm4": 38920000,
        "iz_mm4": 3243000,
        "wel_z_mm3": 283600,
        "omega_yy": 1.662,
        "omega_zz": 5.430,
    },
    "IPE270": {
        "mass_kg_m": 36.80,
        "area_mm2": 4590,
        "area_m2": 0.00459,
        "iy_mm4": 57900000,
        "iz_mm4": 4289000,
        "wel_z_mm3": 419900,
        "omega_yy": 1.667,
        "omega_zz": 5.192,
    },
    "IPE300": {
        "mass_kg_m": 43.00,
        "area_mm2": 5380,
        "area_m2": 0.00538,
        "iy_mm4": 83560000,
        "iz_mm4": 5571000,
        "wel_z_mm3": 603800,
        "omega_yy": 1.667,
        "omega_zz": 5.192,
    },
}

UNP_PROFILES = {
    "UNP100": {"mass_kg_m": 10.80},
    "UNP120": {"mass_kg_m": 13.60},
    "UNP140": {"mass_kg_m": 16.30},
    "UNP160": {"mass_kg_m": 19.20},
    "UNP180": {"mass_kg_m": 22.40},
    "UNP200": {"mass_kg_m": 25.70},
    "UNP220": {"mass_kg_m": 30.00},
    "UNP240": {"mass_kg_m": 33.80},
    "UNP260": {"mass_kg_m": 38.60},
    "UNP280": {"mass_kg_m": 42.70},
    "UNP300": {"mass_kg_m": 47.00},
    "UNP320": {"mass_kg_m": 50.70},
    "UNP350": {"mass_kg_m": 61.80},
    "UNP380": {"mass_kg_m": 64.30},
    "UNP400": {"mass_kg_m": 73.20},
}


def get_ipe_profile_names():
    return list(IPE_PROFILES.keys())


def get_ipe_profile(profile_name: str) -> dict:
    if profile_name not in IPE_PROFILES:
        raise ValueError(f"Unknown IPE profile: {profile_name}")
    return IPE_PROFILES[profile_name]


def get_unp_profile(profile_name: str) -> dict:
    if profile_name not in UNP_PROFILES:
        raise ValueError(f"Unknown UNP profile: {profile_name}")
    return UNP_PROFILES[profile_name]


def get_youngs_modulus_mpa(material_name=None) -> float:
    return 210000


def get_crown_ring_for_rafter(ipe_name: str) -> str:
    size = int(ipe_name.replace("IPE", ""))
    target = size + 20
    candidate = f"UNP{target}"

    if candidate in UNP_PROFILES:
        return candidate

    available = sorted(int(name.replace("UNP", "")) for name in UNP_PROFILES.keys())
    closest = min(available, key=lambda x: abs(x - target))
    return f"UNP{closest}"
