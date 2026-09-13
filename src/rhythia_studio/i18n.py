"""JSON catalogs, source-text fallback and explicit message parameters.

English source strings are stable message identifiers, as in gettext. Domain IDs
and project data are never translated. Each window owns its translator.
"""

import json
import re
from pathlib import Path
from string import Formatter

from .messages import Message, MessageError

CATALOGS = Path(__file__).parent / "locales"


def languages():
    result = {}
    for path in sorted(CATALOGS.glob("*.json")):
        catalog = json.loads(path.read_text(encoding="utf-8"))
        result[path.stem] = catalog["name"]
    return result


class Translator:
    def __init__(self, language="en", directory=CATALOGS):
        self.directory = Path(directory)
        self.set_language(language)

    def set_language(self, language):
        path = self.directory / f"{language}.json"
        if not re.fullmatch(r"[a-z]{2}(?:_[A-Z]{2})?", language) or not path.is_file():
            language = "en"
            path = self.directory / "en.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.language = language
        self.locale = data.get("locale", language)
        self.messages = data["messages"]
        for source, target in self.messages.items():
            source_fields = {field for _, field, _, _ in Formatter().parse(source) if field}
            target_fields = {field for _, field, _, _ in Formatter().parse(target) if field}
            if source_fields != target_fields:
                raise ValueError(f"Mismatched translation placeholders: {language}: {source}")

    def text(self, message, **values):
        source = message
        if isinstance(source, MessageError):
            source = source.message
        if isinstance(source, Message):
            values = source.values | values
            source = source.source
        source = str(source)
        target = self.messages.get(source, source)
        values = {
            key: self.text(value) if isinstance(value, (Message, MessageError)) else value
            for key, value in values.items()
        }
        return target.format(**values) if values else target
