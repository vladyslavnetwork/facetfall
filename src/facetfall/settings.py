"""Збереження налаштувань і рекорду у JSON-файлі."""

import json
import os
from pathlib import Path


def _data_dir():
    # У snap-пакеті SNAP_USER_COMMON не змінюється між оновленнями,
    # тому рекорд не губиться після оновлення гри.
    if os.environ.get("SNAP_USER_COMMON"):
        return Path(os.environ["SNAP_USER_COMMON"])
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "facetfall"


class Settings:
    DEFAULTS = {"language": None, "sound": True, "fullscreen": False, "high_score": 0, "checkpoint": 1}

    def __init__(self, path=None):
        self.path = Path(path) if path else _data_dir() / "settings.json"
        self.data = dict(self.DEFAULTS)
        try:
            with open(self.path, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data.update({k: loaded[k] for k in self.DEFAULTS if k in loaded})
        except (OSError, ValueError):
            pass

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            pass  # гра має працювати навіть без права запису
