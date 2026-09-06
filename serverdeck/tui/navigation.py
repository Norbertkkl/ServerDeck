from typing import Any, Dict
from serverdeck.core.i18n import i18n
from serverdeck.tui.theme import colorize

def render_tab_bar(active_tab: int, theme: Dict[str, Any]) -> str:
    row1 = [
        ("1", i18n.t("nav.tab_1", "Overview")),
        ("2", i18n.t("nav.tab_2", "Processes")),
        ("3", i18n.t("nav.tab_3", "Network")),
        ("4", i18n.t("nav.tab_4", "Sensors")),
        ("5", i18n.t("nav.tab_5", "Disks & SMART"))
    ]
    row2 = [
        ("6", i18n.t("nav.tab_6", "Memory")),
        ("7", i18n.t("nav.tab_7", "DB & Docker")),
        ("8", i18n.t("nav.tab_9", "Firewall")),
        ("9", i18n.t("nav.tab_0", "Software Hub"))
    ]

    c_active_bg = theme.get("tab_active_bg", "#0284c7")
    c_active_fg = theme.get("tab_active_fg", "#ffffff")
    c_inactive_fg = theme.get("tab_inactive_fg", "#64748b")
    c_hl = theme.get("highlight", "#38bdf8")

    def build_row(tabs):
        parts = []
        for key, name in tabs:
            tab_num = int(key)
            if tab_num == active_tab:
                label = f"[{key}] {name}"
                item = f"\033[48;2;2;132;199m\033[38;2;255;255;255m▌►{label}◄▐\033[0m"
                parts.append(item)
            else:
                key_fmt = colorize(f"[{key}]", c_hl)
                name_fmt = colorize(name, c_inactive_fg)
                parts.append(f"{key_fmt} {name_fmt}")
        return " ".join(parts)

    return build_row(row1) + "\n " + build_row(row2)

