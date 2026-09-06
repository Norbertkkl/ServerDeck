from typing import Any, Dict, List, Optional
from serverdeck.core.i18n import i18n
from serverdeck.managers.firewall import get_ufw_status
from serverdeck.tui.theme import colorize
from serverdeck.tui.components import (
    get_term_layout, render_box_header, render_box_line, render_box_footer,
    pad_visible
)

def render_tab_8_ufw(
    theme: Dict[str, Any],
    selected_idx: int = 0,
    filter_str: str = "",
    snapshot_msg: Optional[str] = None,
    is_modal: bool = False,
    cached_rules: Optional[List[Dict[str, Any]]] = None,
    force_refresh: bool = False
) -> List[Dict[str, Any]]:
    c_border = theme.get("border", "#1e3a8a")
    c_title = theme.get("title", "#00f0ff")
    c_label = theme.get("label", "#94a3b8")
    c_val = theme.get("value", "#f0f9ff")
    c_hl = theme.get("highlight", "#38bdf8")

    w, h = get_term_layout()
    box_w = min(120, max(40, w - 2))
    inner_w = box_w - 4

    ufw_info = get_ufw_status(force=force_refresh)
    if cached_rules is not None and not force_refresh and not filter_str:
        rules = cached_rules
    else:
        all_rules = ufw_info.get("rules", [])
        if filter_str:
            f_lower = filter_str.lower()
            rules = [
                r for r in all_rules
                if f_lower in str(r.get("num", "")).lower()
                or f_lower in r.get("to", "").lower()
                or f_lower in r.get("action", "").lower()
                or f_lower in r.get("from", "").lower()
            ]
        else:
            rules = all_rules

    is_act = ufw_info.get("active", False)
    stat_badge = colorize("[ ACTIVE / ENABLED ]", theme.get("ok", "#00ff9d"), bold=True) if is_act else colorize("[ DISABLED / INACTIVE ]", theme.get("crit", "#f43f5e"), bold=True)
    inc_pol = colorize(ufw_info.get("default_incoming", "deny").upper(), theme.get("crit", "#f43f5e") if ufw_info.get("default_incoming", "deny") == "deny" else theme.get("ok", "#00ff9d"))
    out_pol = colorize(ufw_info.get("default_outgoing", "allow").upper(), theme.get("ok", "#00ff9d"))

    print(render_box_header("FIREWALL POLICY & UFW RULES MANAGER", box_w, theme))
    u_line = f"• {colorize('UFW Status:', c_label)} {stat_badge}  • {colorize('Incoming:', c_label)} [{inc_pol}]  • {colorize('Outgoing:', c_label)} [{out_pol}]"
    print(render_box_line(u_line, box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    tbl_hdr = f"  {'':<2} {'RULE #':<8} {'ACTION':<11} {'PORT / PROTOCOL':<20} {'SOURCE IP':<18} {'COMMENT'}"
    print(render_box_line(colorize(tbl_hdr, c_label, bold=True), box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    window_size = 2 if is_modal else 5
    start_idx = max(0, min(selected_idx - window_size // 2, max(0, len(rules) - window_size)))
    visible_rules = rules[start_idx:start_idx + window_size]

    extra_w = max(0, inner_w - 74)
    to_w = 18 + extra_w // 2
    from_w = 16 + (extra_w - extra_w // 2)

    for offset, r in enumerate(visible_rules):
        actual_idx = start_idx + offset
        is_selected = (actual_idx == selected_idx)
        pointer = "► " if is_selected else "  "

        r_num = colorize(f"#{r.get('num', actual_idx+1)}", c_hl if not is_selected else theme.get("ok", "#00ff9d"), bold=is_selected)
        act = r.get("action", "ALLOW")
        act_c = theme.get("ok", "#00ff9d") if "ALLOW" in act else (theme.get("crit", "#f43f5e") if "DENY" in act or "REJECT" in act else theme.get("warn", "#f59e0b"))
        act_badge = colorize(act[:10], act_c, bold=True)
        to_str = colorize(r.get("to", "Any")[:to_w], c_val)
        from_str = colorize(r.get("from", "Anywhere")[:from_w], c_label)
        comment_str = colorize(r.get("comment", "")[:12], c_hl)

        ptr_col = colorize(pointer, c_hl, bold=True)
        r_num_col = pad_visible(r_num, 8)
        row_txt = f"{ptr_col}{r_num_col} {pad_visible(act_badge, 11)} {pad_visible(to_str, to_w + 2)} {pad_visible(from_str, from_w + 2)} {comment_str}"
        print(render_box_line(row_txt, box_w, theme))

    if not rules:
        print(render_box_line(colorize("  No firewall rules configured or match filter.", c_label), box_w, theme))

    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))
    shortcuts = f"• [Rule {selected_idx + 1}/{len(rules)}] | [a] Add | [d] Del | [t] Toggle | [r] Reload | [/] Filter" if rules else "• Shortcuts: [a] Add Rule | [t] Toggle UFW | [r] Reload"
    print(render_box_line(shortcuts, box_w, theme))
    print(render_box_footer(box_w, theme))
    return rules

