"""The Export summary: which lines it holds, in what order, and how each counts
(spec export-summary)."""

from app import exportsummary, exporttables
from app.models import (
    Discipline,
    DisciplineKind,
    ExtraCategory,
    ExtraItem,
    Tournament,
)
from tests.test_export_tables import add_item, organizer_with_tournament, sheet_rows


def discipline(slug: str, kind: DisciplineKind = DisciplineKind.INDIVIDUAL) -> Discipline:
    return Discipline(slug=slug, name=slug, kind=kind)


def item(
    item_id: int,
    name: str,
    category: ExtraCategory,
    option_label: str | None = None,
    choices: list[str] | None = None,
) -> ExtraItem:
    return ExtraItem(
        id=item_id,
        name=name,
        category=category,
        option_label=option_label,
        option_choices=choices or [],
    )


def row(
    paid: bool = False,
    seated: list[str] | None = None,
    queued: list[str] | None = None,
    extras: dict[str, list[dict]] | None = None,
    deleted: bool = False,
) -> dict:
    return {
        "paid": paid,
        "disciplines": seated or [],
        "substitute_for": queued or [],
        "extras": extras or {},
        "_deleted": deleted,
    }


def chose(extra: ExtraItem, qty: int = 1, option: str | None = None) -> dict[str, list[dict]]:
    return {
        extra.category.value: [
            {"item_id": extra.id, "name": extra.name, "qty": qty, "option": option}
        ]
    }


def table(tournament: Tournament, rows: list[dict]) -> list[tuple[str, str | None, bool, int, int]]:
    return [
        (line.name, line.option, line.missing, line.paid, line.unpaid)
        for line in exportsummary.summary_lines(tournament, rows)
    ]


def test_disciplines_first_then_items_by_category_in_band_order():
    party = item(1, "party", ExtraCategory.AFTERPARTY)
    shirt = item(2, "shirt", ExtraCategory.MERCH)
    mask = item(3, "mask", ExtraCategory.RENTAL)
    team = discipline("LS-T", DisciplineKind.TEAM)
    tournament = Tournament(
        disciplines=[discipline("LS"), team, discipline("SA")], extra_items=[party, shirt, mask]
    )

    assert [line[0] for line in table(tournament, [])] == ["LS", "SA", "mask", "shirt", "party"]


def test_an_offered_item_nobody_chose_reads_zero():
    seminar = item(1, "seminar", ExtraCategory.SEMINAR)
    tournament = Tournament(disciplines=[], extra_items=[seminar])

    assert table(tournament, [row(paid=True)]) == [("seminar", None, False, 0, 0)]


def test_a_discipline_counts_its_seated_and_its_queue_as_its_tab_does():
    tournament = Tournament(disciplines=[discipline("LS"), discipline("SA")], extra_items=[])
    rows = [
        row(paid=True, seated=["LS"]),
        row(paid=True, seated=["LS"]),
        row(paid=False, seated=["LS"]),
        row(paid=True, queued=["LS"]),
        row(paid=False, queued=["LS"]),
        row(paid=False, queued=["LS"]),
        row(paid=True, seated=["SA"]),
    ]

    lines = exportsummary.summary_lines(tournament, rows)
    assert [(line.kind, line.name, line.paid, line.unpaid) for line in lines] == [
        ("discipline", "LS", 2, 1),
        ("queue", "LS", 1, 2),
        ("discipline", "SA", 1, 0),  # nobody queued, no queue line
    ]
    # one answer to one question: the tab's `24 + 3` is the lines' sums
    tab = exporttables.Tab(kind=exporttables.DISCIPLINE, key="LS", label="LS")
    assert exporttables.tab_counts(rows, tab) == (3, 3)


def test_items_count_pieces_split_on_the_registration_being_settled():
    party = item(1, "party", ExtraCategory.AFTERPARTY)
    mug = item(2, "mug", ExtraCategory.MERCH)
    tournament = Tournament(disciplines=[discipline("LS")], extra_items=[party, mug])
    rows = [
        row(paid=True, seated=["LS"], extras={**chose(party), **chose(mug, qty=2)}),
        # unsettled: every entry and piece it holds is unpaid
        row(paid=False, seated=["LS"], extras={**chose(party), **chose(mug, qty=3)}),
        row(paid=True, seated=["LS"], extras=chose(mug), deleted=True),
    ]

    assert table(tournament, rows) == [
        ("LS", None, False, 1, 1),
        ("mug", None, False, 2, 3),
        ("party", None, False, 1, 1),
    ]


def test_declared_choices_in_their_order_zeros_and_stale_answers_included():
    shirt = item(1, "shirt", ExtraCategory.MERCH, "size", ["S", "M", "L", "XL"])
    tournament = Tournament(disciplines=[], extra_items=[shirt])
    rows = [
        row(paid=True, extras=chose(shirt, qty=2, option="XL")),
        row(paid=False, extras=chose(shirt, option="xl")),
        row(paid=True, extras=chose(shirt, option="XXL")),  # choices edited since
        row(paid=False, extras=chose(shirt, option=None)),
        row(paid=False, extras=chose(shirt, option="M")),
    ]

    assert table(tournament, rows) == [
        ("shirt", "S", False, 0, 0),
        ("shirt", "M", False, 0, 1),
        ("shirt", "L", False, 0, 0),
        ("shirt", "XL", False, 2, 1),
        ("shirt", "XXL", False, 1, 0),
        ("shirt", None, True, 0, 1),
    ]


def test_free_text_answers_fold_case_and_spaces_in_order_of_arrival():
    jacket = item(1, "jacket", ExtraCategory.RENTAL, "size")
    tournament = Tournament(disciplines=[], extra_items=[jacket])
    rows = [
        row(paid=True, extras=chose(jacket, option="XL")),
        row(paid=True, extras=chose(jacket, option="L")),
        row(paid=False, extras=chose(jacket, option=" l ")),
    ]

    assert table(tournament, rows) == [
        ("jacket", "XL", False, 1, 0),
        ("jacket", "L", False, 1, 1),
    ]
    # no answers, and so nothing to break down: the item is still stated
    assert table(tournament, []) == [("jacket", None, False, 0, 0)]


def test_an_item_without_an_option_ignores_a_stale_answer():
    party = item(1, "party", ExtraCategory.AFTERPARTY)
    tournament = Tournament(disciplines=[], extra_items=[party])

    assert table(tournament, [row(paid=True, extras=chose(party, option="vegan"))]) == [
        ("party", None, False, 1, 0)
    ]


def test_two_items_sharing_a_name_are_counted_apart():
    first = item(1, "shirt", ExtraCategory.MERCH)
    second = item(2, "shirt", ExtraCategory.MERCH)
    tournament = Tournament(disciplines=[], extra_items=[second, first])

    assert table(tournament, [row(paid=True, extras=chose(second, qty=4))]) == [
        ("shirt", None, False, 0, 0),
        ("shirt", None, False, 4, 0),
    ]


def summary(client, organizer):
    response = client.get("/api/tournaments/cup/export/summary", headers=organizer)
    assert response.status_code == 200, response.text
    return response.json()["lines"]


def test_the_summary_is_read_over_the_tournaments_rows(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    shirt = add_item(client, organizer, "t-shirt", "merch", option_label="size")
    buyer = auth_headers(email="buyer@example.com", name="Buyer One")
    client.post(
        "/api/tournaments/cup/register",
        json={
            "disciplines": ["LS"],
            "extras": [{"extra_item_id": shirt["id"], "qty": 2, "option_value": "XL"}],
        },
        headers=buyer,
    )

    assert [
        (line["kind"], line["option"], line["paid"], line["unpaid"])
        for line in summary(client, organizer)
    ] == [
        ("discipline", None, 0, 1),
        ("discipline", None, 0, 0),
        ("item", "XL", 0, 2),
    ]

    # a deletion reaches the summary on the next read
    rows, _ = sheet_rows(client, organizer)
    client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "export",
            "kind": "row_delete",
            "target": rows["Buyer One"]["id"],
            "payload": {},
        },
        headers=organizer,
    )
    assert [(line["paid"], line["unpaid"]) for line in summary(client, organizer)] == [
        (0, 0),
        (0, 0),
        (0, 0),
    ]
