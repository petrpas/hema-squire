"""HEMA discipline taxonomy: weapon x gender x material.

Code format mirrors v1 HemaDiscipline.str(): optional "Plastic " prefix,
weapon code, W/M gender suffix; Open and Steel are unmarked defaults.
Examples: "LS", "SAW", "Plastic LSM".
"""

WEAPONS = {
    "LS": "Longsword",
    "SA": "Sabre",
    "RA": "Single Rapier",
    "RD": "Rapier & Dagger",
    "SB": "Sword & Buckler",
}

GENDERS = {"": "Open", "W": "Women", "M": "Men"}

MATERIALS = {"": "Steel", "Plastic": "Plastic"}


def _build() -> dict[str, str]:
    codes: dict[str, str] = {}
    for material_prefix, material_name in MATERIALS.items():
        for weapon_code, weapon_name in WEAPONS.items():
            for gender_suffix, gender_name in GENDERS.items():
                code = f"{material_prefix} {weapon_code}{gender_suffix}".strip()
                name = f"{weapon_name} {gender_name}"
                if material_prefix:
                    name = f"{name} ({material_name})"
                codes[code] = name
    return codes


DISCIPLINES: dict[str, str] = _build()


def is_valid_code(code: str) -> bool:
    return code in DISCIPLINES


def default_name(code: str) -> str:
    return DISCIPLINES[code]
