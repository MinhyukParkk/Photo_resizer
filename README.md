# Photo_resizer

Bulk-resize photos so every output JPEG is **1 MB or smaller**, without touching the originals.

Useful when email attachments, upload forms, or document files have a size limit and you have a folder full of full-resolution phone photos.

## What it does

- Walks through a folder **and all of its subfolders**
- Processes `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.heif`
- Applies EXIF orientation, so iPhone photos are not rotated sideways
- Flattens transparency onto a white background before saving as JPEG
- Finds the highest JPEG quality that still fits under 1 MB; if quality alone is not enough, it scales the image down step by step
- Writes a new file next to the original and **never overwrites or deletes anything**

```
IMG_1234.HEIC  ->  IMG_1234_resized.jpeg
beach.jpg      ->  beach_resized.jpeg
```

Files that already end in `_resized` are skipped, so it is safe to run twice.

## Requirements

- Python 3.9 or newer
- [Pillow](https://pypi.org/project/Pillow/)
- [pillow-heif](https://pypi.org/project/pillow-heif/) — only needed for iPhone HEIC/HEIF photos

```bash
pip install pillow pillow-heif
```

## Usage

Resize everything in the folder that contains the script:

```bash
python bulk_resize_photos.py
```

Resize everything in a specific folder:

```bash
python bulk_resize_photos.py "C:\Users\you\Pictures\Site Visit"
```

macOS / Linux:

```bash
python bulk_resize_photos.py ~/Pictures/site-visit
```

## Example output

```
Root folder: C:\Users\you\Pictures\Site Visit
Maximum output size: 1,000,000 bytes

Found 3 image(s).

[1/3] charles-river/IMG_1201.HEIC
    -> charles-river/IMG_1201_resized.jpeg | 964.2 KB | quality=82 | 3024x4032
[2/3] charles-river/IMG_1202.HEIC
    -> charles-river/IMG_1202_resized.jpeg | 912.7 KB | quality=79 | 3024x4032
[3/3] fens/panorama.png
    -> fens/panorama_resized.jpeg | 987.1 KB | quality=71 | 4593x1837

Done.
Created: 3
Errors:  0
```

## Settings

The limits live at the top of `bulk_resize_photos.py` if you need a different target:

| Constant | Default | Meaning |
| --- | --- | --- |
| `MAX_BYTES` | `1_000_000` | Maximum size of each output file, in bytes |
| `MIN_QUALITY` | `30` | Lowest JPEG quality the script will accept |
| `MAX_QUALITY` | `95` | Highest JPEG quality it will try |
| `SHRINK_FACTOR` | `0.90` | How much the image shrinks per pass when quality alone is not enough |
| `MIN_LONG_EDGE` | `800` | Point at which the script prefers lowering quality over shrinking further |

## Notes

- Output is always JPEG, so PNG transparency is lost by design.
- If you see a HEIC error, install `pillow-heif` and run the script again.