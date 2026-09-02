"""Table import: file intake, parse-decision persistence, problems surfacing."""

import io

from conftest import outcome, settle

from app.importer import ImportParser, ParsedFencer, get_import_parser
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

    def parse_batch(self, rows, disciplines, rentals):
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
                    disciplines=["SA"],
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
        json={"slug": "SA", "weapon": "SA", "capacity": 20, "fee": 800},
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
    # the upload records the batch and returns; the parse runs behind it
    assert response.status_code == 202, response.text
    assert response.json()["rows"] == 2

    body = outcome(client, organizer)
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
    settle(client, organizer)
    first_ids = sorted(
        r["id"] for r in get_sheet(client, organizer)["rows"] if r["id"].startswith("imp:")
    )

    # identical re-upload: no LLM call, no operation to run at all, and the
    # outcome comes straight back (spec, Reused rows are not work)
    reuploaded = upload(client, organizer)
    assert reuploaded.status_code == 202
    body = reuploaded.json()
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
    assert upload(client, organizer, content=grown).status_code == 202
    body = outcome(client, organizer)
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
    assert response.status_code == 202, response.text
    assert response.json()["rows"] == 1
    assert outcome(client, organizer)["rows"] == 1


def test_blank_lines_are_not_fencers(client, auth_headers):
    """A trailing empty line is what a spreadsheet export ends with; imported
    as a row it reaches the parser, which has to name a record with nothing in
    it, and the table gains a fencer nobody entered."""
    organizer = auth_headers()
    setup(client, organizer)
    parser = FakeParser()
    override_parser(parser)

    padded = CSV + ",,,,,,,,\n" + "\n"
    assert upload(client, organizer, content=padded).status_code == 202
    body = outcome(client, organizer)

    assert body["rows"] == 2
    rows = [r for r in get_sheet(client, organizer)["rows"] if r["id"].startswith("imp:")]
    assert len(rows) == 2


def test_a_semicolon_separated_export_is_read_as_columns(client, auth_headers):
    """A Czech bank separates with semicolons, because there a comma is the
    decimal point. Read with commas, the whole line is one column — and every
    embedded decimal comma cuts it short, so `1214,03` ends the row at `1214`
    and the payer's name, three columns later, is simply gone. Nothing
    downstream can tell that from a bank that really does write one column."""
    from app.importer import read_table

    table = (
        '"Datum";"Objem";"Měna";"Zpráva pro příjemce";"Poznámka"\r\n'
        '"07.04.2026";"1214,03";"CZK";"NaDuel26: CHEREAU - Sabre, and bocler";"M. PAUL CHEREAU"\r\n'
    ).encode("utf-8-sig")

    assert read_table("vypis.csv", table) == [
        {
            "Datum": "07.04.2026",
            "Objem": "1214,03",
            "Měna": "CZK",
            "Zpráva pro příjemce": "NaDuel26: CHEREAU - Sabre, and bocler",
            "Poznámka": "M. PAUL CHEREAU",
        }
    ]


def test_a_comma_separated_export_still_reads_as_commas(client, auth_headers):
    """The registration form exports with commas and its text is full of
    semicolons-free prose; sniffing must not steal it away from the comma."""
    from app.importer import read_table

    table = b'Name,Club,Note\nJan,AKA,"sabre, sword and buckler"\n'
    assert read_table("regs.csv", table) == [
        {"Name": "Jan", "Club": "AKA", "Note": "sabre, sword and buckler"}
    ]


def test_ragged_rows_align_to_the_header(client, auth_headers):
    """Real exports are ragged: a bank writes a preamble line, a message field
    carries an unquoted separator. Both shapes reached `row_fingerprint`, which
    sorts the keys — and a long row's overflow arrives under csv.DictReader's
    restkey, which is None, so sorting it against the column names raised
    TypeError mid-import."""
    from app.importer import read_table, row_fingerprint

    table = b"a,b,c\nlong,row,with,extra,cells\nshort,row\n"
    rows = read_table("statement.csv", table)

    assert rows == [
        {"a": "long", "b": "row", "c": "with"},
        {"a": "short", "b": "row", "c": ""},
    ]
    # every key and value a string, so the fingerprint can sort them
    for raw in rows:
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in raw.items())
        assert row_fingerprint(raw)


def test_ragged_xlsx_rows_align_to_the_header(client, auth_headers):
    """The same rule for the other reader — a sheet whose rows outrun or fall
    short of the header row."""
    import openpyxl

    from app.importer import read_table, row_fingerprint

    workbook = openpyxl.Workbook()
    for row in (["a", "b", "c"], ["long", "row", "with", "extra"], ["short"]):
        workbook.active.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)

    # openpyxl pads the header row out to the widest row, so the overflow
    # cell invents an unnamed fourth column; it is dropped with its header
    rows = read_table("statement.xlsx", buffer.getvalue())
    assert rows == [
        {"a": "long", "b": "row", "c": "with"},
        {"a": "short", "b": "", "c": ""},
    ]
    for raw in rows:
        assert row_fingerprint(raw)


def test_unsupported_format_rejected(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    override_parser(FakeParser())
    response = upload(client, organizer, filename="regs.pdf")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 9.9 The parser chooses a discipline instead of describing one
# (design discipline-identity D7/D8)
# ---------------------------------------------------------------------------


def setup_split_tournament(client, organizer):
    """A tournament offering two longsword tiers sharing a classification —
    the ambiguity scenario a legacy "weapon only" row cannot resolve on its
    own (design D8)."""
    client.post(
        "/api/tournaments",
        json={"slug": "split", "display_name": "Split", "date": "2026-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/split/disciplines",
        json={
            "slug": "LS-A", "weapon": "LS", "name": "Longsword Top",
            "capacity": 20, "fee": 800,
        },
        headers=organizer,
    )
    client.post(
        "/api/tournaments/split/disciplines",
        json={
            "slug": "LS-B", "weapon": "LS", "name": "Longsword Open",
            "capacity": 20, "fee": 800,
        },
        headers=organizer,
    )


class BracketAwareParser:
    """Stands in for the LLM: resolves a row naming a bracket to that
    bracket's slug, and leaves a row naming only the weapon unresolved with a
    problem (design D8) — the offered `disciplines` argument is exactly the
    `(slug, name)` pairs the real prompt is built from."""

    def parse_batch(self, rows, disciplines, rentals):
        parsed = []
        for raw in rows:
            text = raw.get("row", "")
            if "Top" in text:
                slugs, problem = ["LS-A"], None
            elif "Open" in text:
                slugs, problem = ["LS-B"], None
            else:
                slugs, problem = [], "ambiguous: longsword split into two brackets"
            parsed.append(
                ParsedFencer(
                    registration_time="2026-04-01T14:15:27",
                    name=text or "Fencer",
                    disciplines=slugs,
                    problems=problem,
                )
            )
        return parsed


def upload_split(client, organizer, rows):
    content = "row\n" + "\n".join(rows) + "\n"
    return client.post(
        "/api/tournaments/split/import",
        files={"file": ("regs.csv", io.BytesIO(content.encode()), "text/csv")},
        headers=organizer,
    )


def split_sheet_rows(client, organizer):
    rows = client.get("/api/tournaments/split/sheet", headers=organizer).json()["rows"]
    return [r for r in rows if r["id"].startswith("imp:")]


def test_row_naming_bracket_resolves(client, auth_headers):
    organizer = auth_headers()
    setup_split_tournament(client, organizer)
    override_parser(BracketAwareParser())
    upload_split(client, organizer, ["Alice Top"])
    assert split_sheet_rows(client, organizer)[0]["disciplines"] == ["LS-A"]


def test_ambiguous_row_left_unresolved_with_problem(client, auth_headers):
    organizer = auth_headers()
    setup_split_tournament(client, organizer)
    override_parser(BracketAwareParser())
    upload_split(client, organizer, ["Bob Longsword"])
    row = split_sheet_rows(client, organizer)[0]
    assert row["disciplines"] == []
    assert row["problems"] and "ambiguous" in row["problems"]


def test_old_shape_decision_resolves_when_unambiguous():
    """A decision stored before disciplines carried slugs describes a
    discipline as weapon/gender/material; it resolves without a new LLM call
    when exactly one offered discipline matches that classification."""
    from types import SimpleNamespace

    from app.models import Discipline
    from app.sheet import _resolve_discipline_slugs

    tournament = SimpleNamespace(
        disciplines=[Discipline(slug="LS", weapon="LS", gender="", material="")]
    )
    slugs, problems = _resolve_discipline_slugs(
        tournament, [{"weapon": "LS", "gender": "", "material": ""}]
    )
    assert slugs == ["LS"]
    assert problems == []


def test_old_shape_decision_ambiguous_after_split():
    """The same old-shape decision, read after the organizer has since split
    that weapon into two disciplines, is reported unresolved rather than
    silently attached to either (design D8, Risks)."""
    from types import SimpleNamespace

    from app.models import Discipline
    from app.sheet import _resolve_discipline_slugs

    tournament = SimpleNamespace(
        disciplines=[
            Discipline(slug="LS-A", weapon="LS", gender="", material=""),
            Discipline(slug="LS-B", weapon="LS", gender="", material=""),
        ]
    )
    slugs, problems = _resolve_discipline_slugs(
        tournament, [{"weapon": "LS", "gender": "", "material": ""}]
    )
    assert slugs == []
    assert len(problems) == 1


# ---------------------------------------------------------------------------
# What the tournament lends is offered to the parser, and borrowed once
# ---------------------------------------------------------------------------


class RentalParser(ImportParser):
    """Stands in for the LLM: echoes back what it was offered, and repeats an
    item the way a source row does — once per discipline entered."""

    def __init__(self):
        self.offered_rentals = None

    def parse_batch(self, rows, disciplines, rentals):
        self.offered_rentals = rentals
        return [
            ParsedFencer(
                registration_time="2026-04-01T14:15:27",
                name=raw["Jméno / Full Name"].strip(),
                disciplines=["SA", "SB", "SA"],
                borrow=["Sabre", "Sabre", "Buckler"],
            )
            for raw in rows
        ]


def test_offered_rentals_reach_the_parser_and_are_borrowed_once(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": 20, "fee": 800},
        headers=organizer,
    )
    for name in ("Sabre", "Buckler"):
        client.post(
            "/api/tournaments/cup/extra-items",
            json={"name": name, "category": "rental", "price": 50, "max_qty": 1},
            headers=organizer,
        )
    client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "T-shirt", "category": "merch", "price": 250, "max_qty": 1},
        headers=organizer,
    )
    parser = RentalParser()
    override_parser(parser)

    assert upload(client, organizer).status_code == 202
    settle(client, organizer)
    # what the tournament lends, and nothing it merely sells
    assert parser.offered_rentals == ["Sabre", "Buckler"]

    row = next(r for r in get_sheet(client, organizer)["rows"] if r["id"].startswith("imp:"))
    assert row["weapon_rentals"] == ["Sabre", "Buckler"]
    assert row["disciplines"] == ["SA", "SB"]
