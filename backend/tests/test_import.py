"""Table import: file intake, parse-decision persistence, problems surfacing."""

import io

from app.importer import ImportParser, ParsedDiscipline, ParsedFencer, get_import_parser
from app.main import app

CSV = (
    "Časová značka,E-mailová adresa,Jméno / Full Name,Klub / Club,"
    "Národnost / Nationality,Disciplíny / Disciplines,hemaratings.com ID,"
    "Afterparty,Poznámka / Note\n"
    "1.4.2026 14:15:27,alex@example.com,Alexander Bryzgalov ,Twerchhau,"
    'Russian ,šavle / sabre,,Asi jo / Likely so,\n'
    "1.4.2026 14:16:13,ala@example.com,Aleksandra Grzegorczyk,Mordschlag,"
    'PL,"šavle / sabre, meč a štítek / sword and buckler",1234,Ano / Yes,dorazím později\n'
)


class FakeParser:
    """Deterministic stand-in for the LLM: derives records from raw columns."""

    def __init__(self):
        self.calls = 0

    def parse(self, rows, disciplines):
        self.calls += 1
        parsed = []
        for raw in rows:
            name = raw["Jméno / Full Name"].strip()
            hr = raw.get("hemaratings.com ID", "")
            nationality_raw = raw.get("Národnost / Nationality", "")
            afterparty_raw = raw.get("Afterparty", "")
            parsed.append(
                ParsedFencer(
                    registration_time="2026-04-01T14:15:27",
                    name=name,
                    nationality="RU" if "Russian" in nationality_raw else "PL",
                    email=raw["E-mailová adresa"],
                    club=raw["Klub / Club"],
                    hr_id=int(hr) if hr.strip().isdigit() else None,
                    disciplines=[ParsedDiscipline(weapon="SA")],
                    notes=raw.get("Poznámka / Note") or None,
                    problems="afterparty answer ambiguous" if "Asi" in afterparty_raw else None,
                )
            )
        return parsed


def setup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "SA", "capacity": 20, "fee": 800},
        headers=organizer,
    )


def upload(client, organizer, content=CSV, filename="regs.csv"):
    return client.post(
        "/api/tournaments/cup/import",
        files={"file": (filename, io.BytesIO(content.encode()), "text/csv")},
        headers=organizer,
    )


def override_parser(parser: ImportParser):
    app.dependency_overrides[get_import_parser] = lambda: parser


def get_sheet(client, organizer):
    return client.get("/api/tournaments/cup/sheet", headers=organizer).json()


def test_import_creates_rows_with_provenance_and_problems(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    parser = FakeParser()
    override_parser(parser)

    response = upload(client, organizer)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rows"] == 2
    assert body["parsed"] == 2
    assert body["problems"] == [{"row": 1, "problems": "afterparty answer ambiguous"}]

    rows = [r for r in get_sheet(client, organizer)["rows"] if r["id"].startswith("imp:")]
    assert len(rows) == 2
    by_name = {r["name"]: r for r in rows}
    alex = by_name["Alexander Bryzgalov"]
    assert alex["state"] == "imported"
    assert alex["disciplines"] == ["SA"]
    assert alex["problems"] == "afterparty answer ambiguous"
    assert alex["_source"] == {"file": "regs.csv", "row": 1}
    assert by_name["Aleksandra Grzegorczyk"]["hr_id"] == 1234


def test_reupload_reuses_decisions_and_keeps_row_identity(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    parser = FakeParser()
    override_parser(parser)

    upload(client, organizer)
    first_ids = sorted(
        r["id"] for r in get_sheet(client, organizer)["rows"] if r["id"].startswith("imp:")
    )

    # identical re-upload: no LLM call, identical row keys
    body = upload(client, organizer).json()
    assert body["parsed"] == 0
    assert body["reused"] == 2
    assert parser.calls == 1
    second_ids = sorted(
        r["id"] for r in get_sheet(client, organizer)["rows"] if r["id"].startswith("imp:")
    )
    assert second_ids == first_ids

    # a grown table parses only the new row; rules on old rows still apply
    target = first_ids[0]
    client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "parsing",
            "kind": "field_edit",
            "target": target,
            "payload": {"field": "club", "value": "Twerchhau e.V."},
        },
        headers=organizer,
    )
    grown = CSV + (
        "2.4.2026 09:00:00,jan@example.com,Jan Testovací,Praha,CZ,šavle / sabre,,Ne / No,\n"
    )
    body = upload(client, organizer, content=grown).json()
    assert body["rows"] == 3
    assert body["parsed"] == 1  # only the new row hits the parser
    assert body["reused"] == 2

    sheet = get_sheet(client, organizer)
    edited = next(r for r in sheet["rows"] if r["id"] == target)
    assert edited["club"] == "Twerchhau e.V."


def test_import_without_llm_reports_unparsed_rows(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_import_parser] = lambda: None

    body = upload(client, organizer).json()
    assert body["detail"] == "llm_not_configured"
    assert body["unparsed"] == 2

    rows = [r for r in get_sheet(client, organizer)["rows"] if r["id"].startswith("imp:")]
    assert all(r["problems"] == "unparsed" for r in rows)


def test_xlsx_intake(client, auth_headers):
    import openpyxl

    organizer = auth_headers()
    setup(client, organizer)
    parser = FakeParser()
    override_parser(parser)

    workbook = openpyxl.Workbook()
    ws = workbook.active
    ws.append(
        ["Časová značka", "E-mailová adresa", "Jméno / Full Name", "Klub / Club",
         "Národnost / Nationality", "Disciplíny / Disciplines", "hemaratings.com ID",
         "Afterparty", "Poznámka / Note"]
    )
    ws.append(["1.4.2026 14:15:27", "alex@example.com", "Alexander Bryzgalov", "Twerchhau",
               "Russian", "šavle / sabre", "", "Ano", ""])
    buffer = io.BytesIO()
    workbook.save(buffer)

    response = client.post(
        "/api/tournaments/cup/import",
        files={"file": ("regs.xlsx", io.BytesIO(buffer.getvalue()),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=organizer,
    )
    assert response.status_code == 200, response.text
    assert response.json()["rows"] == 1


def test_unsupported_format_rejected(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    override_parser(FakeParser())
    response = upload(client, organizer, filename="regs.pdf")
    assert response.status_code == 422
