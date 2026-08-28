"""Setup fields that recall the organizer's own prior values.

Every value offered is derived per request from the caller's own tournaments;
nothing about the feature is stored, which is what these tests pin down.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fencer, Tournament, TournamentOrganizer
from app.routers.tournaments import SUGGESTION_CAP, _distinct_organizers, _distinct_recent

SUGGESTIONS = "/api/tournaments/suggestions"


def make_tournament(client, headers, slug, name="Turnaj", date="2026-05-01", **patch):
    response = client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": name, "date": date},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    if patch:
        response = client.patch(f"/api/tournaments/{slug}", json=patch, headers=headers)
        assert response.status_code == 200, response.text
    return response.json()


# --- the ordering and de-duplication helpers (design D5) ---------------------


def test_distinct_recent_keeps_first_occurrence_and_order():
    assert _distinct_recent(["Praha", "Brno", "Praha", "Plzeň"]) == ["Praha", "Brno", "Plzeň"]


def test_distinct_recent_drops_empty_and_blank():
    assert _distinct_recent([None, "", "   ", "Praha"]) == ["Praha"]


def test_distinct_recent_trims_before_comparing():
    assert _distinct_recent(["Praha", " Praha "]) == ["Praha"]


def test_distinct_recent_caps_a_long_history():
    values = [f"Město {i}" for i in range(20)]
    capped = _distinct_recent(values)
    assert len(capped) == SUGGESTION_CAP
    # the cap keeps the most recent, which is what the caller supplied first
    assert capped == values[:SUGGESTION_CAP]


class FakeTournament:
    def __init__(self, organizers):
        self.organizers = organizers


def test_distinct_organizers_keys_on_the_pair():
    """One name used with two links is two entries, so the organizer can tell
    them apart (spec: One name, two links)."""
    pairs = _distinct_organizers(
        [
            FakeTournament(
                [
                    {"name": "SHBU", "link": "https://a.example"},
                    {"name": "SHBU", "link": "https://b.example"},
                ]
            )
        ]
    )
    assert pairs == [
        {"name": "SHBU", "link": "https://a.example"},
        {"name": "SHBU", "link": "https://b.example"},
    ]


def test_distinct_organizers_treats_empty_link_as_absent():
    """A club never appears twice over `""` vs `None` alone."""
    pairs = _distinct_organizers(
        [FakeTournament([{"name": "SHBU", "link": ""}, {"name": "SHBU", "link": None}])]
    )
    assert pairs == [{"name": "SHBU", "link": None}]


def test_distinct_organizers_tolerates_bare_strings():
    """`Tournament.organizers` may still hold bare strings on a
    restored-from-old-export deployment (models.py:210)."""
    pairs = _distinct_organizers([FakeTournament(["SHBU", {"name": "Jiný spolek", "link": None}])])
    assert pairs == [
        {"name": "SHBU", "link": None},
        {"name": "Jiný spolek", "link": None},
    ]


# --- the endpoint -----------------------------------------------------------


def test_first_tournament_offers_nothing(client, auth_headers):
    """An organizer with no history sees empty lists — the frontend renders no
    affordance at all (spec: The very first tournament)."""
    headers = auth_headers()
    response = client.get(SUGGESTIONS, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"locations": [], "bank_accounts": [], "organizers": []}


def test_second_tournament_recalls_the_first(client, auth_headers):
    """spec: Organizer's second tournament."""
    headers = auth_headers()
    make_tournament(
        client,
        headers,
        "prvni",
        location="Sokolovna Praha",
        bank_account="CZ6508000000192000145399",
        organizers=[{"name": "SHBU", "link": "https://shbu.example"}],
    )
    body = client.get(SUGGESTIONS, headers=headers).json()
    assert body["locations"] == ["Sokolovna Praha"]
    assert body["bank_accounts"] == ["CZ6508000000192000145399"]
    assert body["organizers"] == [{"name": "SHBU", "link": "https://shbu.example"}]


def test_ordered_by_tournament_date_descending(client, auth_headers):
    """The tournament carries no creation stamp, so the event date is the proxy
    for recency (design D5)."""
    headers = auth_headers()
    make_tournament(client, headers, "stary", date="2025-03-01", location="Brno")
    make_tournament(client, headers, "novy", date="2026-09-01", location="Praha")
    assert client.get(SUGGESTIONS, headers=headers).json()["locations"] == ["Praha", "Brno"]


def test_value_used_on_many_tournaments_appears_once(client, auth_headers):
    """spec: A value used on many tournaments."""
    headers = auth_headers()
    for index in range(5):
        make_tournament(
            client, headers, f"t{index}", date=f"202{index}-05-01", location="Sokolovna"
        )
    assert client.get(SUGGESTIONS, headers=headers).json()["locations"] == ["Sokolovna"]


def test_drafts_and_cancelled_are_included(client, auth_headers):
    """A draft is exactly where a value about to be reused sits (design D6).
    A tournament is a draft until published, so this one never is."""
    headers = auth_headers()
    make_tournament(client, headers, "koncept", location="Tělocvična Zlín")
    assert client.get(SUGGESTIONS, headers=headers).json()["locations"] == ["Tělocvična Zlín"]


def test_legacy_bare_string_organizers_do_not_break_the_endpoint(
    client, auth_headers, engine
):
    """A restored-from-old-export deployment can hold bare strings; the endpoint
    serves them as name-with-no-link rather than failing."""
    headers = auth_headers()
    make_tournament(client, headers, "obnoveny", location="Olomouc")
    with Session(engine) as session:
        tournament = session.scalar(select(Tournament).where(Tournament.slug == "obnoveny"))
        tournament.organizers = ["Starý spolek"]
        session.commit()

    response = client.get(SUGGESTIONS, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["organizers"] == [{"name": "Starý spolek", "link": None}]


# --- scoping (design D6/D7, spec: Suggestions come from the organizer's own) --


def test_one_organizers_values_stay_their_own(client, auth_headers):
    """Neither organizer is offered anything of the other's — the bank account
    least of all (design D7)."""
    first = auth_headers(email="first@example.com", name="První")
    second = auth_headers(email="second@example.com", name="Druhý")

    make_tournament(
        client,
        first,
        "prvni",
        location="Praha",
        bank_account="CZ6508000000192000145399",
        organizers=[{"name": "Spolek A", "link": None}],
    )
    make_tournament(
        client,
        second,
        "druhy",
        location="Ostrava",
        bank_account="CZ5301000000430000010009",
        organizers=[{"name": "Spolek B", "link": None}],
    )

    first_body = client.get(SUGGESTIONS, headers=first).json()
    assert first_body["locations"] == ["Praha"]
    assert first_body["bank_accounts"] == ["CZ6508000000192000145399"]
    assert first_body["organizers"] == [{"name": "Spolek A", "link": None}]

    second_body = client.get(SUGGESTIONS, headers=second).json()
    assert second_body["locations"] == ["Ostrava"]
    assert second_body["bank_accounts"] == ["CZ5301000000430000010009"]
    assert second_body["organizers"] == [{"name": "Spolek B", "link": None}]


def test_console_access_granted_after_the_fact_widens_the_scope(
    client, auth_headers, engine
):
    """spec: Access granted after the fact. Ownership and console membership
    both count, which is the pair the rest of the console checks."""
    owner = auth_headers(email="owner@example.com", name="Vlastník")
    helper = auth_headers(email="helper@example.com", name="Pomocník")
    make_tournament(client, owner, "turnaj", location="Hradec Králové")

    assert client.get(SUGGESTIONS, headers=helper).json()["locations"] == []

    with Session(engine) as session:
        tournament = session.scalar(select(Tournament).where(Tournament.slug == "turnaj"))
        fencer = session.scalar(select(Fencer).where(Fencer.email == "helper@example.com"))
        session.add(
            TournamentOrganizer(tournament_id=tournament.id, fencer_id=fencer.id)
        )
        session.commit()

    assert client.get(SUGGESTIONS, headers=helper).json()["locations"] == ["Hradec Králové"]


def test_requires_authentication(client):
    assert client.get(SUGGESTIONS).status_code in (401, 403)


# --- derived, not stored (design D1) ----------------------------------------


def test_a_corrected_value_stops_being_offered(client, auth_headers):
    """spec: A corrected value stops being offered. This is the whole payoff of
    deriving rather than recording: the fix is a single edit at the source."""
    headers = auth_headers()
    make_tournament(client, headers, "turnaj", location="Sokolvna Praha")
    assert client.get(SUGGESTIONS, headers=headers).json()["locations"] == ["Sokolvna Praha"]

    client.patch(
        "/api/tournaments/turnaj", json={"location": "Sokolovna Praha"}, headers=headers
    )
    assert client.get(SUGGESTIONS, headers=headers).json()["locations"] == ["Sokolovna Praha"]


def test_reading_suggestions_modifies_nothing(client, auth_headers, engine):
    """spec: Suggestions are read-only and leave no trace."""
    headers = auth_headers()
    make_tournament(client, headers, "turnaj", location="Zlín")

    with Session(engine) as session:
        before = [
            (t.slug, t.location, t.bank_account, t.organizers)
            for t in session.scalars(select(Tournament)).all()
        ]

    client.get(SUGGESTIONS, headers=headers)

    with Session(engine) as session:
        after = [
            (t.slug, t.location, t.bank_account, t.organizers)
            for t in session.scalars(select(Tournament)).all()
        ]
    assert before == after


@pytest.mark.parametrize("field", ["display_name", "subtitle", "description"])
def test_no_other_field_is_suggested(client, auth_headers, field):
    """spec: A field outside the three. The payload names exactly three lists;
    a fourth field would have to be added here deliberately."""
    headers = auth_headers()
    make_tournament(client, headers, "turnaj", location="Zlín")
    body = client.get(SUGGESTIONS, headers=headers).json()
    assert set(body) == {"locations", "bank_accounts", "organizers"}
    assert field not in body
