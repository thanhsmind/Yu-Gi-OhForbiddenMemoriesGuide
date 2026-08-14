#!/usr/bin/env python3
"""Compress the CardFusionExplorer source PNG art into a second image set
at images/art/<slug>.webp (decision D12 in
docs/history/fm-guide-site/CONTEXT.md).

This is a developer-only tool (D6): Pillow is its dependency, never the
shipped page's. tools/check.py, which the page's data flow runs through,
never imports Pillow.

Source images -- NOT committed (see docs/history/fm-guide-site/plan.md
"Nguồn nào vào git"), must already exist on this machine, and are never
downloaded by this script: a local copy of
data/CardFusionExplorer/Card-Fusion-Explorer-Assets/images/ -- 1,057 PNGs
(Rush Duel-style art) + 99 unrelated IMG-ART .webp files, 350MB total. Each
PNG's filename comes off the matching
data/CardFusionExplorer/Card-Fusion-Explorer-Assets/cartas_runtime.json
entry's `IMG-CARD` field (e.g. "res://Imagens/cartas/
blue-eyes_white_dragon.png" -> basename "blue-eyes_white_dragon.png").
If the directory is absent, this script prints an error naming the
expected path and exits 1 -- it never fetches anything from the network.

File -> FM_DATA slug: the same join tools/extract_cards.py uses to fold
cartas_runtime.json's 360 outside-FM cards onto the FM_DATA card table
(EQUIP_NAME_ALIASES, normalize_match_name(), slugify() -- imported from
extract_cards.py rather than re-derived, so the two tools can never drift
apart: for a cartas_runtime.json row whose `Card` name matches one of the
722 FM cards after the alias+normalize join, this script uses that FM
card's real data/cards.json slug; every other row gets slugify(Card name),
exactly like extract_cards.py's load_outside_fm_cards() does for that same
row). Measured: 1,056 of cartas_runtime.json's 1,056 entries resolve to a
real FM_DATA slug (722 FM + 360 outside-FM = 1,082 cards total) -- the
other 26 FM_DATA cards (Ritual cards absent from this source, per D12 /
CONTEXT.md "Reusable Assets") get no images/art/ file at all.

Compression: every sampled source PNG measured 256x374px (already under
the 400px-wide budget in D12) with a fully opaque alpha channel (every
sampled image's alpha extrema is (255, 255)) -- so `convert("RGB")` just
drops the unused alpha channel losslessly rather than compositing over a
guessed background color. Resized to <=MAX_WIDTH px wide, aspect ratio
kept, only when a source image is actually wider than that (none in this
dataset are). Re-encoded WEBP_QUALITY=80, method=6 -- measured (30-image
sample) ~22 KB/image average, ~22.7MB projected for all 1,056 images,
comfortably under the 40MB budget in D12; this script's own printed
"tổng dung lượng" line re-measures the real output directory rather than
trusting that projection, and so does tools/check.py.

Usage:
    python3 tools/build_art_images.py
    python3 tools/build_art_images.py --images-dir /path/to/images
    python3 tools/build_art_images.py --quality 70 --max-width 400
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover - environment guard, not test-covered
    print(
        "build_art_images.py needs Pillow (pip install pillow) -- a "
        "developer-only dependency (D6); tools/check.py never imports it.",
        file=sys.stderr,
    )
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_cards as ec  # noqa: E402  (import after sys.path tweak, by design)

DEFAULT_IMAGES_DIR = Path(
    "/home/thanhsmind/projects/goglbe/Yu-Gi-OhForbiddenMemoriesGuide/"
    "data/CardFusionExplorer/Card-Fusion-Explorer-Assets/images"
)
OUT_DIR = ec.REPO_ROOT / "images" / "art"
MAX_WIDTH = 400
WEBP_QUALITY = 80


def resolve_basename_to_slug() -> dict[str, str]:
    """basename(IMG-CARD) -> FM_DATA slug, one entry per cartas_runtime.json
    row -- see module docstring for the join rule. Reuses
    extract_cards.py's own EQUIP_NAME_ALIASES/normalize_match_name/slugify
    rather than re-deriving them, so a future edit to either the alias
    table or the slug rule can't silently make this script and
    extract_cards.py disagree about which slug a given image belongs to."""
    fm_cards = ec.load_spine_cards()
    fm_by_norm = {ec.normalize_match_name(c["name"]): c["slug"] for c in fm_cards}

    raw = json.loads(ec.CARTAS_RUNTIME_JSON.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for entry in raw:
        img = entry.get("IMG-CARD")
        if not img:
            continue
        basename = Path(img).name
        name = entry["Card"]
        lookup_name = ec.EQUIP_NAME_ALIASES.get(name.strip().lower(), name)
        norm = ec.normalize_match_name(lookup_name)
        slug = fm_by_norm.get(norm) or ec.slugify(name)
        mapping[basename] = slug
    return mapping


def total_fm_data_card_count() -> int:
    """722 FM cards + 360 outside-FM cards -- computed the same way
    extract_cards.py's extract_all() does, without paying for the rest of
    that function's work (fusion_unique.json's 50,937 rows, docs/guide/
    parsing, etc.) which this script doesn't need."""
    fm_cards = ec.load_spine_cards()
    outside_cards = ec.load_outside_fm_cards(fm_cards)
    return len(fm_cards) + len(outside_cards)


def build(images_dir: Path, out_dir: Path, quality: int, max_width: int) -> int:
    if not images_dir.is_dir():
        print(
            f"error: nguồn ảnh gốc không có trên máy: {images_dir}\n"
            "Đây là bộ ảnh CardFusionExplorer chưa commit (350MB) -- phải "
            "có sẵn trên máy này; công cụ này không tự tải gì từ mạng.",
            file=sys.stderr,
        )
        return 1

    mapping = resolve_basename_to_slug()
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.webp"):
        stale.unlink()

    built = 0
    missing_source: list[str] = []
    for basename, slug in sorted(mapping.items()):
        src = images_dir / basename
        if not src.is_file():
            missing_source.append(basename)
            continue
        with Image.open(src) as im:
            if im.mode != "RGB":
                im = im.convert("RGB")
            if im.width > max_width:
                new_height = round(im.height * max_width / im.width)
                im = im.resize((max_width, new_height), Image.LANCZOS)
            im.save(out_dir / f"{slug}.webp", "WEBP", quality=quality, method=6)
        built += 1

    total_cards = total_fm_data_card_count()
    cards_without_art = total_cards - built
    total_bytes = sum(f.stat().st_size for f in out_dir.glob("*.webp"))

    print(f"số ảnh đã dựng:              {built}")
    print(f"số lá không có ảnh:          {cards_without_art} (trên tổng {total_cards} lá FM_DATA)")
    print(f"tổng dung lượng images/art/: {total_bytes / 1024 / 1024:.2f} MB")
    if missing_source:
        print(
            f"cảnh báo: {len(missing_source)} basename(s) từ cartas_runtime.json "
            f"không thấy trong {images_dir}, ví dụ {missing_source[:5]}",
            file=sys.stderr,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=DEFAULT_IMAGES_DIR,
        help="thư mục ảnh PNG gốc CardFusionExplorer (mặc định máy dev hiện tại)",
    )
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR, help="thư mục ghi WebP ra")
    parser.add_argument("--quality", type=int, default=WEBP_QUALITY, help="chất lượng WebP (0-100)")
    parser.add_argument("--max-width", type=int, default=MAX_WIDTH, help="bề rộng tối đa (px)")
    args = parser.parse_args(argv)
    return build(args.images_dir, args.out_dir, args.quality, args.max_width)


if __name__ == "__main__":
    sys.exit(main())
