"""Pool sheets as PDF, from the templates adopted from `hema-agent` (spec
floor-pools, Pool sheets list the bouts in order).

The templates carry `{{placeholder}}` fields, as `hema-agent` filled them;
they are filled here and compiled from source. The fonts are the office's
bundled ones, read by path.
"""

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
