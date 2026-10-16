#!/usr/bin/env python3
"""
tg-media-tools — Watermark and compress images for Telegram sharing.

Usage:
    python media_tools.py watermark input.jpg --text "@myhandle" --position bottom-right --opacity 128
    python media_tools.py compress input.jpg --max-kb 500
    python media_tools.py info input.jpg
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right", "center")
MARGIN = 12


def die(message):
    """Print an error message and exit with a non-zero status."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def load_image(path):
    """Load an image from disk, with clear errors for missing/unsupported files."""
    if not os.path.isfile(path):
        die(f"file not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        die(
            f"unsupported format '{ext or '(no extension)'}' — "
            f"supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )
    try:
        img = Image.open(path)
        img.load()  # force the file to be read so corrupt files fail here
    except Exception as exc:
        die(f"could not read image '{path}': {exc}")
    return img


def suffixed(path, suffix, new_ext=None):
    """Return a sibling output path, e.g. 'photo.jpg' -> 'photo_watermarked.jpg'."""
    base, ext = os.path.splitext(path)
    return base + suffix + (new_ext if new_ext is not None else ext)


def get_font(image_width):
    """Pick a readable font, scaled to the image width."""
    size = max(12, image_width // 20)
    for candidate in (
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow versions have no size parameter
        return ImageFont.load_default()


def cmd_watermark(args):
    """Draw semi-transparent text over the image and save as JPEG."""
    img = load_image(args.input).convert("RGBA")
    if not 0 <= args.opacity <= 255:
        die("--opacity must be between 0 and 255")

    font = get_font(img.width)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bbox = draw.textbbox((0, 0), args.text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    w, h = img.size
    positions = {
        "top-left": (MARGIN, MARGIN),
        "top-right": (w - text_w - MARGIN, MARGIN),
        "bottom-left": (MARGIN, h - text_h - MARGIN),
        "bottom-right": (w - text_w - MARGIN, h - text_h - MARGIN),
        "center": ((w - text_w) // 2, (h - text_h) // 2),
    }
    x, y = positions[args.position]
    # textbbox can report a non-zero origin, so compensate to align correctly
    x -= bbox[0]
    y -= bbox[1]

    draw.text((x, y), args.text, font=font, fill=(255, 255, 255, args.opacity))
    result = Image.alpha_composite(img, overlay).convert("RGB")

    out = args.output or suffixed(args.input, "_watermarked", ".jpg")
    result.save(out, "JPEG", quality=92)
    print(f"Saved {out}")


def cmd_compress(args):
    """Re-encode (and shrink if needed) a JPEG so it fits under --max-kb."""
    img = load_image(args.input).convert("RGB")
    if args.max_kb <= 0:
        die("--max-kb must be a positive number")
    target_bytes = int(args.max_kb * 1024)

    out = args.output or suffixed(args.input, "_compressed", ".jpg")

    quality = 95
    working = img
    while True:
        working.save(out, "JPEG", quality=quality, optimize=True)
        if os.path.getsize(out) <= target_bytes:
            break
        if quality > 30:
            quality -= 10
        else:
            w, h = working.size
            if min(w, h) <= 200:
                break  # shrinking further would destroy the image
            working = working.resize(
                (int(w * 0.85), int(h * 0.85)), Image.LANCZOS
            )
            quality = 85

    final_bytes = os.path.getsize(out)
    print(f"Saved {out} ({final_bytes / 1024:.1f} KB)")
    if final_bytes > target_bytes:
        print(
            f"Warning: could not get below {args.max_kb} KB without "
            "heavy quality loss.",
            file=sys.stderr,
        )


def cmd_info(args):
    """Print basic metadata about an image."""
    img = load_image(args.input)
    size_bytes = os.path.getsize(args.input)
    print(f"Path:       {args.input}")
    print(f"Dimensions: {img.width} x {img.height}")
    print(f"Format:     {img.format}")
    print(f"Mode:       {img.mode}")
    print(f"File size:  {size_bytes} bytes ({size_bytes / 1024:.1f} KB)")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="media_tools.py",
        description="Watermark and compress images for Telegram sharing.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_wm = sub.add_parser("watermark", help="Overlay semi-transparent text on an image.")
    p_wm.add_argument("input", help="Input image file.")
    p_wm.add_argument("--text", default="@myhandle", help="Watermark text (default: @myhandle).")
    p_wm.add_argument(
        "--position",
        choices=POSITIONS,
        default="bottom-right",
        help="Where to place the text (default: bottom-right).",
    )
    p_wm.add_argument(
        "--opacity",
        type=int,
        default=128,
        help="Text opacity, 0 (invisible) to 255 (solid). Default: 128.",
    )
    p_wm.add_argument("--output", help="Output file (default: <input>_watermarked.jpg).")
    p_wm.set_defaults(func=cmd_watermark)

    p_cp = sub.add_parser("compress", help="Re-encode an image to fit under a size limit.")
    p_cp.add_argument("input", help="Input image file.")
    p_cp.add_argument(
        "--max-kb",
        type=float,
        default=500,
        help="Target maximum file size in KB (default: 500).",
    )
    p_cp.add_argument("--output", help="Output file (default: <input>_compressed.jpg).")
    p_cp.set_defaults(func=cmd_compress)

    p_in = sub.add_parser("info", help="Print dimensions, format, file size and mode.")
    p_in.add_argument("input", help="Input image file.")
    p_in.set_defaults(func=cmd_info)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
