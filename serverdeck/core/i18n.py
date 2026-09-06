import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


def find_locales_dir() -> str:
    pkg_locales = Path(__file__).resolve().parent.parent / "locales"
    if pkg_locales.exists():
        return str(pkg_locales)
    if Path("./locales").exists():
        return str(Path("./locales").resolve())
    user_locales = Path.home() / ".config" / "serverdeck" / "locales"
    if user_locales.exists():
        return str(user_locales)
    return str(pkg_locales)


class I18nEngine:
    def __init__(self, locales_dir: Optional[str] = None, default_lang: str = "en"):
        self.locales_dir = locales_dir or find_locales_dir()
        self.default_lang = default_lang
        self.current_lang = default_lang
        self.translations: Dict[str, Dict[str, Any]] = {}
        self._lookup_cache: Dict[Tuple[str, str], Any] = {}
        self.load_translations()

    def load_translations(self) -> None:
        self._lookup_cache.clear()
        if not os.path.exists(self.locales_dir):
            return

        for filename in sorted(os.listdir(self.locales_dir)):
            filepath = os.path.join(self.locales_dir, filename)
            lang = filename.rsplit(".", 1)[0]

            if filename.endswith((".yaml", ".yml")):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self.translations[lang] = yaml.safe_load(f) or {}
                except Exception:
                    self.translations[lang] = {}
            elif filename.endswith(".json") and lang not in self.translations:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self.translations[lang] = json.load(f) or {}
                except Exception:
                    self.translations[lang] = {}

    def get_available_languages(self) -> List[str]:
        return list(self.translations.keys()) if self.translations else ["en", "pl"]

    def set_language(self, lang: str) -> bool:
        if lang in self.translations:
            self.current_lang = lang
            self._lookup_cache.clear()
            return True
        return False

    def toggle_language(self) -> str:
        langs = self.get_available_languages()
        if not langs:
            return self.current_lang
        curr_idx = langs.index(self.current_lang) if self.current_lang in langs else 0
        next_lang = langs[(curr_idx + 1) % len(langs)]
        self.current_lang = next_lang
        self._lookup_cache.clear()
        return next_lang

    def t(self, keypath: str, default: Optional[str] = None, **kwargs: Any) -> str:
        cache_key = (self.current_lang, keypath)
        val = self._lookup_cache.get(cache_key)

        if val is None:
            keys = keypath.split(".")
            val = self._resolve(self.translations.get(self.current_lang, {}), keys)
            if (val is None or val == "") and self.current_lang != self.default_lang:
                fallback_val = self._resolve(self.translations.get(self.default_lang, {}), keys)
                if fallback_val is not None and fallback_val != "":
                    val = fallback_val
            if val is not None:
                self._lookup_cache[cache_key] = val

        if val is None:
            return default if default is not None else keypath

        if kwargs:
            try:
                return str(val).format(**kwargs)
            except Exception:
                return str(val)
        return str(val)

    def _resolve(self, data: Dict[str, Any], keys: list) -> Any:
        curr = data
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return None
        return curr


i18n = I18nEngine()
