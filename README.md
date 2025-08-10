# film-contact-sheet

A tiny CLI utility to build **contact sheets (PDF)** from images in a folder.

- Multi-page PDF (auto pagination)
- Uniform thumbnail orientation inside the PDF (`--uniform-orient`), source files are never modified
- A4 page orientation (`--page-orient`)
- Automatic or explicit grid (`--rows` / `--cols`)
- Margins & gaps in millimeters
- Optional captions (`--labels`)
- **Film-like ordering** (`--order film-bottom-up`): fill columns **bottom→top** (neighbors along the short side), like 35mm strips

## Install

Python 3.8+ recommended.

```bash
python -m pip install -r requirements.txt
```

## Usage

Basic (auto everything, outputs `contact_sheet.pdf` in the current folder):

```bash
python film_contact_sheet.py /path/to/images
```

A few practical examples:

```bash
# All thumbnails forced to portrait inside the PDF, A4 portrait (defaults)
python film_contact_sheet.py /path/to/images

# Film-like order (bottom→top columns), captions with file names, 3 mm gaps
python film_contact_sheet.py /path/to/images --order film-bottom-up --labels name --gap-mm 3

# Explicit 8x6 grid, landscape page, uniform landscape thumbnails
python film_contact_sheet.py /path/to/images --rows 8 --cols 6 --page-orient landscape --uniform-orient landscape
```

### Options (most common)

- `--page-orient portrait|landscape` – A4 page orientation (default: `portrait`).
- `--uniform-orient none|portrait|landscape` – force a single orientation for thumbnails inside the PDF (default: `portrait`).
- `--rows INT` / `--cols INT` – explicit grid; if unspecified, the script picks a grid automatically.
- `--margin-mm FLOAT` – page margin in mm (default: `10`).
- `--gap-mm FLOAT` – gap between cells in mm (default: `2`).
- `--labels none|index|name` – captions under thumbnails (default: `none`).
- `--order row-left-right|film-bottom-up` – grid fill order (default: `film-bottom-up`).

## Notes

- EXIF orientation is respected.
- Images are scaled to fit cells while keeping aspect ratio.
- Color management is not the goal here; thumbnails are rendered as RGB for PDF.
- If you have many images, the tool creates additional pages automatically.

## License

MIT. See `LICENSE` for details.

## Support & contributions

This is a small personal utility shared **as is**. I don’t plan to provide support or accept feature requests.  
If you need changes, please **fork** and modify your copy.
