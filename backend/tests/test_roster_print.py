"""A discipline roster typeset to PDF and PNG (spec roster-print)."""

import io
import re

from PIL import Image

from tests.test_export_tables import organizer_with_tournament

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def roster_rows(count, club="Klub"):
    return [[str(i), f"Šermíř {i}", "CZE", club, "10234", "12", "Ano"] for i in range(1, count + 1)]


def print_roster(client, headers, fmt="pdf", **body):
    payload = {"discipline": "LS", "rows": roster_rows(3), "line_after": None, **body}
    return client.post(f"/api/tournaments/cup/export/roster.{fmt}", json=payload, headers=headers)


def test_both_formats_are_their_format(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)

    pdf = print_roster(client, organizer, "pdf")
    png = print_roster(client, organizer, "png")

    assert pdf.status_code == 200, pdf.text
    assert pdf.content.startswith(b"%PDF")
    assert pdf.headers["content-type"] == "application/pdf"
    assert png.status_code == 200, png.text
    assert png.content.startswith(PNG_SIGNATURE)


def test_the_file_is_named_for_tournament_and_discipline(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)

    response = print_roster(client, organizer, "png", discipline="SA")

    assert response.headers["content-disposition"] == 'attachment; filename="cup-SA.png"'


def test_typst_syntax_in_a_club_is_text(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)

    response = print_roster(
        client, organizer, "pdf", rows=roster_rows(2, club='#import "x"'), line_after=1
    )

    assert response.status_code == 200, response.text


def test_a_long_roster_is_one_image(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)

    response = print_roster(client, organizer, "png", rows=roster_rows(60), line_after=24)

    assert response.status_code == 200, response.text
    image = Image.open(io.BytesIO(response.content))
    # 60 rows on one page: far taller than the page is wide
    assert image.height > 1.5 * image.width


def test_a_long_roster_prints_on_a4_pages(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)

    response = print_roster(client, organizer, "pdf", rows=roster_rows(90), line_after=24)

    assert response.status_code == 200, response.text
    boxes = re.findall(rb"/MediaBox\s*\[([^\]]*)\]", response.content)
    # several pages, every one of them A4 (595 x 842 pt)
    assert len(boxes) > 1
    for box in boxes:
        width, height = (float(n) for n in box.split()[2:4])
        assert (round(width), round(height)) == (595, 842)


def test_english_changes_the_printed_headers(client, auth_headers):
    # a Czech-speaking organizer: the console's language is what English replaces
    organizer = organizer_with_tournament(
        client, lambda **kwargs: auth_headers(language="cs", **kwargs)
    )

    czech = print_roster(client, organizer, "png", english=False)
    english = print_roster(client, organizer, "png", english=True)

    assert english.status_code == 200, english.text
    assert english.content != czech.content


def add_team_discipline(client, organizer):
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "LS-T",
            "weapon": "LS",
            "kind": "team",
            "team_min": 3,
            "team_max": 3,
            "capacity": 8,
            "fee": 3000,
        },
        headers=organizer,
    )


def team_rows(team="Wolves"):
    return [
        ["1", team, "Šermíř 1", "CZE", "Klub", "10234", "12", "Ano"],
        ["", "", "Šermíř 2", "CZE", "Klub", "", "", ""],
        ["2", "Bears", "Šermíř 3", "CZE", "Klub", "", "", "Ne"],
    ]


def test_a_team_discipline_prints_flat_from_its_own_template(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    add_team_discipline(client, organizer)

    for fmt, signature in (("pdf", b"%PDF"), ("png", PNG_SIGNATURE)):
        response = print_roster(
            client,
            organizer,
            fmt,
            discipline="LS-T",
            rows=team_rows(),
            line_after=2,
            team_starts=[0, 2],
            english=True,
        )
        assert response.status_code == 200, response.text
        assert response.content.startswith(signature)


def test_typst_syntax_in_a_team_name_is_text(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    add_team_discipline(client, organizer)

    response = print_roster(
        client,
        organizer,
        "png",
        discipline="LS-T",
        rows=team_rows(team="#set page(width: 1cm)"),
        team_starts=[0, 2],
    )

    assert response.status_code == 200, response.text
    image = Image.open(io.BytesIO(response.content))
    # the page keeps its 48em width: the name never became a set rule
    assert image.width > 1000


def test_a_roster_of_the_other_kinds_width_is_refused(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
    add_team_discipline(client, organizer)

    team_as_individual = print_roster(client, organizer, discipline="LS-T")
    individual_as_team = print_roster(client, organizer, rows=team_rows())

    assert team_as_individual.status_code == 422
    assert team_as_individual.json()["detail"] == "roster_width"
    assert individual_as_team.status_code == 422


def test_a_foreign_organizer_is_refused(client, auth_headers):
    organizer_with_tournament(client, auth_headers)
    stranger = auth_headers(email="other@example.com", name="Other")

    response = print_roster(client, stranger)

    assert response.status_code == 403


def test_the_rows_are_capped(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)

    response = print_roster(client, organizer, rows=roster_rows(1001))

    assert response.status_code == 422
