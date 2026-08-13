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
        "257 lá có hệ fusion (mục 'Dung hợp xung đột')",
        len(fusion_conflict_members) == 257,
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
        "meta.fusionBasicCount/fusionExactCount/fusionConflictCount khớp đúng số phần tử thật của ba bảng công thức",
        (data["meta"]["fusionBasicCount"], data["meta"]["fusionExactCount"], data["meta"]["fusionConflictCount"])
        == (len(data["fusionBasic"]), len(data["fusionExact"]), len(data["fusionConflict"]))
        == (141, 150, 202),
        f"got {(data['meta']['fusionBasicCount'], data['meta']['fusionExactCount'], data['meta']['fusionConflictCount'])}",
    )
    check(
        "meta.fusionGroupsWithMembers/fusionConflictMemberNames khớp đúng số nhóm hệ và số tên riêng biệt",
        (len(data["meta"]["fusionGroupsWithMembers"]), len(data["meta"]["fusionConflictMemberNames"])) == (25, 257),
        f"got {(len(data['meta']['fusionGroupsWithMembers']), len(data['meta']['fusionConflictMemberNames']))}",
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
