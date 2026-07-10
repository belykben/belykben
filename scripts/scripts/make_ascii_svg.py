"""
Convert a portrait photo into a COLORED ASCII-art SVG — each character is filled
with the actual pixel color sampled from the source image, on a near-black
background — inspired by the attached reference image style.

GitHub renders SVGs embedded via <img> and runs their SMIL animations there.
Each row is revealed with a left-to-right clip wipe staggered top -> bottom.
"""
from PIL import Image, ImageEnhance, ImageFilter
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# defaults to the prepped grayscale image (see prep_photo.py)
SRC  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-prepped.png")
OUT  = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "avi-ascii.svg")

# Color source: prefer source-prepped-color.png (RGB, bg removed) alongside the gray file
_color_candidate = SRC.replace("source-prepped.png", "source-prepped-color.png")
SRC_COLOR = _color_candidate if os.path.exists(_color_candidate) else SRC

COLS = 100
ROWS = 53
CELL_W = 8
CELL_H = 15
RAMP = " .`:-=+*cs#%@"   # bright(sparse) -> dark(dense)

# Tuning
CONTRAST   = 1.4
BRIGHTNESS = 1.0
GAMMA      = 1.35
SHARPEN    = True
WHITE_FLOOR = 0.78   # luminance above this -> space (blank background)

# Color: boost saturation on the color sample so chars pop
SAT_BOOST  = 1.8    # 1.0 = natural, >1 = more vibrant
DIM_FACTOR = 0.88   # slight dim so bright face isn't blown out

PAD         = 20
TITLEBAR_H  = 30
STATUS_H    = 30
ART_W       = COLS * CELL_W
ART_H       = ROWS * CELL_H
CANVAS_W    = ART_W + PAD * 2
CANVAS_H    = TITLEBAR_H + ART_H + STATUS_H + PAD

BG       = "#0d1117"
BG2      = "#0f1419"
FRAME    = "#30363d"
TITLE_TEXT = "#7d8590"
INK      = "#c9d1d9"
CURSOR   = "#ffffff"

ROW_DUR  = 0.11
STAGGER  = 0.11

STATIC = bool(os.environ.get("STATIC"))

# ── 1. load grayscale for character density mapping ───────────────────────────
im_gray = Image.open(SRC).convert("L")
if SHARPEN:
    im_gray = im_gray.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=2))
im_gray = ImageEnhance.Brightness(im_gray).enhance(BRIGHTNESS)
im_gray = ImageEnhance.Contrast(im_gray).enhance(CONTRAST)
im_gray = im_gray.resize((COLS, ROWS), Image.LANCZOS)
px_gray = im_gray.load()

# ── 2. load color image for per-character fill color ─────────────────────────
im_col = Image.open(SRC_COLOR).convert("RGB")
im_col = ImageEnhance.Color(im_col).enhance(SAT_BOOST)       # boost saturation
im_col = im_col.resize((COLS, ROWS), Image.LANCZOS)
px_col = im_col.load()

# ── 3. build per-row list of (char, r, g, b) tuples ──────────────────────────
rows_data = []
for y in range(ROWS):
    row = []
    for x in range(COLS):
        lum = px_gray[x, y] / 255.0
        lum = pow(lum, GAMMA)
        if lum >= WHITE_FLOOR:
            row.append((" ", 13, 17, 23))   # background colour
            continue
        idx = int((1.0 - lum) * (len(RAMP) - 1) + 0.5)
        idx = max(0, min(len(RAMP) - 1, idx))
        r, g, b = px_col[x, y]
        # dim slightly
        r = int(r * DIM_FACTOR)
        g = int(g * DIM_FACTOR)
        b = int(b * DIM_FACTOR)
        row.append((RAMP[idx], r, g, b))
    rows_data.append(row)

art_top = TITLEBAR_H + PAD * 0.35

# ── 4. build per-row SVG text with colored tspans ────────────────────────────
def row_to_svg_text(row_chars, x, y, font_size, art_w):
    """
    Collapse runs of same-color chars into single <tspan> elements.
    Returns an SVG <text> string with per-tspan fill colors.
    """
    # group consecutive chars with the same color
    runs = []
    cur_c, cur_r, cur_g, cur_b = row_chars[0]
    buf = cur_c
    for (c, r, g, b) in row_chars[1:]:
        if (r, g, b) == (cur_r, cur_g, cur_b):
            buf += c
        else:
            runs.append((buf, cur_r, cur_g, cur_b))
            buf, cur_r, cur_g, cur_b = c, r, g, b
    runs.append((buf, cur_r, cur_g, cur_b))

    inner = ""
    for (text, r, g, b) in runs:
        fill = f"#{r:02x}{g:02x}{b:02x}"
        inner += f'<tspan fill="{fill}">{html.escape(text)}</tspan>'

    return (
        f'<text xml:space="preserve" x="{x}" y="{y:.1f}" '
        f'font-size="{font_size:.1f}" textLength="{art_w}" lengthAdjust="spacing">'
        f'{inner}</text>'
    )

# ── 5. assemble SVG ───────────────────────────────────────────────────────────
parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, '
    f'Menlo, Consolas, monospace">'
)
parts.append(
    '<defs>'
    f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
    f'</linearGradient></defs>'
)

parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>')
parts.append(
    f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" '
    f'fill="none" stroke="{FRAME}" stroke-width="1"/>'
)
parts.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>')
for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
parts.append(
    f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
    f'text-anchor="middle">ben@github: ~$ ./portrait.sh</text>'
)

font_size = CELL_H * 0.86
for ry, row_chars in enumerate(rows_data):
    y     = art_top + ry * CELL_H + CELL_H * 0.74
    row_y = art_top + ry * CELL_H
    delay = ry * STAGGER
    text  = row_to_svg_text(row_chars, PAD, y, font_size, ART_W)

    if STATIC:
        parts.append(text)
        continue

    parts.append(
        f'<clipPath id="r{ry}"><rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}" width="0">'
        f'<animate attributeName="width" from="0" to="{ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/></rect></clipPath>'
    )
    parts.append(f'<g clip-path="url(#r{ry})">{text}</g>')
    parts.append(
        f'<rect y="{row_y+1:.1f}" width="{CELL_W}" height="{CELL_H-2}" fill="{CURSOR}" opacity="0">'
        f'<animate attributeName="x" from="{PAD}" to="{PAD+ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/>'
        f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
        f'<set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/></rect>'
    )

# status bar
status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
status_y      = status_line_y + 19
parts.append(
    f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" '
    f'y2="{status_line_y:.1f}" stroke="{FRAME}"/>'
)
parts.append(
    f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13">'
    f'ben@github:~$ whoami <tspan fill="{INK}">Benedict Thomas M</tspan></text>'
)
parts.append(
    f'<rect x="{PAD+210}" y="{status_y-12:.1f}" width="8" height="14" fill="{INK}">'
    f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
    f'dur="1s" repeatCount="indefinite"/></rect>'
)

parts.append("</svg>")
svg = "".join(parts)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print("wrote", OUT, len(svg), "bytes;", CANVAS_W, "x", CANVAS_H)
