"""
Prepare a portrait photo for clean ASCII conversion:
  1. remove the background (rembg) so the subject is isolated
  2. boost LOCAL contrast (CLAHE) so a flatly-lit face gains highlights and
     shadows -- this is what turns a dark blob into a recognizable face
  3. composite the subject onto pure white so the background reads as blank
     (white -> spaces in the ascii ramp)

Output: source-prepped.png (grayscale) and source-prepped-color.png (RGB),
consumed by make_ascii_svg.py.
Run once whenever the source photo changes; the ascii SVG itself is static.

    python scripts/prep_photo.py <input.jpg> [output.png]
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import remove

HERE = os.path.dirname(os.path.abspath(__file__))
INP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.jpg")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-prepped.png")

# 1. cut out the subject
cut = remove(Image.open(INP).convert("RGBA"))
rgb = np.array(cut.convert("RGB"))
alpha = np.array(cut.split()[-1])                 # 0 = background

# 2. local-contrast the luminance (CLAHE)
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.6, tileGridSize=(8, 8))
gray = clahe.apply(gray)

# a touch of global lift so the face sits in the sparse end of the ramp
gray = cv2.convertScaleAbs(gray, alpha=1.05, beta=18)

# 3. paste onto white using the alpha mask (feathered a hair to avoid a halo)
mask = (alpha.astype(np.float32) / 255.0)
mask = cv2.GaussianBlur(mask, (0, 0), 1.0)
out = gray.astype(np.float32) * mask + 255.0 * (1.0 - mask)
out = np.clip(out, 0, 255).astype(np.uint8)

Image.fromarray(out, mode="L").save(OUT)
print("wrote", OUT, out.shape)

# 4. also save a full-color version (subject on white, RGB) for colored ASCII
rgb_boosted = cv2.convertScaleAbs(rgb, alpha=1.05, beta=8)
out_col_r = rgb_boosted[:, :, 0].astype(np.float32) * mask + 255.0 * (1.0 - mask)
out_col_g = rgb_boosted[:, :, 1].astype(np.float32) * mask + 255.0 * (1.0 - mask)
out_col_b = rgb_boosted[:, :, 2].astype(np.float32) * mask + 255.0 * (1.0 - mask)
out_col = np.stack(
    [np.clip(out_col_r, 0, 255).astype(np.uint8),
     np.clip(out_col_g, 0, 255).astype(np.uint8),
     np.clip(out_col_b, 0, 255).astype(np.uint8)], axis=2
)
col_out = OUT.replace(".png", "-color.png").replace("-prepped-color-color", "-prepped-color")
if col_out == OUT:
    col_out = OUT.replace("source-prepped", "source-prepped-color")
Image.fromarray(out_col, mode="RGB").save(col_out)
print("wrote", col_out, out_col.shape)
