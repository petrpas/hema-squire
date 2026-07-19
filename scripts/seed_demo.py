"""Seed a demo tournament for local testing. Idempotent — reruns are no-ops.

Run from the backend directory (dev.sh --seed does this):

    cd backend && uv run python ../scripts/seed_demo.py

Creates an organizer account, the "Na Duel! 2026" tournament with four
disciplines, four registered fencers (one paid via a simulated Fio CSV
statement), and an imported Google-Form-style table. Without an Anthropic
key the imported rows would stay unparsed, so their parse decisions are
backfilled directly — the sheet then shows what a configured LLM produces.
"""

import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))  # run from backend/ so `app` imports

BASE = "http://localhost:8000"
ORGANIZER = ("petr@example.com", "demo-heslo-123", "Petr Organizátor")
SLUG = "na-duel-2026"


def call(method, path, token=None, body=None, files=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if files:
        boundary = "----seedboundary"
        name, filename, content = files
        payload = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{filename}"\r\nContent-Type: text/csv\r\n\r\n'
        ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        request = urllib.request.Request(
            BASE + path, data=payload, headers=headers, method=method
        )
    elif body is not None:
        headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            BASE + path, data=json.dumps(body).encode(), headers=headers, method=method
        )
    else:
        request = urllib.request.Request(BASE + path, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"null")


def main() -> None:
    slugs = [t["slug"] for t in call("GET", "/api/tournaments")]
    if SLUG in slugs:
        print(f"'{SLUG}' already exists — nothing to seed.")
        print(f"organizer login: {ORGANIZER[0]} / {ORGANIZER[1]}")
        return

    email, password, name = ORGANIZER
    try:
        token = call("POST", "/api/auth/signup", body={
            "email": email, "password": password, "display_name": name,
        })["token"]
    except urllib.error.HTTPError:
        token = call("POST", "/api/auth/login", body={
            "email": email, "password": password,
        })["token"]

    call("POST", "/api/tournaments", token, {
        "slug": SLUG, "display_name": "Na Duel! 2026", "date": "2026-10-17",
    })
    # itemized pricing (design D8): the demo exercises the new path — extra
    # services across categories plus a count discount and an early-bird
    # percent discount. Legacy fee_early / weapon_rental_fee / afterparty_fee
    # / early_bird_until stay unset, as new-style tournaments never set them.
    call("PATCH", f"/api/tournaments/{SLUG}", token, {
        "bank_account": "CZ6508000000192000145399",
        "location": "Praha, Sportovní hala Podolí",
        "organizer_names": ["Duelanti od sv. Rocha", "Pražský Šermířský Klub"],
        "registration_opens": "2026-01-01",
        "discounts": [
            {
                "name": "Sleva za 2 disciplíny",
                "condition": {"kind": "discipline_count", "count": 2},
                "effect": {"kind": "fixed", "value": 150},
                "scope": ["discipline"],
            },
            {
                "name": "Early bird",
                "condition": {"kind": "early", "until": "2026-08-31"},
                "effect": {"kind": "percent", "value": 10},
                "scope": ["discipline"],
            },
        ],
    })
    for code, capacity, fee in [("LS", 32, 900), ("SA", 24, 800),
                                ("SB", 16, 800), ("RD", 16, 850)]:
        call("POST", f"/api/tournaments/{SLUG}/disciplines", token,
             {"code": code, "capacity": capacity, "fee": fee})

    extra_items = {}
    for name, category, price, max_qty in [
        ("Páteční seminář", "seminar", 300, 1),
        ("Zapůjčení zbraně", "rental", 200, 2),
        ("Afterparty sobota", "afterparty", 350, 1),
        ("Tričko turnaje", "merch", 250, 3),
    ]:
        item = call("POST", f"/api/tournaments/{SLUG}/extra-items", token,
                    {"name": name, "category": category, "price": price, "max_qty": max_qty})
        extra_items[name] = item["id"]

    def extra(name, qty=1):
        return {"extra_item_id": extra_items[name], "qty": qty}

    fencers = [
        ("jan.novak@example.com", "Jan Novák", ["LS", "SB"],
         [extra("Afterparty sobota"), extra("Zapůjčení zbraně")]),
        ("anna.k@example.com", "Anna Kowalska", ["SA"], []),
        ("tom.a@example.com", "Tom Andersen", ["LS", "SA"],
         [extra("Páteční seminář"), extra("Zapůjčení zbraně", 2)]),
        ("petr.s@example.com", "Petr Svoboda", ["RD"], [extra("Tričko turnaje")]),
    ]
    jan_token = None
    for fencer_email, fencer_name, disciplines, extras in fencers:
        account = call("POST", "/api/auth/signup", body={
            "email": fencer_email, "password": password, "display_name": fencer_name,
        })
        if jan_token is None:
            jan_token = account["token"]
        registration = call("POST", f"/api/tournaments/{SLUG}/register",
                            account["token"],
                            {"disciplines": disciplines, "extras": extras})
        print(f"registered {fencer_name}: VS {registration['vs']} "
              f"· {registration['total_amount']} CZK")

    # pay the first fencer through the CSV bank-statement path
    my = call("GET", f"/api/tournaments/{SLUG}/my-registration", jan_token)
    amount = my["total_amount"]
    czk = f"{amount // 1000} {amount % 1000:03d},00" if amount >= 1000 else f"{amount},00"
    statement = (
        "meta;data\n\n"
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;"
        "Název protiúčtu;Protiúčet\n"
        f"9001;15.07.2026;{czk};CZK;{my['vs']};;;VS {my['vs']};Jan Novák;123/0800\n"
    ).encode()
    matched = call("POST", f"/api/tournaments/{SLUG}/payments/import-statement",
                   token, files=("file", "vypis.csv", statement))
    print(f"bank statement: {matched}")

    # imported legacy table (google-form style)
    table = (
        "Časová značka,E-mailová adresa,Jméno / Full Name,Klub / Club,"
        "Národnost / Nationality,Disciplíny / Disciplines,hemaratings.com ID,"
        "Afterparty,Poznámka / Note\n"
        "1.6.2026 14:15:27,alex.b@example.com,Alexander Bryzgalov,Twerchhau,RU,"
        "šavle / sabre,,Asi jo / Likely so,\n"
        "1.6.2026 15:02:00,lukas.m@example.com,Lukas Mueller,Berlin Schwert,DE,"
        "longsword,8821,Ano / Yes,vegetarián\n"
        "2.6.2026 09:30:12,marie.n@example.com,Marie Nová,Praha HEMA,CZ,"
        "šavle / sabre,,Ne / No,\n"
    ).encode()
    outcome = call("POST", f"/api/tournaments/{SLUG}/import", token,
                   files=("file", "registrace_v0.csv", table))
    print(f"table import: {outcome}")

    if outcome.get("unparsed"):
        _backfill_parse_decisions()
        print(f"backfilled {outcome['unparsed']} parse decisions (no LLM key set)")

    print(f"\ndone — organizer login: {email} / {password}")


def _backfill_parse_decisions() -> None:
    """What the LLM parser would return for the three imported rows."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.db import engine
    from app.importer import ParsedDiscipline, ParsedFencer, store_decision
    from app.models import ImportedRow, Tournament

    records = {
        1: ParsedFencer(
            registration_time="2026-06-01T14:15:27", name="Alexander Bryzgalov",
            nationality="RU", email="alex.b@example.com", club="Twerchhau",
            disciplines=[ParsedDiscipline(weapon="SA")],
            problems="afterparty answer ambiguous (Asi jo)"),
        2: ParsedFencer(
            registration_time="2026-06-01T15:02:00", name="Lukas Mueller",
            nationality="DE", email="lukas.m@example.com", club="Berlin Schwert",
            hr_id=8821, disciplines=[ParsedDiscipline(weapon="LS")],
            after_party="Yes", notes="vegetarián"),
        3: ParsedFencer(
            registration_time="2026-06-02T09:30:12", name="Marie Nová",
            nationality="CZ", email="marie.n@example.com", club="Praha HEMA",
            disciplines=[ParsedDiscipline(weapon="SA")], after_party="No"),
    }
    with Session(engine) as session:
        tournament = session.scalar(select(Tournament).where(Tournament.slug == SLUG))
        rows = session.scalars(
            select(ImportedRow).where(ImportedRow.tournament_id == tournament.id)
        ).all()
        for row in rows:
            store_decision(session, tournament, "parse", row.key,
                           records[row.row_number].model_dump())
        session.commit()


if __name__ == "__main__":
    main()
