"""Переклади гри через стандартний gettext.

Вихідні переклади лежать у po/<мова>.po, а скомпільовані .mo-файли —
у src/navala/locale/<мова>/LC_MESSAGES/navala.mo
(їх створює tools/compile_translations.sh).
"""

import gettext
import os
from pathlib import Path

DOMAIN = "facetfall"
LOCALE_DIR = Path(__file__).resolve().parent / "locale"

# Код мови -> назва мови, написана цією ж мовою.
LANGUAGES = [
    ("en", "English"),
    ("uk", "Українська"),
    ("pl", "Polski"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("es", "Español"),
]
CODES = [code for code, _name in LANGUAGES]

_translation = gettext.NullTranslations()
_current = "en"


def detect_system_language():
    """Мова системи з LANGUAGE / LC_ALL / LC_MESSAGES / LANG, інакше англійська."""
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        for part in value.split(":"):
            code = part.split(".")[0].split("@")[0].split("_")[0].lower()
            if code in CODES:
                return code
    return "en"


def set_language(code):
    global _translation, _current
    if code not in CODES:
        code = "en"
    _current = code
    _translation = gettext.translation(
        DOMAIN, localedir=LOCALE_DIR, languages=[code], fallback=True
    )


def current_language():
    return _current


def language_name(code):
    return dict(LANGUAGES).get(code, code)


def _(message):
    return _translation.gettext(message)
