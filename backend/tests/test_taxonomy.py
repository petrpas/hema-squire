"""Taxonomy code derivation: round-trip over the 30 generated codes, and name
generation for taxonomy vs. custom weapons (design discipline-identity D4/D5,
task 9.1)."""

from app import taxonomy


def test_taxonomy_code_and_parse_code_round_trip_every_generated_code():
    for code in taxonomy.DISCIPLINES:
        weapon, gender, material = taxonomy.parse_code(code)
        assert taxonomy.taxonomy_code(weapon, gender, material) == code


def test_taxonomy_name_returns_none_for_a_weapon_outside_the_taxonomy():
    assert taxonomy.taxonomy_name("Messer", "", "") is None
    assert taxonomy.taxonomy_name("LS", "", "") == taxonomy.DISCIPLINES["LS"]


def test_is_taxonomy_weapon():
    for code in taxonomy.WEAPONS:
        assert taxonomy.is_taxonomy_weapon(code) is True
    assert taxonomy.is_taxonomy_weapon("Messer") is False


def test_discipline_name_marks_a_team_discipline():
    individual = taxonomy.discipline_name("LS", "", "", is_team=False)
    team = taxonomy.discipline_name("LS", "", "", is_team=True)
    assert individual == taxonomy.taxonomy_name("LS", "", "")
    assert team == f"Team {individual}"
    assert individual != team


def test_discipline_name_returns_none_for_a_weapon_outside_the_taxonomy():
    assert taxonomy.discipline_name("Messer", "", "", is_team=False) is None
    assert taxonomy.discipline_name("Messer", "", "", is_team=True) is None


def test_normalize_slug():
    assert taxonomy.normalize_slug("Tešák") == "Tesak"
    assert taxonomy.normalize_slug("Sword & Buckler (variant)") == "Sword-Buckler-variant"
    assert taxonomy.normalize_slug("LS") == "LS"
    assert taxonomy.normalize_slug("Team-LS") == "Team-LS"
    assert taxonomy.normalize_slug("LS-A") == "LS-A"


def test_normalize_slug_can_return_empty():
    assert taxonomy.normalize_slug("!!!") == ""
