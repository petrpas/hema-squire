"""Locale catalog for backend-generated text (emails, documents).

Locales are JSON files in ``app/locales/``; dropping in a new ``<code>.json``
adds a language without code changes. Missing keys fall back to the default
locale (Czech); a key missing there too is returned verbatim.
"""

import json
from pathlib import Path

DEFAULT_LOCALE = "cs"
LOCALES_DIR = Path(__file__).parent / "locales"


def _flatten(tree: dict, prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in tree.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = str(value)
    return flat


class Catalog:
    def __init__(self, directory: Path = LOCALES_DIR, default: str = DEFAULT_LOCALE):
        self.default = default
        self._messages: dict[str, dict[str, str]] = {}
        for path in sorted(directory.glob("*.json")):
            self._messages[path.stem] = _flatten(json.loads(path.read_text()))

    def available(self) -> list[str]:
        return sorted(self._messages)

    def translate(self, key: str, locale: str | None = None, **params: object) -> str:
        for candidate in (locale, self.default):
            if candidate is None:
                continue
            message = self._messages.get(candidate, {}).get(key)
            if message is not None:
                return message.format(**params) if params else message
        return key


catalog = Catalog()
t = catalog.translate
