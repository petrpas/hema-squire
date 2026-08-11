"""Global VS lookup and cross-tournament set-aside behavior
(design add-structured-vs, Decision 4/5)."""

import io

from tests.conftest import enable_payments, publish


def create_tournament(client, organizer, slug, date="2026-12-05"):
    response = client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": slug, "date": date},
        headers=organizer,
    )
    assert response.status_code == 201, response.text
    enable_payments(client, organizer, slug)
    client.patch(
        f"/api/tournaments/{slug}",
        json={
            "location": "Brno",
            "organizers": [{"name": "Org", "link": None}],
            "bank_account": "CZ6508000000192000145399",
        },
        headers=organizer,
    )
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 32, "fee": 800},
        headers=organizer,
    )
    publish(client, organizer, slug)
    return response.json()


def register(client, slug, headers):
    response = client.post(
        f"/api/tournaments/{slug}/register", json={"disciplines": ["LS"]}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def statement_for(vs, amount="800,00"):
    return (
        "meta;data\n\n"
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet\n"
        f"1;01.08.2026;{amount};CZK;{vs};;;;;\n"
    ).encode()


def import_statement(client, headers, slug, content):
    return client.post(
        f"/api/tournaments/{slug}/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(content), "text/csv")},
        headers=headers,
    ).json()


def test_sibling_tournaments_transaction_is_set_aside_then_matches_its_own(
    client, auth_headers
):
    """6.10: a transaction carrying A's VS, ingested by B, is set aside — not
    in B's unmatched queue, no payment, no email — and matches normally when
    A ingests its own copy."""
    organizer = auth_headers()
    create_tournament(client, organizer, "aa")  # series 1 -> prefix 2601
    create_tournament(client, organizer, "bb")  # series 2 -> prefix 2602
    fencer_a = auth_headers(email="fa@example.com", name="FA")
    reg_a = register(client, "aa", fencer_a)
    assert reg_a["vs"] == 2601001

    # B ingests a statement that (as on a shared bank account) also carries
    # A's transaction
    result = import_statement(client, organizer, "bb", statement_for(reg_a["vs"]))
    assert result["matched"] == 0
    assert result["unmatched"] == 0
    assert result["flagged"] == 0
    assert result["set_aside"] == 1

    b_unmatched = client.get(
        "/api/tournaments/bb/payments/unmatched", headers=organizer
    ).json()
    assert b_unmatched == []

    # A's registration is untouched by B's ingestion
    a_state = client.get("/api/tournaments/aa/my-registration", headers=fencer_a).json()
    assert a_state["state"] == "reserved"

    # A ingesting its own copy of the same transaction matches normally
    own = import_statement(client, organizer, "aa", statement_for(reg_a["vs"]))
    assert own["matched"] == 1
    assert own["set_aside"] == 0

    a_state_after = client.get(
        "/api/tournaments/aa/my-registration", headers=fencer_a
    ).json()
    assert a_state_after["state"] == "paid"


def test_mistyped_prefix_does_not_route_to_a_sibling(client, auth_headers):
    """6.11: a VS whose prefix names a real tournament but whose whole value
    matches no registration lands in the unmatched queue, selecting no
    tournament from its prefix."""
    organizer = auth_headers()
    create_tournament(client, organizer, "aa")  # series 1 -> prefix 2601
    create_tournament(client, organizer, "bb")  # series 2 -> prefix 2602
    register(client, "bb", auth_headers(email="fb@example.com", name="FB"))

    # 2602999: names bb's real prefix (2602) but no registration owns it
    result = import_statement(client, organizer, "aa", statement_for(2602999))
    assert result["matched"] == 0
    assert result["set_aside"] == 0
    assert result["unmatched"] == 1

    queue = client.get("/api/tournaments/aa/payments/unmatched", headers=organizer).json()
    assert queue[0]["status_reason"] == "unknown_vs"
