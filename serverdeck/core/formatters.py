import re

ANSI_RE = re.compile(r'\033\[[0-9;]*[a-zA-Z]')

def visible_len(text: str) -> int:
    return len(ANSI_RE.sub('', text))

def truncate_visible(text: str, max_len: int) -> str:
    if visible_len(text) <= max_len:
        return text
    curr_len = 0
    res = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == '\033':
            m = ANSI_RE.match(text, i)
            if m:
                res.append(m.group(0))
                i = m.end()
                continue
        if curr_len < max_len:
            res.append(text[i])
            curr_len += 1
            i += 1
        else:
            break
    res.append('\033[0m')
    return "".join(res)

def pad_visible(text: str, length: int) -> str:
    vlen = visible_len(text)
    if vlen >= length:
        return truncate_visible(text, length)
    return text + (" " * (length - vlen))

def format_bytes(num_bytes: float) -> str:
    val = float(num_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if abs(val) < 1024.0:
            return f"{val:5.1f} {unit}"
        val /= 1024.0
    return f"{val:5.1f} EB"

def format_uptime(seconds: float) -> str:
    s = int(seconds)
    days, s = divmod(s, 86400)
    hours, s = divmod(s, 3600)
    minutes, s = divmod(s, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    parts.append(f"{s}s")
    return " ".join(parts)

