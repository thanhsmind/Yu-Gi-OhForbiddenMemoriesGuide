#!/usr/bin/env python3
"""Mine yugipedia for the Forbidden Memories card DB + card art.

Sources (all read-only, MediaWiki APIs):
  - Gallery_of_Yu-Gi-Oh!_Forbidden_Memories_cards_(European_English) wikitext
    -> card number, English name, wiki page title, image file name
  - Semantic MediaWiki #ask -> card type, type, guardian star, level, ATK/DEF,
    password, star chip cost
  - imageinfo -> thumbnail URLs for the card art
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://yugipedia.com/api.php"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
GALLERY = "Gallery of Yu-Gi-Oh! Forbidden Memories cards (European English)"
THUMB_WIDTH = 320

ROOT = Path(sys.argv[1]).resolve()
IMG_DIR = ROOT / "images" / "cards"
DATA_DIR = ROOT / "data"


def get(url, binary=False, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            return raw if binary else json.loads(raw)
        except Exception as exc:  # noqa: BLE001 - retry anything transient
            if attempt == tries - 1:
                raise
            print(f"  retry {attempt + 1}: {exc}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))


def api(**params):
    params.setdefault("format", "json")
    return get(API + "?" + urllib.parse.urlencode(params))


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ---------------------------------------------------------------- gallery ---
def parse_gallery():
    wikitext = api(action="parse", page=GALLERY, prop="wikitext")["parse"]["wikitext"]["*"]
    body = re.search(r"<gallery[^>]*>(.*?)</gallery>", wikitext, re.S)
    line_re = re.compile(
        r"^(?P<file>\S+\.png)\s*\|\s*<nowiki>#</nowiki>(?P<num>\d+)<br\s*/>"
        r'"\[\[(?P<target>[^\]|]+)(?:\|(?P<label>[^\]]+))?\]\]"\s*$'
    )
    cards = []
    for line in body.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        m = line_re.match(line)
        if not m:
            print(f"  UNPARSED: {line}", file=sys.stderr)
            continue
        target = m.group("target").strip()
        name = (m.group("label") or target).strip()
        cards.append(
            {
                "number": int(m.group("num")),
                "name": name,
                "slug": slugify(name),
                "file": m.group("file"),
                "page": target,
                "url": "https://yugipedia.com/wiki/" + urllib.parse.quote(target.replace(" ", "_")),
            }
        )
    return cards


# -------------------------------------------------------------------- SMW ---
ASK_PROPS = [
    "Card number",
    "English name",
    "Card type (short)",
    "Type",
    "Guardian Star",
    "Level",
    "ATK#",
    "DEF#",
    "Password",
    "Star Chip cost",
    "Lore",
    "Japanese name",
    "Romaji name",
    "Translated Japanese name",
    "Obtained by",
    "Main card page",
]

WIKILINK = re.compile(r"\[\[(?:[^\]|]+\|)?([^\]|]+)\]\]")


def clean_lore(text):
    """Strip wiki markup from card text so it renders as plain prose."""
    if not text:
        return None
    text = WIKILINK.sub(r"\1", text)
    text = re.sub(r"'''(.+?)'''", r"\1", text)
    text = re.sub(r"''(.+?)''", r"\1", text)
    text = text.replace("&#35;", "#").replace("<br />", " ").replace("<br>", " ")
    return re.sub(r"\s+", " ", text).strip()


def strip_ruby(text):
    """Japanese names arrive as <ruby> markup; keep the base kanji, drop furigana."""
    if not text:
        return None
    text = re.sub(r"<rp>.*?</rp>|<rt>.*?</rt>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip() or None


def _flat(value):
    out = []
    for v in value or []:
        if isinstance(v, dict):
            v = v.get("fulltext") or v.get("value")
        if v not in (None, ""):
            out.append(v)
    return out


def _one(value):
    flat = _flat(value)
    return flat[0] if flat else None


def fetch_stats():
    stats = {}
    offset = 0
    while True:
        query = (
            "[[Release::Yu-Gi-Oh! Forbidden Memories]]|"
            + "|".join("?" + p for p in ASK_PROPS)
            + f"|sort=Card number|limit=500|offset={offset}"
        )
        data = api(action="ask", query=query)
        results = data.get("query", {}).get("results", {})
        if not results:
            break
        for page, row in results.items():
            p = row.get("printouts", {})
            num = _one(p.get("Card number"))
            if num is None:
                continue
            stats[int(num)] = {
                "cardType": clean_lore(_one(p.get("Card type (short)"))),
                "type": _one(p.get("Type")),
                "guardianStars": _flat(p.get("Guardian Star")) or None,
                "level": _one(p.get("Level")),
                "atk": _one(p.get("ATK")),
                "def": _one(p.get("DEF")),
                "password": _one(p.get("Password")),
                "starChipCost": _one(p.get("Star Chip cost")),
                "lore": clean_lore(_one(p.get("Lore"))),
                "japaneseName": strip_ruby(_one(p.get("Japanese name"))),
                "romajiName": _one(p.get("Romaji name")),
                "translatedJapaneseName": _one(p.get("Translated Japanese name")),
                "obtainedBy": _flat(p.get("Obtained by")) or None,
                "mainCardPage": _one(p.get("Main card page")),
                "wikiPage": page,
            }
        nxt = data.get("query-continue-offset")
        if not nxt or nxt <= offset:
            break
        offset = nxt
        print(f"  stats so far: {len(stats)}")
    return stats


# ------------------------------------------------------------------ images ---
def fetch_image_urls(files):
    urls = {}
    for i in range(0, len(files), 50):
        chunk = files[i : i + 50]
        data = api(
            action="query",
            titles="|".join("File:" + f for f in chunk),
            prop="imageinfo",
            iiprop="url",
            iiurlwidth=THUMB_WIDTH,
        )
        norm = {n["to"]: n["from"] for n in data["query"].get("normalized", [])}
        for page in data["query"]["pages"].values():
            title = page["title"]
            title = norm.get(title, title)
            key = title.split(":", 1)[1]
            info = page.get("imageinfo")
            if not info:
                print(f"  MISSING FILE: {key}", file=sys.stderr)
                continue
            urls[key] = info[0].get("thumburl") or info[0]["url"]
        print(f"  image urls: {len(urls)}/{len(files)}")
    return urls


def download(cards, urls):
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    ok = missing = skipped = 0
    for c in cards:
        dest = IMG_DIR / (c["slug"] + ".png")
        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            c["image"] = f"images/cards/{c['slug']}.png"
            continue
        url = urls.get(c["file"])
        if not url:
            missing += 1
            c["image"] = None
            continue
        dest.write_bytes(get(url, binary=True))
        c["image"] = f"images/cards/{c['slug']}.png"
        ok += 1
        if ok % 50 == 0:
            print(f"  downloaded {ok}")
    return ok, skipped, missing


def main():
    print("1/4 gallery wikitext")
    cards = parse_gallery()
    print(f"  cards: {len(cards)}")

    print("2/4 semantic stats")
    stats = fetch_stats()
    print(f"  stats: {len(stats)}")

    for c in cards:
        s = stats.get(c["number"], {})
        c.update(
            {
                "cardType": s.get("cardType"),
                "type": s.get("type"),
                "guardianStars": s.get("guardianStars"),
                "level": s.get("level"),
                "atk": s.get("atk"),
                "def": s.get("def"),
                "password": s.get("password"),
                "starChipCost": s.get("starChipCost"),
                "lore": s.get("lore"),
                "japaneseName": s.get("japaneseName"),
                "romajiName": s.get("romajiName"),
                "translatedJapaneseName": s.get("translatedJapaneseName"),
                "obtainedBy": s.get("obtainedBy"),
                "mainCardPage": s.get("mainCardPage"),
                "mainCardUrl": (
                    "https://yugipedia.com/wiki/"
                    + urllib.parse.quote(s["mainCardPage"].replace(" ", "_"))
                    if s.get("mainCardPage")
                    else None
                ),
            }
        )

    print("3/4 image urls")
    urls = fetch_image_urls(sorted({c["file"] for c in cards}))

    print("4/4 download images")
    ok, skipped, missing = download(cards, urls)
    print(f"  new={ok} cached={skipped} missing={missing}")

    # slug collisions would silently overwrite art -- report them.
    seen = {}
    for c in cards:
        seen.setdefault(c["slug"], []).append(c["number"])
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    if dupes:
        print(f"  SLUG COLLISIONS: {dupes}", file=sys.stderr)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": {
            "gallery": "https://yugipedia.com/wiki/"
            + urllib.parse.quote(GALLERY.replace(" ", "_")),
            "stats": "Semantic MediaWiki ask: [[Release::Yu-Gi-Oh! Forbidden Memories]]",
            "fetched": time.strftime("%Y-%m-%d"),
            "license": "Yugipedia text CC BY-SA; card art © Konami, fan-guide use",
        },
        "count": len(cards),
        "cards": sorted(cards, key=lambda c: c["number"]),
    }
    out = DATA_DIR / "cards.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")

    for field in ("atk", "lore", "type", "password"):
        filled = sum(1 for c in cards if c.get(field) is not None)
        print(f"cards with {field}: {filled}/{len(cards)}")


if __name__ == "__main__":
    main()
