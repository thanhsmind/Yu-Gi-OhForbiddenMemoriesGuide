#!/usr/bin/env python3
"""Mine docs/guide/*.md into a single window.FM_DATA JS block.

This is a developer-only tool (decision D6 in
docs/history/fm-guide-site/CONTEXT.md): the shipped index.html never runs
Python, it only embeds the JS this script prints. Re-run this script and
splice its output between the `/* FM_DATA:BEGIN */` / `/* FM_DATA:END */`
markers in index.html whenever docs/guide/ changes.

Sources (read-only, never edited by this script):
  - "Game Yu-Gi-Oh! Forbidden Memories Quân Bài Phụ trợ.md"
      #NNN <name> (<n> Equips) headers + their #NNN <item> lines -> the
      number<->name roster (653 pairs) and per-monster equip lists.
  - "Game Yu-Gi-Oh! Forbidden Memories fusion.md"
      three fenced sections: "Dung hợp cơ bản" ([Type]+[Type] = Name
      (ATK/DEF Star/Star)), "Dung hợp chính xác" (Name + Name = Name), and
      "Dung hợp xung đột" (per-card fusion-system membership).

D4 (docs/history/fm-guide-site/CONTEXT.md): a field with no source is
`None` (-> JSON null). Never 0, never guessed.

Usage:
    python3 tools/extract_cards.py                  # print JS to stdout
    python3 tools/extract_cards.py --out FILE        # write JS to FILE
    python3 tools/extract_cards.py --json            # print raw JSON
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUIDE_DIR = REPO_ROOT / "docs" / "guide"

EQUIP_FILE = GUIDE_DIR / "Game Yu-Gi-Oh! Forbidden Memories Quân Bài Phụ trợ.md"
FUSION_FILE = GUIDE_DIR / "Game Yu-Gi-Oh! Forbidden Memories fusion.md"

# Three names that are spelled differently in fusion.md than in the equip
# file's #NNN roster (docs/history/fm-guide-site/plan.md, "Ba tên lệch giữa
# hai file"). Fixed table, never fuzzy/prefix matching.
NAME_ALIASES = {
    "blue-eyed silver zombie": "139",   # -> #139 Blue Eyes Silver Zombie
    "doma the angel of silence": "111",  # -> #111 Doma the Angel of Silence
    "stone d.": "426",                   # -> #426 Stone Dragon
}

EQUIP_HEADER_RE = re.compile(r'^#(\d+)\s+(.*?)\s*\(\s*(\d+)\s*Equips?\s*\)')
EQUIP_ITEM_RE = re.compile(r'^#(\d+)\s+(.+?)\s*$')
STAT_RE = re.compile(r'^([^()]+?)\s*\((\d+)/(\d+)\s+(\w+)/(\w+)\)\s*$')
CONFLICT_TOP_HEADER_RE = re.compile(r'^\s*\[[^\]]+\]\s*\+\s*\[[^\]]+\]\s*=\s*.+$')


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def slugify(name: str) -> str:
    """D3: lowercase; every run of non a-z0-9 chars becomes one '-'; trim
    leading/trailing '-'."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def extract_fenced_after(lines: list[str], marker: str, until: str | None = None) -> list[str]:
    """Lines inside ``` fences, starting from the first line containing
    `marker`, stopping before the first later line containing `until`
    (or at end of file). Handles a section split across several adjacent
    fences (fusion.md's "Dung hợp xung đột" closes and reopens a fence
    with nothing but a blank line between them in a few places) by simply
    toggling fence state — content is included whenever we are inside a
    fence, regardless of how many fences the section is split into.
    """
    start = next(i for i, l in enumerate(lines) if marker in l)
    end = len(lines)
    if until:
        for i in range(start + 1, len(lines)):
            if until in lines[i]:
                end = i
                break
    in_fence = False
    out = []
    for line in lines[start:end]:
        if line.strip() == "```":
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(line)
    return out


# ---------------------------------------------------------------------------
# (a) Number <-> name roster + per-monster equip lists
# "Game Yu-Gi-Oh! Forbidden Memories Quân Bài Phụ trợ.md"
# ---------------------------------------------------------------------------

def parse_equip_file(lines: list[str]):
    """Returns (numbered_names, equip_lists).

    numbered_names: {number(str) -> name}, one entry per distinct #NNN seen
      across BOTH the "#NNN Name (n Equips)" monster headers (621) and the
      "#NNN Item" equip lines nested under them (32 more, first-seen name
      wins) -> 653 total pairs.
    equip_lists: one entry per monster header block, in source order:
      {number, name, equip_count, equips: [{number, name}, ...]}.

    The header regex only requires "#NNN <name> (<n> Equips)" as a prefix
    and ignores anything after the closing paren, so it tolerates the
    malformed "#395 Dancing Elf  (10 Equips) ------..." line where the
    dashes are glued onto the header line itself instead of living on
    their own '---' line.
    """
    numbered_names: dict[str, str] = {}
    equip_lists = []
    in_block = False
    current = None

    for line in lines:
        header = EQUIP_HEADER_RE.match(line)
        if header:
            num, name, count = header.group(1), header.group(2).strip(), header.group(3)
            numbered_names.setdefault(num, name)
            current = {
                "number": num,
                "name": name,
                "equip_count": int(count),
                "equips": [],
            }
            equip_lists.append(current)
            in_block = True
            continue

        stripped = line.strip()
        if stripped.startswith("====="):
            in_block = False
            current = None
            continue
        if stripped.startswith("---"):
            continue  # separator line under a header, never an item line

        if in_block and current is not None:
            item = EQUIP_ITEM_RE.match(line)
            if item:
                inum, iname = item.group(1), item.group(2).strip()
                numbered_names.setdefault(inum, iname)
                current["equips"].append({"number": inum, "name": iname})

    return numbered_names, equip_lists


# ---------------------------------------------------------------------------
# Shared stat-entry parsing: "Name (ATK/DEF Star/Star)[, Name2 (...), ...]"
# ---------------------------------------------------------------------------

def parse_stat_entries(text: str) -> list[dict]:
    # Split on a comma that follows a closing paren, never on any other
    # comma — card names can contain thousand-separator commas
    # (e.g. "30,000-Year White Turtle"); splitting on every comma would
    # shred that name into "30" and "000-Year White Turtle".
    parts = re.split(r"(?<=\)),\s*", text)
    out = []
    for part in parts:
        part = part.strip().rstrip(",").strip()
        if not part:
            continue
        m = STAT_RE.match(part)
        if m:
            out.append(
                {
                    "name": m.group(1).strip(),
                    "atk": int(m.group(2)),
                    "def": int(m.group(3)),
                    "star1": m.group(4),
                    "star2": m.group(5),
                }
            )
    return out


def parse_side(raw: str) -> dict:
    """A recipe side is either a bracketed fusion type ([Zombie]), a
    brace-delimited set of specific cards ({A, B}), or a single specific
    card name."""
    s = raw.strip()
    if s.startswith("{") and s.endswith("}"):
        names = [x.strip() for x in s[1:-1].split(",") if x.strip()]
        return {"kind": "names", "value": names}
    m = re.match(r"^\[([^\]]+)\]$", s)
    if m:
        return {"kind": "type", "value": m.group(1).strip()}
    return {"kind": "name", "value": s}


def split_on_plus_and_delim(line: str, delim: str):
    """Split a "LEFT + RIGHT <delim> TAIL" header line into its three
    parts. Columns are aligned with runs of spaces, not a fixed width —
    we only rely on the literal '+' and `delim` characters, which is safe
    because card names never contain them."""
    idx_plus = line.index("+")
    left = line[:idx_plus].strip()
    rest = line[idx_plus + 1 :]
    idx_delim = rest.index(delim)
    right = rest[:idx_delim].strip()
    tail = rest[idx_delim + len(delim) :].strip()
    return left, right, tail


# ---------------------------------------------------------------------------
# (b) "Dung hợp cơ bản" — [Type] + [Type] = Name (ATK/DEF Star/Star)
# ---------------------------------------------------------------------------

def parse_fusion_basic(lines: list[str]):
    """Returns (fusion_basic, atk_def_by_name).

    fusion_basic: one entry per [Left]+[Right] block, in source order:
      {left, right, results: [stat...], possible: [stat...]}.
      `results` are the block's direct "= Name (...)" outcomes; `possible`
      are the "< Name (...), ..." cards that can also arise for that pair
      once other card-specific rules are applied. Blocks are separated by
      blank lines in the source; every block's first line starts with the
      left side's '['.
    atk_def_by_name: {name -> stat} across every stat sighting in the
      section (results + possible combined) — the section's only source
      of ATK/DEF + Guardian Star pairs (101 distinct names).
    """
    content = extract_fenced_after(lines, "Dung hợp cơ bản", until="Dung hợp chính xác")

    blocks: list[list[str]] = []
    current: list[str] = []
    for line in content:
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)

    atk_def_by_name: dict[str, dict] = {}
    fusion_basic = []

    for block in blocks:
        first = block[0]
        left_raw, right_raw, tail = split_on_plus_and_delim(first, "=") if "=" in first[first.index("+") :] else (
            first[: first.index("+")].strip(),
            first[first.index("+") + 1 :].strip(),
            None,
        )
        remaining = block[1:]
        if tail is not None:
            remaining = [tail] + remaining

        left = parse_side(left_raw)
        right = parse_side(right_raw)

        results: list[dict] = []
        possible: list[dict] = []
        mode = "results"
        for raw in remaining:
            s = raw.strip()
            if not s:
                continue
            if s.startswith("="):
                mode = "results"
                s = s[1:].strip()
            elif s.startswith("<"):
                mode = "possible"
                s = s[1:].strip()
            if not s:
                continue
            entries = parse_stat_entries(s)
            target = results if mode == "results" else possible
            for entry in entries:
                target.append(entry)
                atk_def_by_name.setdefault(entry["name"], entry)

        fusion_basic.append(
            {"left": left, "right": right, "results": results, "possible": possible}
        )

    return fusion_basic, atk_def_by_name


# ---------------------------------------------------------------------------
# "Dung hợp chính xác" — Name + Name = Name (no stats)
# ---------------------------------------------------------------------------

EXACT_LINE_RE = re.compile(r"^(.*?)\+\s*(.*?)=\s*(.*)$")


def parse_fusion_exact(lines: list[str]) -> list[dict]:
    content = extract_fenced_after(lines, "Dung hợp chính xác", until="Dung hợp xung đột")
    out = []
    for line in content:
        if not line.strip():
            continue
        m = EXACT_LINE_RE.match(line)
        if not m:
            continue
        a, b, result = (g.strip() for g in m.groups())
        out.append({"a": a, "b": b, "result": result})
    return out


# ---------------------------------------------------------------------------
# (c) "Dung hợp xung đột" — per-card fusion-system membership
# ---------------------------------------------------------------------------

def parse_fusion_conflict(lines: list[str]):
    """Returns (stanzas, groups, member_names).

    Each stanza is two header lines followed by a two-column member table
    (until a blank line):
        [GeneralLeft] + [GeneralRight] = GeneralResult
        [OverrideLeft|Name] + [OverrideRight|Name] < OverrideResult
        LeftMember                       RightMember
        ...
    Columns are split on runs of 2+ spaces (never a fixed character
    width — long names such as "Wicked Dragon with the Ersatz Head" push
    the right column further out, see fusion.md:1072 and :3326).

    groups: {bracket-type-tag -> set(member names)}, built from whichever
      side(s) of each stanza's override header are a `[Type]` (not every
      side is; some override rules pin a *specific* card instead of a
      type, e.g. "[Sheepian] + Mystical Sheep #2 < Mystical Sheep #1").
    member_names: every distinct name that appears in a member row,
      regardless of which side/type it belongs to.
    """
    content = extract_fenced_after(lines, "Dung hợp xung đột")
    stanzas = []
    groups: dict[str, set[str]] = {}
    member_names: set[str] = set()

    i = 0
    n = len(content)
    while i < n:
        line = content[i]
        if line.strip() == "" or not CONFLICT_TOP_HEADER_RE.match(line):
            i += 1
            continue

        top_left, top_right, top_result = split_on_plus_and_delim(line, "=")
        i += 1
        if i >= n:
            break

        override_line = content[i]
        if "+" not in override_line or "<" not in override_line:
            # Malformed/unexpected shape — skip defensively rather than crash.
            i += 1
            continue
        ov_left_raw, ov_right_raw, ov_result = split_on_plus_and_delim(override_line, "<")
        left = parse_side(ov_left_raw)
        right = parse_side(ov_right_raw)
        i += 1

        members = []
        # A member block normally ends at a blank line. Guard it against
        # also ending at the next stanza's top header: fusion.md has one
        # spot (the seam between two adjacent ``` fences, around
        # "Witch's Apprentice" / "[Aqua] + [Dragon] = Kairyu-shin") where
        # the blank-line separator is missing in the source. Without this
        # guard, the next header's own tokens ("[Aqua]",
        # "+ [Dragon] = Kairyu-shin") would be swallowed as fake member
        # names — exactly the kind of dòng ma D4 forbids.
        while i < n and content[i].strip() != "" and not CONFLICT_TOP_HEADER_RE.match(content[i]):
            row = content[i]
            cols = re.split(r"\s{2,}", row.rstrip())
            left_name = cols[0].strip() if len(cols) >= 1 and cols[0].strip() else None
            right_name = cols[1].strip() if len(cols) >= 2 and cols[1].strip() else None
            if left_name or right_name:
                members.append({"left": left_name, "right": right_name})
            if left_name:
                member_names.add(left_name)
                if left["kind"] == "type":
                    groups.setdefault(left["value"], set()).add(left_name)
            if right_name:
                member_names.add(right_name)
                if right["kind"] == "type":
                    groups.setdefault(right["value"], set()).add(right_name)
            i += 1

        stanzas.append(
            {
                "generalLeft": top_left.strip("[] "),
                "generalRight": top_right.strip("[] "),
                "generalResult": top_result,
                "overrideLeft": left,
                "overrideRight": right,
                "overrideResult": ov_result,
                "members": members,
            }
        )

    return stanzas, groups, member_names


# ---------------------------------------------------------------------------
# Join everything into one dataset
# ---------------------------------------------------------------------------

def build_name_lookup(numbered_names: dict[str, str]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for num, name in numbered_names.items():
        lookup.setdefault(name.lower(), num)
    return lookup


def resolve_number(name: str, name_lookup: dict[str, str]) -> str | None:
    key = name.strip().lower()
    if key in NAME_ALIASES:
        return NAME_ALIASES[key]
    return name_lookup.get(key)


def extract_all() -> dict:
    numbered_names, equip_lists = parse_equip_file(read_lines(EQUIP_FILE))

    fusion_lines = read_lines(FUSION_FILE)
    fusion_basic, atk_def_by_name = parse_fusion_basic(fusion_lines)
    fusion_exact = parse_fusion_exact(fusion_lines)
    fusion_conflict, groups, member_names = parse_fusion_conflict(fusion_lines)

    name_lookup = build_name_lookup(numbered_names)

    atk_def_by_number: dict[str, dict] = {}
    for name, stat in atk_def_by_name.items():
        num = resolve_number(name, name_lookup)
        if num:
            atk_def_by_number[num] = stat

    name_to_tags: dict[str, set[str]] = {}
    for tag, names in groups.items():
        for nm in names:
            name_to_tags.setdefault(nm, set()).add(tag)

    tags_by_number: dict[str, set[str]] = {}
    for nm, tags in name_to_tags.items():
        num = resolve_number(nm, name_lookup)
        if num:
            tags_by_number.setdefault(num, set()).update(tags)

    equips_by_number = {e["number"]: e["equips"] for e in equip_lists}

    cards = []
    for num in sorted(numbered_names, key=int):
        name = numbered_names[num]
        stat = atk_def_by_number.get(num)
        tags = tags_by_number.get(num)
        cards.append(
            {
                "number": num,
                "name": name,
                "slug": slugify(name),
                "atk": stat["atk"] if stat else None,
                "def": stat["def"] if stat else None,
                "guardianStars": [stat["star1"], stat["star2"]] if stat else None,
                "fusionSystems": sorted(tags) if tags else None,
                "equips": equips_by_number.get(num),
            }
        )

    meta = {
        "totalNumberedCards": len(cards),
        "atkDefEntriesInFusionSource": len(atk_def_by_name),
        "cardsWithAtkDef": sum(1 for c in cards if c["atk"] is not None),
        "fusionConflictMemberNames": sorted(member_names),
        "fusionGroupsWithMembers": sorted(tag for tag, names in groups.items() if names),
    }

    return {
        "cards": cards,
        "equipLists": equip_lists,
        "fusionBasic": fusion_basic,
        "fusionExact": fusion_exact,
        "fusionConflict": fusion_conflict,
        "fusionGroups": {tag: sorted(names) for tag, names in sorted(groups.items())},
        "meta": meta,
    }


FM_DATA_BEGIN_MARKER = "/* FM_DATA:BEGIN */"
FM_DATA_END_MARKER = "/* FM_DATA:END */"

DEFAULT_INJECT_TARGET = REPO_ROOT / "index.html"


def build_js(data: dict) -> str:
    """The exact block spliced between the FM_DATA markers in index.html
    (cell fm-guide-site-2, D2). The marker lines themselves are the exact
    literal strings FM_DATA_BEGIN_MARKER/FM_DATA_END_MARKER — no trailing
    comment on the BEGIN line, so `--inject` can find them by exact string
    match rather than a prefix scan."""
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    return (
        f"{FM_DATA_BEGIN_MARKER}\n"
        "/* generated by tools/extract_cards.py; do not hand-edit */\n"
        f"window.FM_DATA = {payload};\n"
        f"{FM_DATA_END_MARKER}\n"
    )


def inject_into(html_path: Path, data: dict) -> str:
    """Overwrite exactly the region between the two FM_DATA markers
    (inclusive of the marker lines) in `html_path`, leaving every other
    byte of the file untouched. Returns the new file text; raises
    ValueError if either marker is missing so a bad --inject target fails
    loudly instead of silently doing nothing."""
    text = html_path.read_text(encoding="utf-8")
    try:
        start = text.index(FM_DATA_BEGIN_MARKER)
    except ValueError as exc:
        raise ValueError(f"{FM_DATA_BEGIN_MARKER!r} not found in {html_path}") from exc
    try:
        end = text.index(FM_DATA_END_MARKER, start) + len(FM_DATA_END_MARKER)
    except ValueError as exc:
        raise ValueError(f"{FM_DATA_END_MARKER!r} not found in {html_path}") from exc

    new_block = build_js(data).rstrip("\n")
    new_text = text[:start] + new_block + text[end:]
    html_path.write_text(new_text, encoding="utf-8")
    return new_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="write output to this path instead of stdout")
    parser.add_argument(
        "--json", action="store_true", help="emit raw JSON instead of the window.FM_DATA JS block"
    )
    parser.add_argument(
        "--inject",
        nargs="?",
        const=str(DEFAULT_INJECT_TARGET),
        metavar="HTML_FILE",
        help=(
            "splice the freshly extracted data between the FM_DATA:BEGIN/END "
            "markers of HTML_FILE (default: index.html at repo root), "
            "leaving the rest of the file byte-for-byte unchanged. Idempotent: "
            "running twice in a row produces byte-identical output."
        ),
    )
    args = parser.parse_args(argv)

    data = extract_all()

    if args.inject is not None:
        inject_into(Path(args.inject), data)
        return 0

    text = (json.dumps(data, ensure_ascii=False, indent=2) + "\n") if args.json else build_js(data)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
