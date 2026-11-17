"""Pool sheets as PDF, from the templates adopted from `hema-agent` (spec
floor-pools, Pool sheets list the bouts in order).

The templates carry `{{placeholder}}` fields, as `hema-agent` filled them;
they are filled here and compiled from source. The fonts are the office's
bundled ones, read by path.
"""

import json
import tempfile
from pathlib import Path

import typst

_TEMPLATES = Path(__file__).parent / "typst"
_FONTS = Path(__file__).parent.parent / "typst" / "fonts"


class NoTemplate(Exception):
    """The adopted templates print pools of 4 to 8 only."""


def _escape(text: str) -> str:
    # Typst markup: these would start code, labels, references or emphasis
    for char in ("\\", "#", "[", "]", "*", "_", "@", "<", ">", "$", "`"):
        text = text.replace(char, "\\" + char)
    return text


def pool_sheet(tournament: str, discipline: str, number: int, names: list[str]) -> bytes:
    """One pool's sheet: its fencers in sheet order and its bouts in the
    template's order."""
    template = _TEMPLATES / f"pool_table_{len(names)}.typ"
    if not template.exists():
        raise NoTemplate(len(names))
    source = template.read_text(encoding="utf-8")
    fields = {
        "tournament": tournament,
        "discipline": discipline,
        "pool_no": str(number),
    }
    for index, name in enumerate(names, start=1):
        fields[f"fencer_{index}"] = name
        fields[f"f{index}"] = str(index)
    for field, value in fields.items():
        source = source.replace("{{" + field + "}}", _escape(value))
    # compiled from a file, as the office's prints are: the binding's paths
    # and its stub agree on that form
    with tempfile.TemporaryDirectory() as directory:
        filled = Path(directory) / "sheet.typ"
        filled.write_text(source, encoding="utf-8")
        result = typst.compile(
            str(filled), format="pdf", font_paths=[str(_FONTS)], ignore_system_fonts=True
        )
    return _first_page(result)


def _first_page(result: bytes | list[bytes]) -> bytes:
    # the binding's stub promises `bytes`, but several pages come back as a list
    return result[0] if isinstance(result, list) else result


def _string(text: str) -> str:
    """A Typst string literal: plain text, never markup."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def bracket_sheet(
    tournament: str,
    discipline: str,
    size: int,
    by_seed: list[str | None],
    advanced: list[list[str | None]],
) -> bytes:
    """The bracket as recorded so far, from the adopted elimination template:
    the seeds in their slots (`None` a bye), and per later round the names that
    have advanced into its slots."""
    template = _TEMPLATES / f"elimination_{size}.typ"
    if not template.exists():
        raise NoTemplate(size)
    fencers = ",\n".join(f"  {_string(n)}" if n is not None else "  []" for n in by_seed)
    byes = ",\n".join("  true" if n is None else "  false" for n in by_seed)
    rounds = ",\n".join(
        "  (" + ", ".join(_string(n) if n is not None else "none" for n in names) + ",)"
        for names in advanced
    )
    block = (
        f"#let fencers = (\n{fencers},\n)\n"
        f"#let is_bye = (\n{byes},\n)\n"
        f"#let advanced = (\n{rounds}{',' if advanced else ''}\n)"
    )
    source = template.read_text(encoding="utf-8")
    source = source.replace("{{fencers}}", block)
    source = source.replace("{{tournament}}", _escape(tournament))
    source = source.replace("{{discipline}}", _escape(discipline))
    with tempfile.TemporaryDirectory() as directory:
        filled = Path(directory) / "bracket.typ"
        filled.write_text(source, encoding="utf-8")
        result = typst.compile(
            str(filled), format="pdf", font_paths=[str(_FONTS)], ignore_system_fonts=True
        )
    return _first_page(result)


def table_pdf(title: str, subtitle: str, headers: list[str], rows: list[list[str]]) -> bytes:
    """A titled table on A4: an official's rozpis or a piste's sheet."""
    payload = json.dumps({"title": title, "subtitle": subtitle, "headers": headers, "rows": rows})
    result = typst.compile(
        str(_TEMPLATES / "table.typ"),
        format="pdf",
        font_paths=[str(_FONTS)],
        ignore_system_fonts=True,
        sys_inputs={"table": payload},
    )
    return _first_page(result)
