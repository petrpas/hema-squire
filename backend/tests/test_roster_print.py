"""A discipline roster typeset to PDF and PNG (spec roster-print)."""

import io

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


def test_english_changes_the_printed_headers(client, auth_headers):
    # a Czech-speaking organizer: the console's language is what English replaces
    organizer = organizer_with_tournament(
        client, lambda **kwargs: auth_headers(language="cs", **kwargs)
    )

    czech = print_roster(client, organizer, "png", english=False)
    english = print_roster(client, organizer, "png", english=True)

    assert english.status_code == 200, english.text
    assert english.content != czech.content


def test_a_team_discipline_does_not_print(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)
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

    response = print_roster(client, organizer, discipline="LS-T")

    assert response.status_code == 404


def test_a_foreign_organizer_is_refused(client, auth_headers):
    organizer_with_tournament(client, auth_headers)
    stranger = auth_headers(email="other@example.com", name="Other")

    response = print_roster(client, stranger)

    assert response.status_code == 403


def test_the_rows_are_capped(client, auth_headers):
    organizer = organizer_with_tournament(client, auth_headers)

    response = print_roster(client, organizer, rows=roster_rows(1001))

    assert response.status_code == 422
