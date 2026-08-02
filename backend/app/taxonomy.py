"""HEMA discipline taxonomy: weapon x gender x material.

The taxonomy code is a derived join key (design discipline-identity D5), not a
discipline's identity — that is the slug (see models.Discipline.slug). Code
format mirrors v1 HemaDiscipline.str(): optional "Plastic " prefix, weapon
code, W/M gender suffix; Open and Steel are unmarked defaults.
Examples: "LS", "SAW", "Plastic LSM".
"""

import re
import unicodedata

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


def is_taxonomy_weapon(weapon: str) -> bool:
    return weapon in WEAPONS


def taxonomy_code(weapon: str, gender: str, material: str) -> str:
    """The v1 taxonomy code for a weapon x gender x material triple — the join
    key to everything outside a discipline (design discipline-identity D5).
    Meaningful even for a weapon outside the taxonomy: the resulting code
    simply matches no external mapping (design D4)."""
    material_prefix = "" if material in ("", "Steel") else material
    gender_suffix = gender if gender in ("W", "M") else ""
    return f"{material_prefix} {weapon}{gender_suffix}".strip()


def parse_code(code: str) -> tuple[str, str, str]:
    """The inverse of `taxonomy_code`, defined over the 30 generated codes
    (used for the migration backfill and for reading pre-migration export
    documents). Returns (weapon, gender, material)."""
    material = "Plastic" if code.startswith("Plastic ") else ""
    rest = code.removeprefix("Plastic ").strip()
    gender = ""
    if rest and rest[-1] in ("W", "M"):
        gender = rest[-1]
        rest = rest[:-1]
    weapon = rest
    return weapon, gender, material


def taxonomy_name(weapon: str, gender: str, material: str) -> str | None:
    """The generated name for a taxonomy weapon, or None for a weapon the
    taxonomy does not name — such a discipline requires an explicit name
    (design discipline-identity D4)."""
    return DISCIPLINES.get(taxonomy_code(weapon, gender, material))


def discipline_name(weapon: str, gender: str, material: str, is_team: bool) -> str | None:
    """The generated name for a discipline, marked as a team discipline when
    it is one, so an individual and a team discipline classified alike do not
    generate the same name (design discipline-identity-modal D8). `is_team`
    rather than `models.DisciplineKind` to avoid a circular import — models.py
    imports this module."""
    name = taxonomy_name(weapon, gender, material)
    if name is None:
        return None
    return f"Team {name}" if is_team else name


def normalize_slug(value: str) -> str:
    """Fold a slug into a form safe in a URL path, a spreadsheet column, and
    an import parse: diacritics folded to ASCII, every run of characters
    outside letters, digits and `-` collapsed to a single `-`, leading and
    trailing `-` stripped. Case-preserving (design discipline-identity-modal
    D4) — a slug derived from a taxonomy code reads as that code does
    everywhere else in the system. May return the empty string; the caller
    decides the fallback (design discipline-identity-modal task 1.2)."""
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"[^A-Za-z0-9-]+", "-", folded)
    return collapsed.strip("-")
