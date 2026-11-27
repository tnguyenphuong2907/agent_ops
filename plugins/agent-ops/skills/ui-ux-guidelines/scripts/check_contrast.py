#!/usr/bin/env python3
"""Check WCAG 2.2 contrast of color tokens in docs/03-design/design-system.md.

Token format (shadcn/ui style, inside ```css blocks):
    :root { --background: #ffffff; --primary: oklch(0.55 0.2 260); }
    .dark { --background: 222.2 84% 4.9%; }
Supported values: #rgb, #rrggbb, rgb(), hsl(), bare HSL triplet "H S% L%", oklch().
Pairs checked automatically: X / X-foreground, foreground / background,
muted-foreground / background, muted-foreground / muted (same theme).
Extra pairs (anywhere in the file):  contrast-pair: <fg> <bg> [text|large|ui]
Thresholds: text 4.5, large 3.0, ui 3.0.  Exit code 1 if any pair fails.

Usage: python3 check_contrast.py [path/to/design-system.md]
"""
import math
import re
import sys
from pathlib import Path

DEFAULT = Path("docs/03-design/design-system.md")
THRESHOLD = {"text": 4.5, "large": 3.0, "ui": 3.0}


def _hsl_to_rgb(h, s, l):
    s, l = s / 100, l / 100
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    seg = int(h // 60) % 6
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][seg]
    return r + m, g + m, b + m


def _oklch_to_rgb(L, C, H):
    if L > 1:  # percentage form
        L = L / 100
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    lin = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )
    return tuple(min(1.0, max(0.0, v)) for v in lin), True  # already linear


def parse_color(value):
    """Return (rgb tuple 0..1, is_linear) or None."""
    v = value.strip().rstrip(";").strip()
    nums = lambda t: [float(n) for n in re.findall(r"-?\d*\.?\d+", t)]
    if m := re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", v):
        h = m.group(1)
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)), False
    if v.startswith("rgb"):
        r, g, b = nums(v)[:3]
        return (r / 255, g / 255, b / 255), False
    if v.startswith("oklch"):
        n = nums(v)
        L = n[0] / 100 if "%" in v.split()[0] else n[0]
        return _oklch_to_rgb(L, n[1], n[2])
    if v.startswith("hsl") or re.fullmatch(r"-?\d*\.?\d+\s+\d*\.?\d+%\s+\d*\.?\d+%", v):
        h, s, l = nums(v)[:3]
        return _hsl_to_rgb(h, s, l), False
    return None


def luminance(color):
    rgb, linear = color
    if not linear:
        rgb = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(c1, c2):
    a, b = sorted((luminance(c1), luminance(c2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def load(path):
    themes = {"light": {}, "dark": {}}
    extra = []
    theme = "light"
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.search(r"\.dark\b|^#+.*(dark|tối)", line, re.I):
            theme = "dark"
        elif re.search(r":root\b|^#+.*(light|sáng)", line, re.I):
            theme = "light"
        if m := re.search(r"contrast-pair:\s*([\w-]+)\s+([\w-]+)(?:\s+(text|large|ui))?", line):
            extra.append((m.group(1), m.group(2), m.group(3) or "text"))
            continue
        for name, val in re.findall(r"--([\w-]+)\s*:\s*([^;]+);?", line):
            color = parse_color(val)
            if color:
                themes[theme][name] = color
    return themes, extra


def pairs_for(tokens, extra):
    out = []
    for name in tokens:
        if name.endswith("-foreground") and name[: -len("-foreground")] in tokens:
            out.append((name, name[: -len("-foreground")], "text"))
    for fg, bg in [("foreground", "background"), ("muted-foreground", "background"),
                   ("muted-foreground", "muted")]:
        if fg in tokens and bg in tokens and (fg, bg, "text") not in out:
            out.append((fg, bg, "text"))
    return out + [p for p in extra if p[0] in tokens and p[1] in tokens]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not path.exists():
        print(f"Not found: {path}")
        return 2
    themes, extra = load(path)
    failed = checked = 0
    for theme, tokens in themes.items():
        if not tokens:
            continue
        for fg, bg, kind in pairs_for(tokens, extra):
            r = ratio(tokens[fg], tokens[bg])
            ok = r >= THRESHOLD[kind]
            checked += 1
            failed += not ok
            print(f"{'PASS' if ok else 'FAIL'}  [{theme}] {fg} on {bg} ({kind}): {r:.2f} (min {THRESHOLD[kind]})")
    if not checked:
        print("No color pairs found. Use --token: value inside :root / .dark (see docstring).")
        return 2
    print(f"\n{checked} pairs checked, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
