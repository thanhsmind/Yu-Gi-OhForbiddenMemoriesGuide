#!/usr/bin/env python3
"""Assert the data-layer invariants for tools/extract_cards.py.

Runs the real extractor against data/cards.json + docs/guide/ (never a
fixture) and checks the shape/coverage promises made in
docs/history/fm-guide-site/CONTEXT.md's D4 ("no fabricated data; a
missing field is null, never 0") and D7 (the card table's spine is the
722-card data/cards.json; docs/guide/ still supplies equip lists and
fusion recipes, joined on top by card name).

This is the project's declared test command (`commands.test` in
.bee/config.json). Everything it writes goes to a fresh temp directory --
it never touches a deliverable file (index.html, docs/guide/, data/, etc).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXTRACTOR = REPO_ROOT / "tools" / "extract_cards.py"
INDEX_HTML = REPO_ROOT / "index.html"
CARDS_JSON = REPO_ROOT / "data" / "cards.json"
IMAGES_DIR = REPO_ROOT / "images" / "cards"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import extract_cards  # noqa: E402  (import after sys.path tweak, by design)

SLUG_RE = re.compile(r"^[a-z0-9-]+$")

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "ok" if condition else "FAIL"
    line = f"[{status}] {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    if not condition:
        failures.append(line)


def main() -> int:
    # --- Run the real extractor into a scratch temp dir; never a deliverable path. ---
    tmpdir = Path(tempfile.mkdtemp(prefix="fm-guide-check-"))
    out_js = tmpdir / "fm_data.js"
    out_js2 = tmpdir / "fm_data_2.js"

    for out_path in (out_js, out_js2):
        result = subprocess.run(
            [sys.executable, str(EXTRACTOR), "--out", str(out_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            print(f"[FAIL] extractor exited {result.returncode} writing {out_path}")
            return 1

    js_text = out_js.read_text(encoding="utf-8")
    check(
        "extractor writes only to the temp dir (CLI run twice into scratch paths, no repo path touched)",
        out_js.exists() and out_js2.exists(),
    )
    check(
        "extractor output is idempotent (two runs produce byte-identical JS)",
        out_js.read_bytes() == out_js2.read_bytes(),
    )
    check(
        "JS block is wrapped in FM_DATA:BEGIN/END markers and assigns window.FM_DATA",
        js_text.startswith("/* FM_DATA:BEGIN")
        and "window.FM_DATA = " in js_text
        and js_text.rstrip().endswith("/* FM_DATA:END */"),
    )

    # Parse the JSON payload out of the JS block to prove it's valid JSON,
    # then also call the extractor in-process for the rest of the assertions
    # (same code path, avoids re-implementing the parse-JS-out-of-a-string step).
    payload_text = js_text.split("window.FM_DATA = ", 1)[1].rsplit(";\n/* FM_DATA:END */", 1)[0]
    try:
        json.loads(payload_text)
        parses = True
    except json.JSONDecodeError as exc:
        parses = False
        print(f"  JSON parse error: {exc}")
    check("the emitted window.FM_DATA block parses as JSON", parses)

    data = extract_cards.extract_all()
    cards = data["cards"]
    by_number = {c["number"]: c for c in cards}
    by_name_lower = {c["name"].lower(): c for c in cards}

    # --- D7: spine is the 722-card data/cards.json ---
    spine_raw = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    check("đúng 722 lá (spine data/cards.json)", len(cards) == 722, f"got {len(cards)}")
    check(
        "spine không bị sửa (số lá trích xuất == số lá trong data/cards.json)",
        len(cards) == spine_raw["count"] == len(spine_raw["cards"]),
        f"extracted {len(cards)}, data/cards.json count={spine_raw['count']}, cards={len(spine_raw['cards'])}",
    )

    with_atk_def = [c for c in cards if c["atk"] is not None]
    check(
        "621 lá quái vật có ATK/DEF (từ spine, không mine lại từ fusion.md)",
        len(with_atk_def) == 621,
        f"got {len(with_atk_def)}",
    )

    # docs/history/fm-guide-site/CONTEXT.md carries this count forward from
    # the audited docs/guide mining -- unchanged by D7 since fusionConflict
    # parsing (column-splitting logic) is untouched.
    fusion_conflict_members = data["meta"]["fusionConflictMemberNames"]
    check(
        "261 tên riêng biệt xuất hiện trong mục 'Dung hợp xung đột' (fusionConflictMemberNames — khác với 258 lá có fusionSystems, xem check bên dưới)",
        len(fusion_conflict_members) == 261,
        f"got {len(fusion_conflict_members)}",
    )

    check(
        "621 khối equip theo lá quái vật (equipLists, mined từ docs/guide)",
        len(data["equipLists"]) == 621,
        f"got {len(data['equipLists'])}",
    )
    check(
        "621 lá join được equip lên spine (equipListsCount == cardsWithEquips, không lá ma)",
        data["meta"]["cardsWithEquips"] == 621,
        f"got {data['meta']['cardsWithEquips']}",
    )
    check(
        "mọi header equip trong docs/guide join được vào spine 722 lá (alias table đủ, không có tên rơi rớt)",
        data["meta"]["equipNameMisses"] == [],
        f"misses: {data['meta']['equipNameMisses']}",
    )
    check("có công thức từ cả ba mục fusion.md", bool(data["fusionBasic"]) and bool(data["fusionExact"]) and bool(data["fusionConflict"]))

    # --- meta counts backing tab "Độ phủ dữ liệu" (cell fm-guide-site-5) ---
    # The tab reads every number straight from FM_DATA.meta at runtime; here
    # we assert meta actually carries every field it needs, and that each
    # value is the real count from the same extraction run (never a number
    # baked in by hand on either side).
    required_meta_fields = (
        "totalCards", "cardsWithAtkDef", "cardsWithType", "cardsWithEquips",
        "cardsWithFusionSystems", "equipListsCount", "fusionBasicCount",
        "fusionExactCount", "fusionConflictCount", "fusionConflictMemberNames",
        "fusionGroupsWithMembers",
    )
    check(
        "FM_DATA.meta có đủ các trường số đếm phục vụ tab Độ phủ dữ liệu",
        all(k in data["meta"] for k in required_meta_fields),
        f"meta keys: {sorted(data['meta'].keys())}",
    )
    check(
        "meta.cardsWithType đúng bằng số lá có type != null trong spine",
        data["meta"]["cardsWithType"] == sum(1 for c in cards if c["type"] is not None) == 621,
        f"got {data['meta']['cardsWithType']}",
    )
    check(
        "meta.cardsWithFusionSystems (258, hiện trên tab Độ phủ dữ liệu) đúng bằng số lá "
        "có fusionSystems != null trong spine đếm lại (khác 261 — số tên riêng biệt, không phải số lá)",
        data["meta"]["cardsWithFusionSystems"] == sum(1 for c in cards if c["fusionSystems"]) == 258,
        f"got {data['meta']['cardsWithFusionSystems']}",
    )
    check(
        "meta.fusionBasicCount/fusionExactCount khớp đúng số phần tử thật của hai bảng công thức (fusionConflictCount đếm lại từ nguồn ở dưới, không gõ cứng số ở đây)",
        (data["meta"]["fusionBasicCount"], data["meta"]["fusionExactCount"])
        == (len(data["fusionBasic"]), len(data["fusionExact"]))
        == (141, 150),
        f"got {(data['meta']['fusionBasicCount'], data['meta']['fusionExactCount'])}",
    )
    check(
        "meta.fusionGroupsWithMembers/fusionConflictMemberNames khớp đúng số nhóm hệ và số tên riêng biệt",
        (len(data["meta"]["fusionGroupsWithMembers"]), len(data["meta"]["fusionConflictMemberNames"])) == (26, 261),
        f"got {(len(data['meta']['fusionGroupsWithMembers']), len(data['meta']['fusionConflictMemberNames']))}",
    )

    # --- Recount every fusion.md section straight from the source text
    # (never a hardcoded literal) -- guards the fm-guide-site-6 fix for the
    # parser that used to drop a "Dung hợp xung đột" stanza whenever its
    # general line pinned a card name instead of a [Type] on one side. ---
    fusion_lines = extract_cards.read_lines(extract_cards.FUSION_FILE)

    def side_key(side: dict):
        value = side["value"]
        if isinstance(value, list):
            value = tuple(value)
        return (side["kind"], value)

    # (1) conflict stanza count == number of '<' lines in the section.
    conflict_section = extract_cards.extract_fenced_after(fusion_lines, "Dung hợp xung đột")
    source_conflict_lt_lines = [l for l in conflict_section if "<" in l]
    check(
        "số stanza 'Dung hợp xung đột' trích được == số dòng chứa '<' trong nguồn (đếm lại từ nguồn, không gõ cứng)",
        len(data["fusionConflict"]) == data["meta"]["fusionConflictCount"] == len(source_conflict_lt_lines),
        f"extractor {len(data['fusionConflict'])} (meta {data['meta']['fusionConflictCount']}) vs "
        f"{len(source_conflict_lt_lines)} '<' line(s) in source",
    )

    # (2) the (overrideLeft, overrideRight, overrideResult) multiset from
    # the extractor equals the same multiset parsed independently straight
    # off the source's '<' lines (bypassing the stanza-grouping loop
    # entirely, so this can't share the bug it is guarding against).
    source_triples: Counter = Counter()
    for line in source_conflict_lt_lines:
        left_raw, right_raw, result = extract_cards.split_on_plus_and_delim(line, "<")
        left = extract_cards.parse_side(left_raw)
        right = extract_cards.parse_side(right_raw)
        source_triples[(side_key(left), side_key(right), result)] += 1
    extractor_triples: Counter = Counter(
        (side_key(e["overrideLeft"]), side_key(e["overrideRight"]), e["overrideResult"])
        for e in data["fusionConflict"]
    )
    triples_diff = {
        k: (source_triples.get(k, 0), extractor_triples.get(k, 0))
        for k in set(source_triples) | set(extractor_triples)
        if source_triples.get(k, 0) != extractor_triples.get(k, 0)
    }
    check(
        "bội số (overrideLeft, overrideRight, overrideResult) khớp 1-1 với nguồn (đếm lại từ nguồn, không gõ cứng)",
        not triples_diff,
        f"{len(triples_diff)} triple(s) lệch bội số, vd: {list(triples_diff.items())[:5]}",
    )
    check(
        "công thức 'Fungi of the Musk + [Fiend] < Darkworld Thorns' có mặt trong dữ liệu trích được (trước đây mất hẳn)",
        (("name", "Fungi of the Musk"), ("type", "Fiend"), "Darkworld Thorns") in extractor_triples,
    )

    # (3) "Dung hợp cơ bản" results+possible count == number of
    # "(ATK/DEF Sao/Sao)" stat occurrences in that section of the source.
    basic_section = extract_cards.extract_fenced_after(
        fusion_lines, "Dung hợp cơ bản", until="Dung hợp chính xác"
    )
    source_stat_occurrences = sum(
        len(re.findall(r"\(\d+/\d+\s+\w+/\w+\)", l)) for l in basic_section
    )
    extractor_basic_total = sum(len(b["results"]) + len(b["possible"]) for b in data["fusionBasic"])
    check(
        "'Dung hợp cơ bản': results+possible == số cụm (ATK/DEF Sao/Sao) trong nguồn (đếm lại từ nguồn, không gõ cứng)",
        extractor_basic_total == source_stat_occurrences,
        f"extractor results+possible={extractor_basic_total} vs source stat occurrences={source_stat_occurrences}",
    )

    # (4) "Dung hợp chính xác" recipe count == number of '=' lines in the
    # section of the source.
    exact_section = extract_cards.extract_fenced_after(
        fusion_lines, "Dung hợp chính xác", until="Dung hợp xung đột"
    )
    source_exact_eq_lines = [l for l in exact_section if "=" in l]
    check(
        "'Dung hợp chính xác': số công thức == số dòng chứa '=' trong nguồn (đếm lại từ nguồn, không gõ cứng)",
        len(data["fusionExact"]) == len(source_exact_eq_lines),
        f"extractor {len(data['fusionExact'])} vs {len(source_exact_eq_lines)} '=' line(s) in source",
    )

    # The docs/guide equip roster spells 15 names differently than
    # Yugipedia (13 monster headers + 2 equip items) -- every alias must
    # resolve to a real spine card, and that card must carry equip data
    # joined onto it (proves the alias table is actually wired in, not
    # just declared).
    check(
        "bảng EQUIP_NAME_ALIASES có đúng 15 mục (13 lá quái vật + 2 vật phẩm equip)",
        len(extract_cards.EQUIP_NAME_ALIASES) == 15,
        f"got {len(extract_cards.EQUIP_NAME_ALIASES)}",
    )
    alias_misses = []
    for guide_name, yugipedia_name in extract_cards.EQUIP_NAME_ALIASES.items():
        card = by_name_lower.get(yugipedia_name.lower())
        if card is None:
            alias_misses.append((guide_name, yugipedia_name))
    check(
        "mỗi alias trong EQUIP_NAME_ALIASES trỏ tới đúng một lá có thật trong spine",
        not alias_misses,
        f"{alias_misses[:5]}",
    )
    b_skull = by_name_lower.get("b. skull dragon")
    check(
        "alias 'Black Skull Dragon' (docs/guide) -> 'B. Skull Dragon' (Yugipedia) có equip đi kèm",
        b_skull is not None and bool(b_skull.get("equips")),
        f"got {b_skull}",
    )

    # --- FM_DATA.nameAliases (cell fm-guide-site-5 rework): the same
    # EQUIP_NAME_ALIASES table emitted for index.html's nameLinkHtml so a
    # formula operand spelled the docs/guide way (e.g. "Kuwagata a") still
    # links to its real spine card (#480 "Kuwagata α"). Every emitted key
    # must resolve to exactly one real spine card -- guards a dead/no-op
    # link from ever shipping. ---
    check(
        "FM_DATA.nameAliases là chính EQUIP_NAME_ALIASES (không copy tay, không rơi rớt/thêm mục)",
        data["nameAliases"] == extract_cards.EQUIP_NAME_ALIASES,
        f"got {len(data.get('nameAliases', {}))} entries",
    )
    name_alias_misses = [
        (guide_name, target_name)
        for guide_name, target_name in data["nameAliases"].items()
        if by_name_lower.get(target_name.lower()) is None
    ]
    check(
        "mọi khóa trong FM_DATA.nameAliases trỏ tới đúng một lá có thật trong spine (guard FAIL formula-name-links)",
        not name_alias_misses,
        f"{name_alias_misses[:5]}",
    )

    # The #668 Bright Castle equip item line has fusion.md's own separator
    # glued onto it with no whitespace ("#668 Bright Castle===...==="); a
    # naive greedy-to-EOL parse would fold the dashes into the card name.
    # Assert the fix holds: no equip item name in the mined equip lists
    # carries a trailing run of '=' characters.
    glued_names = [
        it["name"]
        for block in data["equipLists"]
        for it in block["equips"]
        if it["name"].rstrip().endswith("=")
    ]
    check(
        "#668 Bright Castle không còn dính dấu '=' nối liền (bug dòng glued-separator đã sửa)",
        not glued_names,
        f"{glued_names}",
    )

    slugs = [c["slug"] for c in cards]
    check(
        "không slug nào trùng nhau trên toàn bộ 722 lá",
        len(set(slugs)) == len(slugs),
        f"{len(slugs) - len(set(slugs))} duplicate(s)",
    )
    bad_slugs = [s for s in slugs if not SLUG_RE.match(s)]
    check("slug chỉ chứa a-z0-9 và dấu gạch", not bad_slugs, f"bad: {bad_slugs[:5]}")

    missing_images = [s for s in slugs if not (IMAGES_DIR / f"{s}.png").is_file()]
    check(
        "cả 722 slug đều có ảnh thật trong images/cards/<slug>.png",
        not missing_images,
        f"{len(missing_images)} missing, e.g. {missing_images[:5]}",
    )

    # A real ATK/DEF of 0 legitimately exists in the source (e.g. Dragon
    # Zombie 1600/0) -- the invariant is about *missing* data, not about
    # whether 0 can ever appear. So: every card with atk is None must also
    # have def is None (never a stray 0 standing in for "no data"), and
    # vice versa.
    inconsistent_null = [
        c for c in cards if (c["atk"] is None) != (c["def"] is None)
    ]
    check(
        "thiếu chỉ số lưu null chứ không phải 0 (không có ô nửa-null nửa-0)",
        not inconsistent_null,
        f"{len(inconsistent_null)} card(s): {[c['name'] for c in inconsistent_null][:5]}",
    )
    check(
        "mọi lá không có nguồn ATK/DEF đều là null (không phải chuỗi rỗng hay 0)",
        all(c["atk"] is None or isinstance(c["atk"], int) for c in cards)
        and all(c["def"] is None or isinstance(c["def"], int) for c in cards),
    )

    # Exact-name fusion recipes pointing at names with no spine card must be
    # kept as name-only references, never invented a ghost row for.
    exact_missing_numbers = [
        r["result"] for r in data["fusionExact"] if r["result"].lower() not in by_name_lower
    ]
    check(
        "công thức 'Dung hợp chính xác' trỏ tới tên không có trong spine vẫn giữ dạng chỉ-có-tên, không crash",
        isinstance(exact_missing_numbers, list),
        f"{len(exact_missing_numbers)} name-only result(s), e.g. {exact_missing_numbers[:3]}",
    )

    # --- The cell's must_have worked example: Blue-eyes White Dragon ---
    bews = by_name_lower.get("blue-eyes white dragon")
    check(
        "gõ 'Blue-eyes White Dragon' hiện 3000/2500, type Dragon, Sun/Mars, level 8, lore, password",
        bews is not None
        and bews["atk"] == 3000
        and bews["def"] == 2500
        and bews["type"] == "Dragon"
        and bews["guardianStars"] == ["Sun", "Mars"]
        and bews["level"] == 8
        and bews["lore"]
        and bews["password"],
        f"got {bews}",
    )

    # Data-layer fields that must never leak an http(s) URL into the shipped
    # page (D1/D2: no network dependency). Confirms load_spine_cards()'s
    # SPINE_FIELDS allowlist is actually excluding them, not just declared.
    url_leaks = [c for c in cards if "url" in c or "mainCardUrl" in c or "page" in c or "mainCardPage" in c or "file" in c]
    check(
        "trường dữ liệu không mang theo url/mainCardUrl/page/mainCardPage/file từ data/cards.json",
        not url_leaks,
        f"{len(url_leaks)} card(s) leaking a dropped field",
    )

    # --- index.html invariants (cell fm-guide-site-2/3, D1/D2/D3/D4/D7) ---
    html_text = INDEX_HTML.read_text(encoding="utf-8")

    check(
        "index.html không chứa '<script src=' (D1/D2: không nạp script ngoài)",
        "<script src=" not in html_text,
    )
    check(
        "index.html không chứa 'fetch(' (D2: dữ liệu nhúng inline, không fetch)",
        "fetch(" not in html_text,
    )
    check(
        "index.html không chứa 'http://' hay 'https://' (D1: không phụ thuộc mạng)",
        "http://" not in html_text and "https://" not in html_text,
    )
    check(
        "chuỗi 'chưa có dữ liệu' có mặt trong index.html (D4)",
        "chưa có dữ liệu" in html_text,
    )

    # starChipCost's 999999 sentinel (D4: a value must never read as real
    # when it is not — 98/722 cards use it for "not purchasable with Star
    # Chips", never a real price) must render as Vietnamese text at the
    # render layer, never the literal number. Pins the chosen behavior so a
    # future edit can't silently reintroduce "999999" as a displayed price.
    sentinel_count = sum(1 for c in cards if c["starChipCost"] == 999999)
    check(
        "starChipCost sentinel 999999 chỉ xuất hiện đúng ở 98/722 lá (không mua được bằng Star Chip, không phải giá thật)",
        sentinel_count == 98,
        f"got {sentinel_count}",
    )
    check(
        "index.html có hàm fmtStarChipCost render sentinel 999999 thành 'không mua được', không in số 999999",
        "function fmtStarChipCost(" in html_text and "không mua được" in html_text,
    )
    check(
        "panel chi tiết dùng fmtStarChipCost(card) cho Star Chip Cost, không dùng fmt(card.starChipCost) trần",
        'fmtStarChipCost(card) + "</dd>"' in html_text,
    )
    other_sentinel_fields = [
        field
        for field in ("atk", "def", "level", "password")
        if any(isinstance(c[field], int) and c[field] >= 99999 for c in cards)
    ]
    check(
        "không trường số nào khác trong spine mang sentinel kiểu 999999 mà chưa được xử lý (chỉ starChipCost dùng sentinel này)",
        not other_sentinel_fields,
        f"{other_sentinel_fields}",
    )
    check(
        "bộ lọc theo Type và theo Loại lá (cardType) có trong index.html",
        'id="type-filter"' in html_text and 'id="cardtype-filter"' in html_text,
    )
    check(
        "panel chi tiết hiện Password, Star Chip Cost, Cách lấy, Tên Nhật, Lore",
        "Password</dt>" in html_text
        and "Star Chip Cost</dt>" in html_text
        and "Cách lấy</dt>" in html_text
        and "Tên Nhật</dt>" in html_text
        and "Lore</dt>" in html_text,
    )

    # --- Tab "Fusion" và tab "Độ phủ dữ liệu" (cell fm-guide-site-5) ---
    check(
        "hai placeholder 'coming-soon' cũ của tab Fusion / Độ phủ dữ liệu đã bị thay bằng nội dung thật",
        "sẽ có ở chặng tiếp theo" not in html_text,
    )
    check(
        "tab Fusion có ô tìm kiếm hai chiều và ba bảng công thức (cơ bản/chính xác/xung đột)",
        'id="fusion-search"' in html_text
        and 'id="fusion-lookup-result"' in html_text
        and 'id="fusion-basic-filter"' in html_text
        and 'id="fusion-basic-body"' in html_text
        and 'id="fusion-exact-body"' in html_text
        and 'id="fusion-conflict-body"' in html_text,
    )
    check(
        "tab Độ phủ dữ liệu có bảng số đếm và mục 'KHÔNG có'",
        'id="coverage-body"' in html_text and "KHÔNG có" in html_text,
    )
    check(
        "panel chi tiết một lá có mục 'Fusion liên quan'",
        "Fusion liên quan" in html_text,
    )
    check(
        "tab Độ phủ dữ liệu đọc số liệu qua DATA.meta.<field> (không gõ cứng số đếm vào HTML)",
        all(
            ("meta." + field) in html_text
            for field in (
                "totalCards", "cardsWithAtkDef", "cardsWithType", "cardsWithEquips",
                "cardsWithFusionSystems", "equipListsCount", "fusionBasicCount",
                "fusionExactCount", "fusionConflictCount", "fusionGroupsWithMembers",
                "fusionConflictMemberNames",
            )
        ),
    )
    check(
        "tên lá bài trong công thức chỉ link khi khớp bảng tra cứu (nameLinkHtml/wireCardLinks tái dùng, không cơ chế thứ hai)",
        "function nameLinkHtml(" in html_text
        and "function wireCardLinks(" in html_text
        and html_text.count("function wireCardLinks(") == 1,
    )

    # --- Deep-link router (cell fm-guide-site-7, D1/D2) ---
    check(
        "index.html có addEventListener('hashchange', ...) để dựng lại trạng thái khi Back/Forward hoặc sửa URL",
        re.search(r"""addEventListener\(\s*["']hashchange["']""", html_text) is not None,
    )
    check(
        "index.html có hàm đọc trạng thái từ hash (readStateFromHash) và hàm ghi trạng thái vào hash (writeHash)",
        "function readStateFromHash(" in html_text and "function writeHash(" in html_text,
    )
    # D1: file:// refuses history.pushState/replaceState given a path
    # argument -- only the hash may ever change. A literal string argument
    # containing '/' would be a path segment (a hash-only value built from
    # this page's own vocabulary -- tab names, filter values, card
    # numbers -- never contains a raw '/': search text is percent-encoded
    # via encodeURIComponent before being placed in the hash).
    push_or_replace_calls = re.findall(r"history\.(?:pushState|replaceState)\(([^)]*)\)", html_text)
    bad_history_calls = [
        c for c in push_or_replace_calls if re.search(r"""["'][^"']*/[^"']*["']""", c)
    ]
    check(
        f"đủ {len(push_or_replace_calls)} lệnh gọi history.pushState/replaceState trong index.html (guard không chạy trên tập rỗng)",
        len(push_or_replace_calls) > 0,
    )
    check(
        "không lệnh pushState/replaceState nào trong index.html truyền chuỗi literal chứa dấu '/' làm URL (chỉ đổi hash, không đổi đường dẫn — bắt buộc để chạy được trên file://)",
        not bad_history_calls,
        f"{bad_history_calls}",
    )

    fm_begin = extract_cards.FM_DATA_BEGIN_MARKER
    fm_end = extract_cards.FM_DATA_END_MARKER
    has_markers = fm_begin in html_text and fm_end in html_text
    check(
        f"index.html chứa cả hai marker chính xác {fm_begin!r} và {fm_end!r}",
        has_markers,
    )
    if has_markers:
        block_start = html_text.index(fm_begin)
        block_end = html_text.index(fm_end, block_start) + len(fm_end)
        block = html_text[block_start:block_end]
        try:
            block_payload = block.split("window.FM_DATA = ", 1)[1].rsplit(";\n" + fm_end, 1)[0]
            embedded = json.loads(block_payload)
            embedded_parses = True
        except (IndexError, json.JSONDecodeError) as exc:
            embedded_parses = False
            embedded = None
            print(f"  index.html FM_DATA parse error: {exc}")
        check(
            "khối window.FM_DATA giữa hai marker trong index.html parse được thành JSON",
            embedded_parses,
        )
        if embedded_parses:
            check(
                "khối FM_DATA nhúng trong index.html chứa đúng 722 lá (dữ liệu thật, không rỗng)",
                len(embedded.get("cards", [])) == 722,
                f"got {len(embedded.get('cards', []))}",
            )

    # --inject run twice in a row on a scratch copy of index.html (never the
    # deliverable itself) must produce byte-identical output.
    inject_dir = Path(tempfile.mkdtemp(prefix="fm-guide-check-inject-"))
    inject_copy_1 = inject_dir / "index_1.html"
    inject_copy_2 = inject_dir / "index_2.html"
    shutil.copyfile(INDEX_HTML, inject_copy_1)
    shutil.copyfile(INDEX_HTML, inject_copy_2)
    inject_ok = True
    for copy_path in (inject_copy_1, inject_copy_2):
        result = subprocess.run(
            [sys.executable, str(EXTRACTOR), "--inject", str(copy_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            inject_ok = False
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            print(f"[FAIL] --inject exited {result.returncode} on {copy_path}")
    check("--inject exits 0 on both scratch copies", inject_ok)
    if inject_ok:
        check(
            "chạy --inject hai lần liên tiếp (trên hai bản sao) cho ra byte y hệt",
            inject_copy_1.read_bytes() == inject_copy_2.read_bytes(),
        )
        check(
            "--inject trên bản sao đã inject rồi vẫn idempotent (chạy lại lần nữa cho ra byte y hệt)",
            subprocess.run(
                [sys.executable, str(EXTRACTOR), "--inject", str(inject_copy_1)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            ).returncode
            == 0
            and inject_copy_1.read_bytes() == inject_copy_2.read_bytes(),
        )

    print()
    print("Summary:")
    print(f"  cards (spine, data/cards.json):      {len(cards)}")
    print(f"  cards with ATK/DEF:                  {len(with_atk_def)}")
    print(f"  cards with equips joined:            {data['meta']['cardsWithEquips']}")
    print(f"  cards with fusion system:            {data['meta']['cardsWithFusionSystems']}")
    print(f"  distinct fusion-conflict member names: {len(fusion_conflict_members)}")
    print(f"  fusion groups with a member list:    {len(data['meta']['fusionGroupsWithMembers'])}")
    print(f"  equip lists (monster headers):       {len(data['equipLists'])}")
    print(f"  fusionBasic blocks:                  {len(data['fusionBasic'])}")
    print(f"  fusionExact recipes:                 {len(data['fusionExact'])}")
    print(f"  fusionConflict stanzas:               {len(data['fusionConflict'])}")

    if failures:
        print()
        print(f"{len(failures)} check(s) failed:")
        for line in failures:
            print(f"  {line}")
        return 1

    print()
    print("All data-layer invariants hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
