# i18n loader using resources/locales/*.json with preset helpers.
from typing import Dict, List
import json
import importlib.resources as pkgres

_CACHE: Dict[str, Dict[str, str]] = {}

def load_locale(lang: str) -> Dict[str, str]:
    if lang in _CACHE:
        return _CACHE[lang]
    try:
        pkg = "resources.locales"
        with pkgres.files(pkg).joinpath(f"{lang}.json").open("r", encoding="utf-8") as f:
            data = json.load(f)
        _CACHE[lang] = data
        return data
    except Exception:
        if lang != "en":
            return load_locale("en")
        return {}

class Translator:
    def __init__(self, lang: str):
        self.lang = lang
        self.table = load_locale(lang)

    def tr(self, key: str, default: str = "") -> str:
        return self.table.get(key, default or key)

    def preset_display_list(self) -> List[str]:
        return [self.tr("preset.slow","Slow"),
                self.tr("preset.normal","Normal"),
                self.tr("preset.fast","Fast"),
                self.tr("preset.veryfast","Very fast")]

    def preset_display_to_key(self, display: str) -> str:
        mapping = {
            self.tr("preset.slow","Slow"): "Slow",
            self.tr("preset.normal","Normal"): "Normal",
            self.tr("preset.fast","Fast"): "Fast",
            self.tr("preset.veryfast","Very fast"): "VeryFast",
        }
        return mapping.get(display, "Normal")

    def preset_key_to_display(self, key: str) -> str:
        mapping = {
            "Slow": self.tr("preset.slow","Slow"),
            "Normal": self.tr("preset.normal","Normal"),
            "Fast": self.tr("preset.fast","Fast"),
            "VeryFast": self.tr("preset.veryfast","Very fast"),
        }
        return mapping.get(key, self.tr("preset.normal","Normal"))
