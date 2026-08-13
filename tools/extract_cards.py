#!/usr/bin/env python3
"""Build a single window.FM_DATA JS block: the card spine from
data/cards.json (D7), with equip lists and fusion recipes mined from
docs/guide/*.md joined on top by card name.

This is a developer-only tool (decision D6 in
docs/history/fm-guide-site/CONTEXT.md): the shipped index.html never runs
Python, it only embeds the JS this script prints. Re-run this script and
splice its output between the `/* FM_DATA:BEGIN */` / `/* FM_DATA:END */`
markers in index.html whenever data/cards.json or docs/guide/ changes.

Sources (read-only, never edited by this script):
  - "data/cards.json" (D7) -- 722 Yugipedia cards, the spine of the card
      table: number/name/slug/cardType/type/guardianStars/level/atk/def/
      password/starChipCost/lore/japaneseName/romajiName/obtainedBy.
      Supersedes the old docs/guide-mined number+name+ATK/DEF roster
      (D4's original source), which only covered 653 names and 98
      ATK/DEF pairs.
  - "Game Yu-Gi-Oh! Forbidden Memories Quân Bài Phụ trợ.md"
      #NNN <name> (<n> Equips) headers + their #NNN <item> lines -> 621
      per-monster equip lists, joined onto the data/cards.json spine by
      name (case-insensitive, via EQUIP_NAME_ALIASES for the handful of
      spellings docs/guide and Yugipedia disagree on).
  - "Game Yu-Gi-Oh! Forbidden Memories fusion.md"
      three fenced sections: "Dung hợp cơ bản" ([Type]+[Type] = Name
      (ATK/DEF Star/Star)), "Dung hợp chính xác" (Name + Name = Name), and
      "Dung hợp xung đột" (per-card fusion-system membership) -- carried
      through unchanged; only the fusion-system tags are joined onto the
      spine (by name, matches Yugipedia's spelling directly, no alias
      needed -- audited: 0 mismatches).
  - "data/lore-vi/part-1.json" .. "part-4.json" -- machine-translated
      Vietnamese lore keyed by card number (string), joined onto the spine
      as `loreVi` alongside the untouched English `lore`. A card with no
      translation gets `loreVi: null`, never an empty string. This text is
      a machine translation, not sourced from any Vietnamese original.

D4 (docs/history/fm-guide-site/CONTEXT.md): a field with no source is
`None` (-> JSON null). Never 0, never guessed. D7 keeps this rule, only
swaps the card table's source.

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
CARDS_JSON = REPO_ROOT / "data" / "cards.json"
LORE_VI_DIR = REPO_ROOT / "data" / "lore-vi"

EQUIP_FILE = GUIDE_DIR / "Game Yu-Gi-Oh! Forbidden Memories Quân Bài Phụ trợ.md"
FUSION_FILE = GUIDE_DIR / "Game Yu-Gi-Oh! Forbidden Memories fusion.md"
LORE_VI_FILES = [LORE_VI_DIR / f"part-{i}.json" for i in range(1, 5)]

# docs/guide's equip roster spells 15 names (13 monster headers, 2 equip
# items) differently than Yugipedia (data/cards.json). Fixed table, never
# fuzzy/prefix matching -- resolved by hand against data/cards.json for
# cell fm-guide-site-3. Keys are lowercased docs/guide spellings; values
# are the exact data/cards.json `name` to join against.
EQUIP_NAME_ALIASES = {
    "red eyes black dragon": "Red-eyes B. Dragon",
    "spirit of the book": "Spirit of the Books",
    "charubin the fire": "Charubin the Fire Knight",
    "blue eyes silver zombie": "Blue-eyed Silver Zombie",
    "black skull dragon": "B. Skull Dragon",
    "one who hunts soul": "One Who Hunts Souls",
    "blue eyes ultimate dragon": "Blue-eyes Ultimate Dragon",
    "stone dragon": "Stone D.",
    "millenium golem": "Millennium Golem",
    "kuwagata a": "Kuwagata α",
    "twin long rods #2": "Twin Long Rods 2",
    "performance of swords": "Performance of Sword",
    "meteor black dragon": "Meteor B. Dragon",
    "lazer cannon armor": "Laser Cannon Armor",
    "silver bow & arrow": "Silver Bow and Arrow",
}

EQUIP_HEADER_RE = re.compile(r'^#(\d+)\s+(.*?)\s*\(\s*(\d+)\s*Equips?\s*\)')
EQUIP_ITEM_RE = re.compile(r'^#(\d+)\s+(.+?)\s*$')
STAT_RE = re.compile(r'^([^()]+?)\s*\((\d+)/(\d+)\s+(\w+)/(\w+)\)\s*$')

# A stanza's general (top) line is almost always [Type] + [Type] = Result,
# but a handful pin a specific card on one side instead of a type (e.g.
# fusion.md:1580 "[Fiend] + Job-change Mirror = Summoned Skull") -- the
# same three side-forms parse_side() already accepts on the override line
# ([Type], a bare name, or a {set, of, names}). Audited against every '+'
# line in the "Dung hợp xung đột" section: exactly the lines containing
# both '+' and '=' are general lines (212/212, 0 ambiguous), so the sides
# are matched permissively (anything but '+'/'='/'<') rather than requiring
# brackets -- a stricter side-grammar would silently re-introduce the drop
# this regex exists to fix.
CONFLICT_TOP_HEADER_RE = re.compile(r'^\s*[^+=<]+\+[^+=<]+=.+$')


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


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
                # One item line (#668 Bright Castle, fusion.md-equivalent
                # of the #395 header bug above) has the block's closing
                # "===...===" separator glued onto the same line with no
                # whitespace in between, so the greedy-to-EOL item regex
                # swallows it into the name. Strip a glued trailing '='
                # run rather than treat it as part of the card name.
                iname = re.sub(r"=+$", "", iname).strip()
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
        GeneralLeft + GeneralRight = GeneralResult
        OverrideLeft + OverrideRight < OverrideResult
        LeftMember                       RightMember
        ...
    Each side of BOTH header lines is one of the same three forms:
    a `[Type]`, a bare card name, or a `{Name, Name}` set (e.g.
    fusion.md:1580 "[Fiend] + Job-change Mirror = Summoned Skull" has a
    name on the general line's right side, not a type) -- parsed by
    parse_side() and stored as {kind, value} on generalLeft/generalRight,
    same shape as overrideLeft/overrideRight. Columns are split on runs
    of 2+ spaces (never a fixed character width — long names such as
    "Wicked Dragon with the Ersatz Head" push the right column further
    out, see fusion.md:1072 and :3326).

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
                "generalLeft": parse_side(top_left),
                "generalRight": parse_side(top_right),
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

# Fields kept from data/cards.json onto the spine. Deliberately excludes
# `url`/`mainCardUrl`/`page`/`mainCardPage`/`file`: those are Yugipedia
# bookkeeping and the first two are live http(s) URLs -- embedding them in
# index.html's FM_DATA block would put a network-looking string in a page
# that D1/D2 require to have none, so they never leave this script.
SPINE_FIELDS = (
    "number", "name", "slug", "cardType", "type", "guardianStars", "level",
    "atk", "def", "password", "starChipCost", "lore", "japaneseName",
    "romajiName", "obtainedBy",
)


def load_spine_cards() -> list[dict]:
    """D7: the 722-card Yugipedia spine, read-only from data/cards.json.
    Field coverage per docs/history/fm-guide-site/CONTEXT.md: 621 monsters
    have type/guardianStars/level/atk/def, all 722 have lore, 698 have
    password/starChipCost, 640 have obtainedBy -- everywhere else is
    already `None` in the source file, so D4 ("missing is null, never 0")
    holds without any extra work here."""
    raw = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    return [{field: c[field] for field in SPINE_FIELDS} for c in raw["cards"]]


def load_lore_vi() -> dict[str, str]:
    """Merge data/lore-vi/part-1.json .. part-4.json into one {card number
    (str) -> Vietnamese lore} map. The four files together cover every card
    number exactly once (audited when the translation cells fm-guide-site-9
    .. -12 landed: no missing number, no key that isn't a real card, no
    empty value, no value identical to its English source) -- tools/check.py
    re-asserts that here rather than trusting the audit forever. This
    translation is machine-generated, never taken from any Vietnamese
    source text, and is always joined onto the spine alongside the original
    English `lore` field -- never replacing it."""
    merged: dict[str, str] = {}
    for path in LORE_VI_FILES:
        merged.update(json.loads(path.read_text(encoding="utf-8")))
    return merged


def extract_all() -> dict:
    numbered_names, equip_lists = parse_equip_file(read_lines(EQUIP_FILE))

    fusion_lines = read_lines(FUSION_FILE)
    # fusion_basic/fusion_exact/fusion_conflict/groups are carried through
    # unchanged (same column-splitting parse as before D7). atk_def_by_name
    # is no longer joined onto the card spine -- data/cards.json already
    # carries ATK/DEF for every monster -- so it is computed and dropped.
    fusion_basic, _atk_def_by_name = parse_fusion_basic(fusion_lines)
    fusion_exact = parse_fusion_exact(fusion_lines)
    fusion_conflict, groups, member_names = parse_fusion_conflict(fusion_lines)

    cards = load_spine_cards()
    cards_by_lower = {c["name"].lower(): c for c in cards}

    # Equip lists (621 monster headers mined from docs/guide) join onto the
    # spine by name, case-insensitive, resolving the 15 spots docs/guide
    # and Yugipedia disagree on spelling via EQUIP_NAME_ALIASES. A header
    # whose resolved name still has no spine card is a real gap, not a
    # ghost row -- surfaced in meta.equipNameMisses instead of silently
    # dropped or invented.
    equip_name_misses: list[str] = []
    for card in cards:
        card["equips"] = None
    for block in equip_lists:
        header_key = block["name"].strip().lower()
        yugipedia_name = EQUIP_NAME_ALIASES.get(header_key, block["name"])
        card = cards_by_lower.get(yugipedia_name.lower())
        if card is None:
            equip_name_misses.append(block["name"])
            continue
        card["equips"] = block["equips"]

    # Fusion-system tags ("Dung hợp xung đột" member names) already match
    # Yugipedia's spelling directly -- audited against the 722-card spine,
    # 0 mismatches -- so no alias table is needed on this side.
    name_to_tags: dict[str, set[str]] = {}
    for tag, names in groups.items():
        for nm in names:
            name_to_tags.setdefault(nm.lower(), set()).add(tag)
    for card in cards:
        tags = name_to_tags.get(card["name"].lower())
        card["fusionSystems"] = sorted(tags) if tags else None

    # Vietnamese lore (machine-translated, keyed by card number) joins onto
    # the spine as `loreVi`, alongside the untouched English `lore` field --
    # never replacing it. A card whose number has no translation gets
    # `None`, never an empty string (same D4 "missing is null" rule as
    # every other field here).
    lore_vi = load_lore_vi()
    for card in cards:
        card["loreVi"] = lore_vi.get(str(card["number"])) or None

    meta = {
        "totalCards": len(cards),
        "cardsWithAtkDef": sum(1 for c in cards if c["atk"] is not None),
        "cardsWithType": sum(1 for c in cards if c["type"] is not None),
        "cardsWithEquips": sum(1 for c in cards if c["equips"]),
        "cardsWithFusionSystems": sum(1 for c in cards if c["fusionSystems"]),
        "cardsWithLoreVi": sum(1 for c in cards if c["loreVi"]),
        "equipListsCount": len(equip_lists),
        "equipNameMisses": equip_name_misses,
        # Per-section recipe counts (tab "Độ phủ dữ liệu", cell fm-guide-site-5):
        # the tab reads these directly from meta instead of hardcoding the
        # numbers into index.html.
        "fusionBasicCount": len(fusion_basic),
        "fusionExactCount": len(fusion_exact),
        "fusionConflictCount": len(fusion_conflict),
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
        # Emitted for index.html's nameLinkHtml (cell fm-guide-site-5 rework):
        # the same EQUIP_NAME_ALIASES table used above to join docs/guide's
        # equip headers onto the spine, so a formula operand spelled the
        # docs/guide way (e.g. "Kuwagata a", "Twin Long Rods #2") still
        # resolves to its real spine card (#480 "Kuwagata α", #606 "Twin
        # Long Rods 2") instead of rendering as unlinked plain text. Single
        # source of truth -- never hand-copied into index.html.
        "nameAliases": dict(EQUIP_NAME_ALIASES),
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
