#!/usr/bin/env python3
r"""
Bulk-resize photos recursively so each output JPEG is <= 1,000,000 bytes.

Usage:
    python bulk_resize_photos.py
or:
    python bulk_resize_photos.py "C:\path\to\root"

Behavior:
- Searches the root folder and all subfolders.
- Processes JPG, JPEG, PNG, WEBP, HEIC, and HEIF images.
- Leaves originals untouched.
- Writes the resized image next to the original:
      IMG_1234.HEIC -> IMG_1234_resized.jpeg
      beach.jpg     -> beach_resized.jpeg
- Skips files that already end in "_resized".
"""

import argparse
import io
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print("ERROR: Pillow is not installed. Run: pip install pillow")
    sys.exit(1)

# HEIC/HEIF support is optional.
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_ENABLED = True
except ImportError:
    HEIF_ENABLED = False

MAX_BYTES = 1_000_000          # Strictly <= 1 MB (decimal)
MIN_QUALITY = 30
MAX_QUALITY = 95
SHRINK_FACTOR = 0.90
MIN_LONG_EDGE = 800

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"
}


def prepare_image(img: Image.Image) -> Image.Image:
    """Apply iPhone/EXIF orientation and convert to JPEG-compatible RGB."""
    img = ImageOps.exif_transpose(img)

    # Flatten transparency onto a white background.
    if img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    ):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background

    if img.mode != "RGB":
        img = img.convert("RGB")

    return img


def encode_jpeg(img: Image.Image, quality: int) -> bytes:
    """Encode an image to JPEG in memory and return its bytes."""
    buffer = io.BytesIO()
    img.save(
        buffer,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
    )
    return buffer.getvalue()


def best_quality_under_limit(img: Image.Image):
    """
    Find the highest JPEG quality that fits within MAX_BYTES.
    Returns (jpeg_bytes, quality) or (None, None).
    """
    low = MIN_QUALITY
    high = MAX_QUALITY
    best_data = None
    best_quality = None

    while low <= high:
        quality = (low + high) // 2
        data = encode_jpeg(img, quality)

        if len(data) <= MAX_BYTES:
            best_data = data
            best_quality = quality
            low = quality + 1
        else:
            high = quality - 1

    return best_data, best_quality


def resize_to_limit(img: Image.Image):
    """
    Keep as much resolution and JPEG quality as practical while ensuring
    the final file is <= MAX_BYTES.
    """
    working = img.copy()

    while True:
        data, quality = best_quality_under_limit(working)
        if data is not None:
            return data, quality, working.size

        width, height = working.size
        long_edge = max(width, height)

        # Extremely unusual fallback: if already very small, force minimum quality.
        if long_edge <= MIN_LONG_EDGE:
            data = encode_jpeg(working, MIN_QUALITY)
            if len(data) <= MAX_BYTES:
                return data, MIN_QUALITY, working.size

            # Keep shrinking if a highly detailed image still exceeds the cap.
            new_width = max(1, int(width * SHRINK_FACTOR))
            new_height = max(1, int(height * SHRINK_FACTOR))
        else:
            new_width = max(1, int(width * SHRINK_FACTOR))
            new_height = max(1, int(height * SHRINK_FACTOR))

        working = working.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )


def output_path_for(source: Path) -> Path:
    return source.with_name(f"{source.stem}_resized.jpeg")


def process_image(source: Path):
    if source.stem.lower().endswith("_resized"):
        return "skipped", None

    if source.suffix.lower() in {".heic", ".heif"} and not HEIF_ENABLED:
        return (
            "error",
            "HEIC/HEIF support is missing. Install it with: pip install pillow-heif"
        )

    destination = output_path_for(source)

    try:
        with Image.open(source) as img:
            img.load()
            prepared = prepare_image(img)

        jpeg_data, quality, final_size = resize_to_limit(prepared)

        # Write only after successful processing.
        destination.write_bytes(jpeg_data)

        return (
            "ok",
            {
                "destination": destination,
                "bytes": len(jpeg_data),
                "quality": quality,
                "dimensions": final_size,
            },
        )

    except Exception as exc:
        return "error", str(exc)


def find_images(root: Path):
    for path in root.rglob("*"):
        if (
            path.is_file()
            and path.suffix.lower() in SUPPORTED_EXTENSIONS
            and not path.stem.lower().endswith("_resized")
        ):
            yield path


def main():
    parser = argparse.ArgumentParser(
        description="Recursively create <=1 MB JPEG copies of photos."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=None,
        help="Root folder. Defaults to the folder containing this script.",
    )
    args = parser.parse_args()

    if args.root:
        root = Path(args.root).expanduser().resolve()
    else:
        root = Path(__file__).resolve().parent

    if not root.exists() or not root.is_dir():
        print(f"ERROR: Root folder does not exist or is not a folder:\n{root}")
        sys.exit(1)

    print(f"Root folder: {root}")
    print(f"Maximum output size: {MAX_BYTES:,} bytes")
    print()

    images = list(find_images(root))

    if not images:
        print("No supported images found.")
        return

    print(f"Found {len(images)} image(s).\n")

    success = 0
    errors = 0

    for index, source in enumerate(images, start=1):
        rel_source = source.relative_to(root)
        print(f"[{index}/{len(images)}] {rel_source}")

        status, result = process_image(source)

        if status == "ok":
            success += 1
            rel_destination = result["destination"].relative_to(root)
            size_kb = result["bytes"] / 1000
            width, height = result["dimensions"]
            print(
                f"    -> {rel_destination}"
                f" | {size_kb:.1f} KB"
                f" | quality={result['quality']}"
                f" | {width}x{height}"
            )
        elif status == "error":
            errors += 1
            print(f"    ERROR: {result}")

    print("\nDone.")
    print(f"Created: {success}")
    print(f"Errors:  {errors}")

    if not HEIF_ENABLED:
        print(
            "\nNote: HEIC/HEIF support is not installed. "
            "If your iPhone photos are HEIC, run:\n"
            "    pip install pillow-heif"
        )


if __name__ == "__main__":
    main()
