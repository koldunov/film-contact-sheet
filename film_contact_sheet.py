#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
film_contact_sheet_v2.py
------------------------
Create contact sheets (PDF) from images in a directory.

Highlights:
- Multi-page PDF when more images than fit on a single page.
- Uniform thumbnail orientation inside the PDF only (--uniform-orient); source files are not modified.
- Page orientation selector for A4 (--page-orient).
- Explicit grid parameters (--rows/--cols) or automatic grid selection.
- Margins and gaps in millimeters.
- Optional captions under thumbnails (--labels).
- Film-like ordering option (--order) to fill columns bottom->top like 35mm strips.

Dependencies: Pillow, reportlab
"""

import argparse
import math
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape as rl_landscape, portrait as rl_portrait
from reportlab.lib.units import mm


# ----------------------------- Utilities -----------------------------

IMG_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


def find_images(input_dir: Path) -> List[Path]:
    """Return a sorted list of image files in the given directory."""
    files: List[Path] = []
    for ext in IMG_EXTS:
        files.extend(sorted(input_dir.glob(f"*{ext}")))
        files.extend(sorted(input_dir.glob(f"*{ext.upper()}")))
    # De-duplicate while preserving order
    seen = set()
    out: List[Path] = []
    for p in files:
        if p.exists() and p.suffix.lower() in IMG_EXTS and p not in seen:
            out.append(p)
            seen.add(p)
    return out


def normalize_exif(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation if present (no-op on failure)."""
    try:
        return ImageOps.exif_transpose(img)
    except Exception:
        return img


def unify_orientation(img: Image.Image, mode: str) -> Image.Image:
    """
    Return a new Image with the requested orientation applied.
    mode: 'none' | 'portrait' | 'landscape'
    Source files on disk are never modified.
    """
    if mode == "none":
        return img

    w, h = img.size
    is_portrait = h >= w
    if mode == "portrait" and not is_portrait:
        return img.rotate(90, expand=True)
    if mode == "landscape" and is_portrait:
        return img.rotate(-90, expand=True)
    return img


def choose_grid_auto(n: int, page_w_pt: float, page_h_pt: float,
                     margin_pt: float, gap_pt: float) -> Tuple[int, int]:
    """
    Simple automatic grid selection: brute-force plausible (rows, cols) and
    pick the one maximizing cell area within the usable page rectangle.
    Returns (rows, cols).
    """
    usable_w = page_w_pt - 2 * margin_pt
    usable_h = page_h_pt - 2 * margin_pt

    best = (1, n)  # fallback
    best_area = -1.0

    # Reasonable search bounds
    for rows in range(1, min(15, n) + 1):
        cols = math.ceil(n / rows)
        if cols > 30:  # hard cap
            continue

        # Cell size given rows/cols and gaps
        cell_w = (usable_w - gap_pt * (cols - 1)) / cols
        cell_h = (usable_h - gap_pt * (rows - 1)) / rows
        if cell_w <= 0 or cell_h <= 0:
            continue
        area = cell_w * cell_h
        if area > best_area:
            best_area = area
            best = (rows, cols)

    return best


def paginate(n: int, per_page: int) -> List[Tuple[int, int]]:
    """
    Return a list of (start, end) index pairs for each page.
    'end' is exclusive.
    """
    pages: List[Tuple[int, int]] = []
    for i in range(0, n, per_page):
        pages.append((i, min(i + per_page, n)))
    return pages


def index_to_cell(idx: int, rows: int, cols: int, order: str):
    """
    Map linear index -> grid coordinates (row, col) according to the chosen order.

    Orders:
      - "row-left-right": fill left→right, top→bottom (classic reading order).
      - "film-bottom-up": fill columns bottom→top, then next column to the right
        (mimics 35mm strips where neighbor frames are along the short side).

    Returns (r, c) with r=0 at the top row, c=0 at the leftmost column.
    """
    if order == "row-left-right":
        r = idx // cols
        c = idx % cols
        return r, c
    elif order == "film-bottom-up":
        c = idx // rows
        row_from_bottom = idx % rows
        r = (rows - 1) - row_from_bottom
        return r, c
    else:
        r = idx // cols
        c = idx % cols
        return r, c


def draw_page(
    c: canvas.Canvas,
    images: List[Path],
    rows: int,
    cols: int,
    margin_pt: float,
    gap_pt: float,
    page_w_pt: float,
    page_h_pt: float,
    uniform_orient: str,
    labels: str,
    order: str,
    font_name: str = "Helvetica",
    font_size: int = 7,
) -> None:
    """Render a single grid page onto the canvas."""
    usable_w = page_w_pt - 2 * margin_pt
    usable_h = page_h_pt - 2 * margin_pt

    cell_w = (usable_w - gap_pt * (cols - 1)) / cols
    cell_h = (usable_h - gap_pt * (rows - 1)) / rows

    # Start (top-left cell baseline)
    x0 = margin_pt
    y0 = page_h_pt - margin_pt - cell_h  # top row

    c.setFont(font_name, font_size)

    for idx, img_path in enumerate(images):
        # Compute row/col based on ordering
        r, cidx = index_to_cell(idx, rows, cols, order)

        x = x0 + cidx * (cell_w + gap_pt)
        y = y0 - r * (cell_h + gap_pt)

        # Load and prepare image
        with Image.open(img_path) as im:
            im = normalize_exif(im)
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            im = unify_orientation(im, uniform_orient)

            # Scale to fit cell while preserving aspect
            iw, ih = im.size
            scale = min(cell_w / iw, cell_h / ih)
            new_w = max(1, int(iw * scale))
            new_h = max(1, int(ih * scale))

            im = im.copy()
            im.thumbnail((new_w, new_h), Image.LANCZOS)

            # Center inside the cell
            offset_x = x + (cell_w - im.width) / 2
            offset_y = y + (cell_h - im.height) / 2

            # Draw image
            c.drawInlineImage(im, offset_x, offset_y, width=im.width, height=im.height)

        # Optional caption
        if labels != "none":
            text = ""
            if labels == "index":
                text = f"{img_path.stem}"
            elif labels == "name":
                text = img_path.name

            if text:
                ty = y - 2  # tiny offset below the cell
                c.drawString(x, ty, text)


# ----------------------------- CLI & main -----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Create contact sheets (PDF) from images in a folder."
    )
    p.add_argument("input_dir", type=Path, help="Folder with source images")
    p.add_argument("-o", "--output", type=Path, default=Path("contact_sheet.pdf"),
                   help="Output PDF path")

    p.add_argument("--page-orient", choices=["portrait", "landscape"], default="portrait",
                   help="A4 page orientation")
    p.add_argument("--uniform-orient", choices=["none", "portrait", "landscape"],
                   default="portrait",
                   help="Force a uniform orientation for thumbnails inside the PDF only")

    p.add_argument("--rows", type=int, default=None, help="Number of rows per page")
    p.add_argument("--cols", type=int, default=None, help="Number of columns per page")

    p.add_argument("--margin-mm", type=float, default=10.0, help="Page margin (mm)")
    p.add_argument("--gap-mm", type=float, default=2.0, help="Gap between cells (mm)")

    p.add_argument("--labels", choices=["none", "index", "name"], default="none",
                   help="Captions under thumbnails: none | index (stem) | name (filename)")

    p.add_argument("--order", choices=["row-left-right", "film-bottom-up"], default="film-bottom-up",
                   help="Grid fill order: 'row-left-right' (reading order) or "
                        "'film-bottom-up' (columns bottom→top, then next column)")

    return p.parse_args()


def main():
    args = parse_args()

    if not args.input_dir.exists() or not args.input_dir.is_dir():
        raise SystemExit(f"Input folder not found: {args.input_dir}")

    images = find_images(args.input_dir)
    if not images:
        raise SystemExit("No supported images found in the folder.")

    # Page size
    if args.page_orient == "landscape":
        page_w_pt, page_h_pt = rl_landscape(A4)
    else:
        page_w_pt, page_h_pt = rl_portrait(A4)

    margin_pt = args.margin_mm * mm
    gap_pt = args.gap_mm * mm

    # Grid
    if args.rows and args.cols:
        rows, cols = args.rows, args.cols
    elif args.rows and not args.cols:
        cols = math.ceil(len(images) / args.rows)
        rows = args.rows
    elif args.cols and not args.rows:
        rows = math.ceil(len(images) / args.cols)
        cols = args.cols
    else:
        rows, cols = choose_grid_auto(len(images), page_w_pt, page_h_pt, margin_pt, gap_pt)

    per_page = rows * cols
    pages = paginate(len(images), per_page)

    c = canvas.Canvas(str(args.output), pagesize=(page_w_pt, page_h_pt))

    for (start, end) in pages:
        page_imgs = images[start:end]
        draw_page(
            c=c,
            images=page_imgs,
            rows=rows,
            cols=cols,
            margin_pt=margin_pt,
            gap_pt=gap_pt,
            page_w_pt=page_w_pt,
            page_h_pt=page_h_pt,
            uniform_orient=args.uniform_orient,
            labels=args.labels,
            order=args.order,
        )
        c.showPage()

    c.save()

    print(f"✓ Done: {args.output} ({len(images)} images, {len(pages)} pages, grid {rows}x{cols})")
    print(f"   Page orientation: {args.page_orient}. Uniform thumbnails: {args.uniform_orient}.")
    print(f"   Margins: {args.margin_mm} mm, gaps: {args.gap_mm} mm. Labels: {args.labels}.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
