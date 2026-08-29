"""The found/proposed tier: what the system merely looked up, and what a model
had to judge (spec table-import, LLM matching to HEMA Ratings).

The tier is derived, never reported by the model, so every case here is a pure
function of a stored decision and the fighters index.
"""

from sqlalchemy.orm import Session

from app.hr_index import DbHRIndex, HRProfile, StubHRIndex, name_key
from app.hr_match import country_code, derive_tier
from app.models import HRFighter

JAN = HRProfile(hr_id=10234, name="Jan Novák", nationality="CZE", club="Prague HEMA")


def index(*profiles: HRProfile) -> StubHRIndex:
    return StubHRIndex(list(profiles))


# ---- the name key ----------------------------------------------------------


def test_name_key_disregards_diacritics_case_and_word_order():
    assert name_key("Jan Novák") == name_key("novak jan") == ("jan", "novak")


def test_name_key_is_not_a_subset_test():
    assert name_key("Jan Petr Novák") != name_key("Jan Novák")


def test_name_key_of_nothing_is_empty():
    assert name_key("") == () and name_key("   ") == ()


# ---- the index lookup ------------------------------------------------------


def test_stub_index_finds_both_orderings_under_one_key():
    reversed_jan = HRProfile(hr_id=99, name="Novák Jan", nationality="CZE", club=None)
    found = index(JAN, reversed_jan).by_name_key("Jan Novak")
    assert {p.hr_id for p in found} == {10234, 99}


def test_db_index_lookup_counts_one_two_and_none(engine):
    with Session(engine) as session:
        session.add_all(
            [
                HRFighter(hr_id=1, name="Jan Novák", name_folded="jan novak",
                          nationality="CZE", club=None),
                HRFighter(hr_id=2, name="Novák Jan", name_folded="novak jan",
                          nationality="CZE", club=None),
                HRFighter(hr_id=3, name="Petr Svoboda", name_folded="petr svoboda",
                          nationality="CZE", club=None),
                # a longer name carrying both tokens: the substring narrowing
                # lets it through, the key comparison must not
                HRFighter(hr_id=4, name="Jan Novákovský", name_folded="jan novakovsky",
                          nationality="CZE", club=None),
            ]
        )
        session.commit()
        db = DbHRIndex(session)
        assert {p.hr_id for p in db.by_name_key("Jan Novak")} == {1, 2}
        assert [p.hr_id for p in db.by_name_key("Petr Svoboda")] == [3]
        assert db.by_name_key("Marie Nová") == []


# ---- the tier --------------------------------------------------------------


def test_exact_unambiguous_hit_is_found():
    assert derive_tier("Jan Novak", "CZ", 10234, index(JAN)) == "found"


def test_surname_first_registration_is_found():
    """Word order is a convention, not a difference the organizer adjudicates."""
    assert derive_tier("Novak Jan", "CZ", 10234, index(JAN)) == "found"


def test_transliteration_is_proposed():
    assert derive_tier("Honza Blazek", "CZ", 10234, index(JAN)) == "proposed"


def test_extra_given_name_is_a_difference():
    assert derive_tier("Jan Petr Novak", "CZ", 10234, index(JAN)) == "proposed"


def test_ambiguous_name_key_is_proposed_however_exact():
    twin = HRProfile(hr_id=555, name="Novák Jan", nationality="CZE", club=None)
    assert derive_tier("Jan Novak", "CZ", 10234, index(JAN, twin)) == "proposed"


def test_a_different_fighter_than_the_exact_hit_is_proposed():
    other = HRProfile(hr_id=8821, name="Lukas Mueller", nationality="DEU", club=None)
    assert derive_tier("Jan Novak", "CZ", 8821, index(JAN, other)) == "proposed"


def test_contradicting_nationality_is_proposed():
    assert derive_tier("Jan Novak", "POL", 10234, index(JAN)) == "proposed"


def test_absent_nationality_contradicts_nothing():
    assert derive_tier("Jan Novak", None, 10234, index(JAN)) == "found"


def test_shorter_country_spelling_is_not_a_contradiction():
    """A registration writes "CZ" or "Czechia" where the index writes "CZE";
    treating that as disagreement would empty the found tier of meaning."""
    assert derive_tier("Jan Novak", "Czechia", 10234, index(JAN)) == "found"


# ---- the two country vocabularies ------------------------------------------


def test_country_code_reads_every_vocabulary_the_two_sides_use():
    """Registrations name a country by ISO code, the fighters index by its
    English name. Both must reach the same country or the tier demotes nearly
    every foreign fencer."""
    for spelling in ("CZ", "CZE", "Czechia", "Czech Republic", "czech republic"):
        assert country_code(spelling) == "CZ", spelling


def test_country_code_bridges_the_codes_no_prefix_rule_could():
    for code, name in (("PL", "Poland"), ("DE", "Germany"), ("SK", "Slovakia"),
                       ("SRB", "Serbia"), ("GB", "United Kingdom")):
        resolved = country_code(code)
        assert resolved is not None and resolved == country_code(name), (code, name)


def test_country_code_reads_the_names_iso_records_differently():
    """The index spells these the common way; ISO 3166 does not."""
    assert country_code("Russia") == country_code("RUS") == "RU"
    assert country_code("Turkey") == country_code("TUR") == "TR"
    assert country_code("Palestine") == country_code("PSE") == "PS"


def test_every_name_for_the_united_kingdom_is_one_country():
    """ISO knows one country here; the fighters index's own flag code spells it
    "UK", and a fencer writes whichever name they think of. None of them may
    read as a different country from the others."""
    for spelling in ("GB", "UK", "United Kingdom", "Great Britain", "England",
                     "Scotland", "Wales", "Northern Ireland"):
        assert country_code(spelling) == "GB", spelling


def test_country_code_is_always_two_characters():
    """Two is the number the evidence register is written in."""
    for spelling in ("Poland", "PL", "POL", "Germany", "United Kingdom", "Russia"):
        assert len(country_code(spelling)) == 2, spelling


def test_country_code_of_nothing_identifiable_is_none():
    assert country_code(None) is None
    assert country_code("  ") is None
    assert country_code("Neverland") is None


def test_an_iso_code_against_an_english_name_is_not_a_contradiction():
    polish = HRProfile(hr_id=42, name="Jakub Rejmus", nationality="Poland", club=None)
    assert derive_tier("Jakub Rejmus", "PL", 42, index(polish)) == "found"


def test_a_country_we_cannot_identify_contradicts_nothing():
    """An unreadable spelling is our failure to interpret it, not the fencer
    disagreeing with their profile — and the row would show no reason for the
    demotion (spec etl-console, The ledger idiom)."""
    odd = HRProfile(hr_id=42, name="Jan Novak", nationality="Neverland", club=None)
    assert derive_tier("Jan Novak", "CZ", 42, index(odd)) == "found"


def test_profile_absent_from_the_index_degrades_to_proposed():
    assert derive_tier("Jan Novak", "CZ", 10234, index()) == "proposed"


def test_no_index_degrades_to_proposed():
    """Asking for a look that was not needed beats skipping one that was."""
    assert derive_tier("Jan Novak", "CZ", 10234, None) == "proposed"
