#!/usr/bin/env python3
"""Trim blank margins from whiteboard snapshot images.

Feishu whiteboard thumbnails come as fixed-size squares (e.g. 2560x2560)
with the drawing in one corner and large blank areas baked into the file.
Auto-crops to the content bounding box plus padding. Requires Pillow; if
missing, copies the file unchanged and warns so the pipeline still runs.
"""

import argparse
import shutil
import sys
from pathlib import Path


def trim(src: Path, dst: Path, padding: int, threshold: int) -> dict:
    try:
        from PIL import Image, ImageChops
    except ImportError:
        shutil.copyfile(src, dst)
        return {"file": str(dst), "trimmed": False, "warning": "Pillow not installed; copied unchanged"}

    img = Image.open(src)
    rgb = img.convert("RGB")
    # 接近白色的像素视为空白
    gray = rgb.point(lambda v: 0 if v >= threshold else 255).convert("L")
    bbox = gray.getbbox()
    if not bbox:
        shutil.copyfile(src, dst)
        return {"file": str(dst), "trimmed": False, "warning": "blank image; copied unchanged"}

    left = max(bbox[0] - padding, 0)
    top = max(bbox[1] - padding, 0)
    right = min(bbox[2] + padding, img.width)
    bottom = min(bbox[3] + padding, img.height)
    if (left, top, right, bottom) == (0, 0, img.width, img.height):
        shutil.copyfile(src, dst)
        return {"file": str(dst), "trimmed": False}

    img.crop((left, top, right, bottom)).save(dst, quality=92)
    return {
        "file": str(dst),
        "trimmed": True,
        "from": f"{img.width}x{img.height}",
        "to": f"{right - left}x{bottom - top}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", help="Snapshot image file(s)")
    parser.add_argument("--out-dir", required=True, help="Directory for trimmed copies (same filenames)")
    parser.add_argument("--padding", type=int, default=24, help="Padding around content (default 24px)")
    parser.add_argument("--threshold", type=int, default=245, help="RGB value treated as blank (default 245)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    import json

    results = [trim(Path(p), out_dir / Path(p).name, args.padding, args.threshold) for p in args.images]
    print(json.dumps(results, ensure_ascii=False, indent=1))
    if any(r.get("warning") for r in results):
        sys.exit(0)


if __name__ == "__main__":
    main()
