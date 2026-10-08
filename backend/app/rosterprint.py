"""A discipline roster typeset to PDF or PNG (change roster-print).

The rows arrive formatted, exactly as the Export tab shows them; this module
only typesets them. The template reads them from `sys.inputs` as JSON, so no
name or club ever becomes Typst source (design D2), and the fonts it is set in
ship beside it, so the output does not depend on the host (design D3).
"""

import json
from pathlib import Path
from typing import Literal

import typst

_TYPST_DIR = Path(__file__).parent / "typst"
_TEMPLATE = _TYPST_DIR / "templates" / "discipline_roster.typ"
_FONTS = _TYPST_DIR / "fonts"

# hema-agent rendered at the binding's default of 144; 200 keeps the text crisp
# in an Instagram post at the page's 48em width (design D3)
_PNG_PPI = 200

RosterFormat = Literal["pdf", "png"]


def render(
    title: str,
    headers: list[str],
    rows: list[list[str]],
    last_in: int,
    fmt: RosterFormat,
) -> bytes:
    """The roster as one document of `fmt`.

    `last_in` is the 1-based row the heavier rule falls under. The page is as
    tall as its content, so a PNG is one image however long the roster; should
    the binding still split it, the first page is what is returned."""
    roster = json.dumps({"title": title, "headers": headers, "rows": rows, "last_in": last_in})
    result = typst.compile(
        str(_TEMPLATE),
        format=fmt,
        font_paths=[str(_FONTS)],
        ignore_system_fonts=True,
        ppi=_PNG_PPI if fmt == "png" else None,
        sys_inputs={"roster": roster},
    )
    return _first_page(result)


def _first_page(result: bytes | list[bytes]) -> bytes:
    # the binding's stub promises `bytes` where no output path is given, but a
    # document of several pages comes back as a list of them, one per page
    return result[0] if isinstance(result, list) else result
