"""Guards the frontend's reading of the setup checklist against the keys the
backend actually emits.

`setup.setup_missing` names what a published tournament still lacks, and
`guard_published_completeness` refuses EVERY write while it names anything —
so a key the client cannot read turns an ordinary save into an opaque 422.
Two readings have to exist for each key:

- a label in both locale catalogues (`setup.missing.<key>`), read by PUBLISH's
  checklist and by the save bar's refusal statement;
- an entry in `MISSING_TAB` (`frontend/src/setup/shared.tsx`), which is what
  makes the item traceable to a tab that can resolve it.

Both drifted before this test existed: the key renamed `city` was still read
as `location`, and `payment_feed`, `external_registration_url` and
`team_bounds` had no tab at all.
"""

import json
import re
from pathlib import Path

import pytest

from app import setup

FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
SHARED_PATH = FRONTEND / "setup" / "shared.tsx"
LOCALE_PATHS = sorted((FRONTEND / "i18n").glob("*.json"))

# Every stable item key the module can append to the checklist, read off its
# own constants rather than restated here.
EMITTED_KEYS = sorted(
    value
    for name, value in vars(setup).items()
    if name.startswith("MISSING_") and isinstance(value, str)
)


def missing_tab_keys() -> set[str]:
    """The keys of the `MISSING_TAB` object literal. A regex rather than a
    parser: the literal is a flat `key: "tab",` block, and a shape this test
    could not read would be a shape the reviewer could not read either."""
    source = SHARED_PATH.read_text(encoding="utf-8")
    body = re.search(
        r"export const MISSING_TAB: Record<string, SetupTab> = \{(.*?)\n\};", source, re.S
    )
    assert body is not None, "MISSING_TAB is not where this test looks for it"
    return set(re.findall(r"^\s*(\w+):\s*\"", body.group(1), re.M))


def test_every_emitted_key_is_declared() -> None:
    assert EMITTED_KEYS, "no MISSING_* constants found — did they move?"


@pytest.mark.parametrize("key", EMITTED_KEYS)
@pytest.mark.parametrize("locale", LOCALE_PATHS, ids=lambda path: path.stem)
def test_every_emitted_key_has_a_label(key: str, locale: Path) -> None:
    catalogue = json.loads(locale.read_text(encoding="utf-8"))
    labels = catalogue["setup"]["missing"]
    assert key in labels, f"{locale.stem}.json has no setup.missing.{key}"
    assert labels[key].strip(), f"{locale.stem}.json leaves setup.missing.{key} empty"


@pytest.mark.parametrize("key", EMITTED_KEYS)
def test_every_emitted_key_names_a_tab(key: str) -> None:
    assert key in missing_tab_keys(), f"MISSING_TAB has no entry for {key}"


def test_no_tab_entry_outlives_its_key() -> None:
    assert missing_tab_keys() <= set(EMITTED_KEYS), "MISSING_TAB reads a key nothing emits"
