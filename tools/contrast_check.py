"""
Contrast checker for key CSS variable color pairs in index.html

Usage:
  python tools/contrast_check.py

This script parses the :root CSS variables in `index.html` and computes WCAG contrast
ratios for a set of commonly-used foreground/background pairs.

It supports hex colors (#rgb, #rrggbb) and rgba(r,g,b,a) (alpha ignored).
"""
import re
import sys
from math import pow

HTML_PATH = 'index.html'

VAR_RE = re.compile(r"--([a-zA-Z0-9\-]+)\s*:\s*([^;]+);")
ROOT_RE = re.compile(r":root\s*{([\s\S]*?)}", re.MULTILINE)


def parse_color(s):
    s = s.strip()
    if s.startswith('#'):
        hexv = s[1:]
        if len(hexv) == 3:
            r = int(hexv[0]*2, 16)
            g = int(hexv[1]*2, 16)
            b = int(hexv[2]*2, 16)
        elif len(hexv) == 6:
            r = int(hexv[0:2], 16)
            g = int(hexv[2:4], 16)
            b = int(hexv[4:6], 16)
        else:
            raise ValueError('Unsupported hex: '+s)
        return (r, g, b)
    m = re.match(r"rgba?\s*\(([^)]+)\)", s)
    if m:
        parts = [p.strip() for p in m.group(1).split(',')]
        r = int(parts[0])
        g = int(parts[1])
        b = int(parts[2])
        return (r, g, b)
    raise ValueError('Unknown color format: '+s)


def srgb_to_lin(c):
    c = c / 255.0
    if c <= 0.03928:
        return c / 12.92
    return pow((c + 0.055) / 1.055, 2.4)


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)


def contrast_ratio(fg, bg):
    L1 = luminance(fg)
    L2 = luminance(bg)
    lighter = max(L1, L2)
    darker = min(L1, L2)
    return (lighter + 0.05) / (darker + 0.05)


def main():
    try:
        with open(HTML_PATH, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print('Error: index.html not found in the current directory.')
        sys.exit(1)

    root = ROOT_RE.search(html)
    if not root:
        print('Could not find :root block in index.html')
        sys.exit(1)
    root_text = root.group(1)
    vars = dict(VAR_RE.findall(root_text))
    # normalize
    vars = {k: v.strip() for k, v in vars.items()}

    def get_rgb(varname):
        if varname not in vars:
            raise KeyError(varname)
        return parse_color(vars[varname])

    pairs = [
        ('--text-dark', '--dark-bg'),
        ('--text-dark', '--card-bg'),
        ('--muted', '--dark-bg'),
        ('--primary', '--card-bg'),
        ('--primary', '--dark-bg'),
    ]

    print('Contrast report (WCAG ratios). Thresholds: AA normal text >=4.5, AA large text >=3.0')
    print('-' * 60)
    for fg_var, bg_var in pairs:
        try:
            fg = get_rgb(fg_var)
            bg = get_rgb(bg_var)
        except Exception as e:
            print(f'{fg_var} vs {bg_var}: Error reading vars: {e}')
            continue
        ratio = contrast_ratio(fg, bg)
        status = 'PASS' if ratio >= 4.5 else (
            'AA-large' if ratio >= 3.0 else 'FAIL')
        print(
            f'{fg_var} ({vars.get(fg_var)}) on {bg_var} ({vars.get(bg_var)}) -> ratio: {ratio:.2f} [{status}]')


if __name__ == '__main__':
    main()
