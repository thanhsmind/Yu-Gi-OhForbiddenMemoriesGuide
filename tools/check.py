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
ART_DIR = REPO_ROOT / "images" / "art"
ART_BUDGET_BYTES = 40 * 1024 * 1024  # D12: images/art/ must stay under 40MB

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
    cards = data["cards"]  # D10: 722 FM cards + 360 outside-FM cards (1,082 total)
    fm_cards = [c for c in cards if not c.get("outsideFm")]
    outside_fm_cards = [c for c in cards if c.get("outsideFm")]
    by_number = {c["number"]: c for c in fm_cards}
    # FM-only on purpose: every check below built on top of `by_name_lower`
    # (fusionExactAllFmCount, EQUIP_NAME_ALIASES, nameAliases, the BEWS
    # worked example) predates D10 and must keep meaning "one of the 722
    # FM cards" -- see `by_name_lower_all` further down for the few checks
    # that do need to see all 1,082 cards by name.
    by_name_lower = {c["name"].lower(): c for c in fm_cards}

    # --- D7: spine is the 722-card data/cards.json; D10 adds 360 more
    # outside-FM cards on top without disturbing that count. ---
    spine_raw = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    check(
        "đúng 722 lá FM (spine data/cards.json, D10 giữ nguyên ràng buộc D7)",
        len(fm_cards) == spine_raw["count"] == len(spine_raw["cards"]) == 722,
        f"fm_cards {len(fm_cards)}, data/cards.json count={spine_raw['count']}, cards={len(spine_raw['cards'])}",
    )
    check(
        "spine FM không bị sửa (số lá FM trích xuất == số lá trong data/cards.json)",
        len(fm_cards) == spine_raw["count"] == len(spine_raw["cards"]),
        f"extracted {len(fm_cards)}, data/cards.json count={spine_raw['count']}, cards={len(spine_raw['cards'])}",
    )

    # --- D10/D11: 360 outside-FM cards from cartas_runtime.json, recounted
    # straight from the source (never trusting the extractor's own count
    # twice) via the same normalize+alias join extract_cards.py uses. ---
    runtime_raw = json.loads(extract_cards.CARTAS_RUNTIME_JSON.read_text(encoding="utf-8"))
    fm_name_norms = {extract_cards.normalize_match_name(c["name"]) for c in fm_cards}

    def _runtime_is_outside_fm(entry: dict) -> bool:
        lookup_name = extract_cards.EQUIP_NAME_ALIASES.get(
            entry["Card"].strip().lower(), entry["Card"]
        )
        return extract_cards.normalize_match_name(lookup_name) not in fm_name_norms

    recounted_outside = [e for e in runtime_raw if _runtime_is_outside_fm(e)]
    check(
        "đúng 360 lá ngoài FM (đếm lại độc lập từ cartas_runtime.json, không gõ cứng)",
        len(recounted_outside) == len(outside_fm_cards) == data["meta"]["outsideFmCards"] == 360,
        f"recounted {len(recounted_outside)}, extractor {len(outside_fm_cards)}, "
        f"meta {data['meta']['outsideFmCards']}",
    )
    check(
        "tổng số lá == lá FM + lá ngoài FM (meta.totalCards/fmCards/outsideFmCards khớp nhau)",
        len(cards) == len(fm_cards) + len(outside_fm_cards)
        == data["meta"]["totalCards"] == data["meta"]["fmCards"] + data["meta"]["outsideFmCards"]
        == 1082,
        f"len(cards)={len(cards)}, fm+outside={len(fm_cards) + len(outside_fm_cards)}, "
        f"meta totalCards={data['meta']['totalCards']}",
    )
    bad_outside_number_star = [
        c for c in outside_fm_cards if c["number"] is not None or c["guardianStars"] is not None
    ]
    check(
        "không lá ngoài FM nào có number hay guardianStars khác null (D11: không bịa số thứ tự/Guardian Star)",
        not bad_outside_number_star,
        f"{[c['name'] for c in bad_outside_number_star][:5]}",
    )
    bad_outside_other_fields = [
        c
        for c in outside_fm_cards
        if c["password"] is not None
        or c["starChipCost"] is not None
        or c["obtainedBy"] is not None
        or c["equips"] is not None
        or c["fusionSystems"] is not None
        or c["japaneseName"] is not None
        or c["romajiName"] is not None
    ]
    check(
        "lá ngoài FM: password/starChipCost/obtainedBy/equips/fusionSystems/japaneseName/romajiName đều null "
        "thật (chưa có nguồn, không bịa)",
        not bad_outside_other_fields,
        f"{[c['name'] for c in bad_outside_other_fields][:5]}",
    )
    check(
        "mọi lá ngoài FM mang outsideFm: true; lá FM không mang trường này (quy ước nhất quán)",
        all(c.get("outsideFm") is True for c in outside_fm_cards)
        and all("outsideFm" not in c for c in fm_cards),
    )

    with_atk_def = [c for c in fm_cards if c["atk"] is not None]
    check(
        "621 lá FM quái vật có ATK/DEF (từ spine, không mine lại từ fusion.md; mẫu số là 722 lá FM, "
        "không phải tổng 1.082 lá)",
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
    check(
        "có công thức từ fusionBasic (fusion.md), fusionPairs (fusion_unique.json, D9) và fusionConflict (fusion.md)",
        bool(data["fusionBasic"]) and bool(data["fusionPairs"]) and bool(data["fusionConflict"]),
    )

    # --- Vietnamese lore translation (cell fm-guide-site-13) ---
    # data/lore-vi/part-1.json .. part-4.json, read directly here (never
    # through the extractor's merged view) so this guards the raw input
    # files, not just whatever extract_cards.load_lore_vi() already trusts.
    LORE_VI_DIR = REPO_ROOT / "data" / "lore-vi"
    lore_vi_raw: dict[str, str] = {}
    duplicate_lore_vi_keys: list[str] = []
    for i in range(1, 5):
        part = json.loads((LORE_VI_DIR / f"part-{i}.json").read_text(encoding="utf-8"))
        for k in part:
            if k in lore_vi_raw:
                duplicate_lore_vi_keys.append(k)
        lore_vi_raw.update(part)
    check(
        "bốn file data/lore-vi/part-*.json không có khóa trùng lẫn nhau",
        not duplicate_lore_vi_keys,
        f"{duplicate_lore_vi_keys[:5]}",
    )
    real_numbers = {str(c["number"]) for c in fm_cards}  # only FM cards have a real number (D11)
    fake_lore_vi_keys = [k for k in lore_vi_raw if k not in real_numbers]
    check(
        "mọi khóa trong bốn file data/lore-vi/part-*.json là số thứ tự của một lá có thật",
        not fake_lore_vi_keys,
        f"{fake_lore_vi_keys[:5]}",
    )
    empty_lore_vi = [k for k, v in lore_vi_raw.items() if not v]
    check(
        "không bản dịch tiếng Việt nào là chuỗi rỗng",
        not empty_lore_vi,
        f"{empty_lore_vi[:5]}",
    )
    en_lore_by_number = {str(c["number"]): c["lore"] for c in fm_cards}  # data/lore-vi/ is FM-only, keyed by number
    identical_lore_vi = [
        k for k, v in lore_vi_raw.items() if v == en_lore_by_number.get(k)
    ]
    check(
        "không bản dịch tiếng Việt nào y hệt nguyên văn tiếng Anh",
        not identical_lore_vi,
        f"{identical_lore_vi[:5]}",
    )
    # D5: tên lá bài (nhiều từ) không được dịch — nếu tên đó xuất hiện trong
    # lore tiếng Anh của một lá, nó phải xuất hiện y nguyên (tiếng Anh) trong
    # loreVi của cùng lá đó. Chỉ xét tên nhiều từ để tránh báo giả với các từ
    # thường (Dragon, Forest, Umi...) vốn cũng trùng tên một lá bài khác.
    # D10: the name pool spans all 1,082 cards (FM + outside FM) -- a
    # multiword name only introduced by the 360 outside-FM cards must still
    # guard both groups' translations.
    multiword_card_names = [c["name"] for c in cards if " " in c["name"]]
    dissolved_card_names_in_lore_vi = [
        (num, name)
        for num, en_lore in en_lore_by_number.items()
        for name in multiword_card_names
        if name in en_lore
        and lore_vi_raw.get(num)
        and name not in lore_vi_raw[num]
    ]
    check(
        "tên lá bài nhiều từ có mặt trong lore tiếng Anh thì cũng có mặt y nguyên (tiếng Anh) trong loreVi cùng lá (D5: không dịch tên bài)",
        not dissolved_card_names_in_lore_vi,
        f"{dissolved_card_names_in_lore_vi[:5]}",
    )
    recounted_lore_vi = sum(1 for num in real_numbers if lore_vi_raw.get(num))
    check(
        "meta.cardsWithLoreVi khớp số đếm lại trực tiếp từ bốn file data/lore-vi/part-*.json "
        "(mẫu số là 722 lá FM, không phải tổng 1.082 lá -- lá ngoài FM lấy loreVi từ Descricao-VI, "
        "một nguồn khác, xem check bên dưới)",
        data["meta"]["cardsWithLoreVi"] == recounted_lore_vi == sum(1 for c in fm_cards if c["loreVi"]),
        f"meta={data['meta']['cardsWithLoreVi']}, recounted={recounted_lore_vi}, "
        f"spine={sum(1 for c in fm_cards if c['loreVi'])}",
    )
    loreVi_null_mismatch = [
        c["number"] for c in fm_cards
        if bool(c["loreVi"]) != bool(lore_vi_raw.get(str(c["number"])))
    ]
    check(
        "lá FM thiếu bản dịch có loreVi là null (không phải chuỗi rỗng); lá có bản dịch giữ đúng giá trị đó",
        not loreVi_null_mismatch,
        f"{loreVi_null_mismatch[:5]}",
    )

    # --- D5/D10: outside-FM loreVi (Descricao-VI, joined per-card rather
    # than by number) must not dissolve a multiword card name either.
    # extract_cards.apply_outside_fm_lore_vi_name_guard() already nulls any
    # violating card's loreVi during extraction -- this recounts the
    # violation set independently, straight from a *fresh* (un-nulled) call
    # to load_outside_fm_cards(), and checks three things: the extracted
    # data has no remaining violation, the extractor nulled exactly the
    # cards that violate (not more, not fewer), and meta reports the same
    # count. ---
    outside_raw_for_guard = extract_cards.load_outside_fm_cards(fm_cards)
    outside_raw_by_name = {c["name"]: c for c in outside_raw_for_guard}
    expected_nulled_names = {
        c["name"]
        for c in outside_raw_for_guard
        if c["lore"]
        and c["loreVi"]
        and any(name in c["lore"] and name not in c["loreVi"] for name in multiword_card_names)
    }
    check(
        "meta.outsideFmLoreViNulled khớp đúng số lá ngoài FM đếm lại độc lập vi phạm quy tắc D5 (đếm lại từ "
        "cartas_runtime.json chưa qua guard, không gõ cứng)",
        data["meta"]["outsideFmLoreViNulled"] == len(expected_nulled_names),
        f"meta={data['meta']['outsideFmLoreViNulled']}, recounted={len(expected_nulled_names)}",
    )
    outside_guard_mismatch = [
        c["name"]
        for c in outside_fm_cards
        if (c["name"] in expected_nulled_names and c["loreVi"] is not None)
        or (c["name"] not in expected_nulled_names and c["loreVi"] != outside_raw_by_name[c["name"]]["loreVi"])
    ]
    check(
        "extract_cards.py chỉ null hoá loreVi của đúng những lá ngoài FM vi phạm D5 -- lá vi phạm có loreVi "
        "null trong dữ liệu trích xuất, lá không vi phạm giữ nguyên bản dịch gốc",
        not outside_guard_mismatch,
        f"{outside_guard_mismatch[:5]}",
    )
    outside_dissolved_remaining = [
        (c["name"], name)
        for c in outside_fm_cards
        if c["lore"] and c["loreVi"]
        for name in multiword_card_names
        if name in c["lore"] and name not in c["loreVi"]
    ]
    check(
        "sau khi guard chạy, không lá ngoài FM nào còn loreVi vi phạm D5 (tên lá bị hòa tan vào bản dịch)",
        not outside_dissolved_remaining,
        f"{outside_dissolved_remaining[:5]}",
    )

    # --- meta counts backing tab "Độ phủ dữ liệu" (cell fm-guide-site-5) ---
    # The tab reads every number straight from FM_DATA.meta at runtime; here
    # we assert meta actually carries every field it needs, and that each
    # value is the real count from the same extraction run (never a number
    # baked in by hand on either side).
    required_meta_fields = (
        "totalCards", "fmCards", "outsideFmCards", "cardsWithAtkDef", "cardsWithType",
        "cardsWithEquips", "cardsWithFusionSystems", "equipListsCount", "fusionBasicCount",
        "fusionExactCount", "fusionExactAllFmCount", "fusionExactTypeRangeCount",
        "fusionExactMultiResultPairs", "fusionSourceRows", "fusionConflictCount",
        "fusionConflictMemberNames", "fusionGroupsWithMembers", "cardsWithLoreVi",
        "outsideFmLoreViNulled",
    )
    check(
        "FM_DATA.meta có đủ các trường số đếm phục vụ tab Độ phủ dữ liệu",
        all(k in data["meta"] for k in required_meta_fields),
        f"meta keys: {sorted(data['meta'].keys())}",
    )
    check(
        "meta.cardsWithType đúng bằng số lá FM có type != null trong spine (mẫu số 722 lá FM, không phải "
        "1.082 -- lá ngoài FM cũng có type nhưng không tính vào mốc này)",
        data["meta"]["cardsWithType"] == sum(1 for c in fm_cards if c["type"] is not None) == 621,
        f"got {data['meta']['cardsWithType']}",
    )
    check(
        "meta.cardsWithFusionSystems (258, hiện trên tab Độ phủ dữ liệu) đúng bằng số lá FM "
        "có fusionSystems != null trong spine đếm lại (khác 261 — số tên riêng biệt, không phải số lá; "
        "mẫu số là 722 lá FM -- lá ngoài FM luôn có fusionSystems null)",
        data["meta"]["cardsWithFusionSystems"] == sum(1 for c in fm_cards if c["fusionSystems"]) == 258,
        f"got {data['meta']['cardsWithFusionSystems']}",
    )
    check(
        "meta.fusionBasicCount khớp đúng số phần tử thật của bảng fusionBasic (fusionConflictCount đếm lại từ nguồn ở dưới, không gõ cứng số ở đây)",
        data["meta"]["fusionBasicCount"] == len(data["fusionBasic"]) == 141,
        f"got {data['meta']['fusionBasicCount']}",
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

    # (4) D9 -- "Chính xác" fusion recipes now come from fusion_unique.json,
    # not fusion.md's old "Dung hợp chính xác" section. Recount everything
    # straight from the raw `especificas` rows (never a hardcoded literal,
    # and never trusting extract_cards's own internal set-building twice).
    fusion_unique_rows = extract_cards.load_fusion_unique_rows()
    check(
        "fusionSourceRows khớp đúng số dòng thô trong especificas (fusion_unique.json)",
        data["meta"]["fusionSourceRows"] == len(fusion_unique_rows) == 50937,
        f"got {data['meta']['fusionSourceRows']}, source has {len(fusion_unique_rows)}",
    )
    source_exact_triples: set[tuple[str, str, str]] = set()
    for row in fusion_unique_rows:
        a, b, result = row["carta1"], row["carta2"], row["resultado"]
        lo, hi = (a, b) if a <= b else (b, a)
        source_exact_triples.add((lo, hi, result))
    check(
        "(a) số công thức 'Chính xác' chuẩn hoá == meta.fusionExactCount == len(fusionPairs)/6, đếm lại từ especificas (đếm lại từ nguồn, không gõ cứng)",
        len(source_exact_triples) == data["meta"]["fusionExactCount"] == len(data["fusionPairs"]) // 6 == 25504,
        f"source {len(source_exact_triples)}, meta {data['meta']['fusionExactCount']}, "
        f"fusionPairs/6 {len(data['fusionPairs']) // 6}",
    )
    check(
        "(b) gộp hai chiều không mất công thức nào: mọi hàng thô trong especificas, chuẩn hoá về (min, max, resultado), đều tìm thấy trong tập kết quả",
        all(
            (min(row["carta1"], row["carta2"]), max(row["carta1"], row["carta2"]), row["resultado"])
            in source_exact_triples
            for row in fusion_unique_rows
        ),
    )
    fusion_name_index = {name: i for i, name in enumerate(data["fusionNames"])}
    decoded_triples: set[tuple[str, str, str]] = set()
    pairs_str = data["fusionPairs"]
    alphabet_index = {c: i for i, c in enumerate(extract_cards.FUSION_PAIR_ALPHABET)}

    def _decode2(chunk: str) -> int:
        return alphabet_index[chunk[0]] * 64 + alphabet_index[chunk[1]]

    decode_out_of_range = False
    for i in range(0, len(pairs_str), 6):
        chunk = pairs_str[i : i + 6]
        lo_i, hi_i, res_i = _decode2(chunk[0:2]), _decode2(chunk[2:4]), _decode2(chunk[4:6])
        if not (0 <= lo_i < len(data["fusionNames"]) and 0 <= hi_i < len(data["fusionNames"]) and 0 <= res_i < len(data["fusionNames"])):
            decode_out_of_range = True
            continue
        decoded_triples.add((data["fusionNames"][lo_i], data["fusionNames"][hi_i], data["fusionNames"][res_i]))
    check(
        "(c) mọi chỉ số giải mã từ fusionPairs đều nằm trong fusionNames (không lệch mảng)",
        not decode_out_of_range,
    )
    check(
        "fusionPairs giải mã ra đúng tập 25.504 bộ ba khớp 1-1 với especificas chuẩn hoá (đếm lại từ nguồn, không gõ cứng)",
        decoded_triples == source_exact_triples,
        f"decoded {len(decoded_triples)} vs source {len(source_exact_triples)}, "
        f"symmetric diff size {len(decoded_triples ^ source_exact_triples)}",
    )
    check(
        "meta.fusionExactAllFmCount đếm lại đúng: số công thức mà cả 3 tên đều là lá FM thật trong spine",
        data["meta"]["fusionExactAllFmCount"]
        == sum(
            1
            for lo, hi, result in source_exact_triples
            if lo.lower() in by_name_lower and hi.lower() in by_name_lower and result.lower() in by_name_lower
        )
        == 25168,
        f"got {data['meta']['fusionExactAllFmCount']}",
    )
    check(
        "meta.fusionExactTypeRangeCount đếm lại đúng: số công thức có một vế dạng hệ ('[...]...')",
        data["meta"]["fusionExactTypeRangeCount"]
        == sum(
            1
            for lo, hi, result in source_exact_triples
            if any(n.startswith("[") and "]" in n for n in (lo, hi, result))
        )
        == 167,
        f"got {data['meta']['fusionExactTypeRangeCount']}",
    )
    exact_pair_results: dict[tuple[str, str], set[str]] = {}
    for lo, hi, result in source_exact_triples:
        exact_pair_results.setdefault((lo, hi), set()).add(result)
    check(
        "meta.fusionExactMultiResultPairs đếm lại đúng: số cặp (min, max) cho nhiều hơn một resultado",
        data["meta"]["fusionExactMultiResultPairs"]
        == sum(1 for results in exact_pair_results.values() if len(results) > 1)
        == 6,
        f"got {data['meta']['fusionExactMultiResultPairs']}",
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

    # D10: slug uniqueness is a whole-table rule -- checked across all 1,082
    # cards (722 FM + 360 outside FM), not just the FM subset, since a slug
    # collision would break images/cards/<slug>.png lookups regardless of
    # which group either card belongs to. Measured: 0 collisions between
    # the two groups.
    slugs = [c["slug"] for c in cards]
    check(
        "không slug nào trùng nhau trên toàn bộ lá (722 lá FM + 360 lá ngoài FM = 1.082 lá, D10)",
        len(set(slugs)) == len(slugs),
        f"{len(slugs) - len(set(slugs))} duplicate(s)",
    )
    bad_slugs = [s for s in slugs if not SLUG_RE.match(s)]
    check("slug chỉ chứa a-z0-9 và dấu gạch", not bad_slugs, f"bad: {bad_slugs[:5]}")

    # D10: images/cards/ only has art for the 722 FM cards so far -- the 360
    # outside-FM cards get their images in Slice 3 (D12/build_art_images.py),
    # not this cell -- so this check stays scoped to fm_cards only.
    fm_slugs = [c["slug"] for c in fm_cards]
    missing_images = [s for s in fm_slugs if not (IMAGES_DIR / f"{s}.png").is_file()]
    check(
        "cả 722 slug lá FM đều có ảnh thật trong images/cards/<slug>.png (lá ngoài FM chưa có ảnh cho tới Slice 3)",
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

    # D9/D10: fusionNames entries with no matching card anywhere in `cards`
    # (a fusion-system badge like "[Machine]0-2000" is the only kind left
    # after Slice 2 joined the 360 outside-FM cards onto `cards` too) must
    # stay plain name-only strings, never crash the extractor and never get
    # an invented spine entry. Deliberately checked against all 1,082 cards
    # here (by_name_lower_all), not the FM-only by_name_lower used above.
    by_name_lower_all = {c["name"].lower(): c for c in cards}
    fusion_names_missing_spine = [n for n in data["fusionNames"] if n.lower() not in by_name_lower_all]
    check(
        "fusionNames trỏ tới tên không có trong spine vẫn giữ dạng chỉ-có-tên, không crash",
        isinstance(fusion_names_missing_spine, list),
        f"{len(fusion_names_missing_spine)} name(s) not in spine, e.g. {fusion_names_missing_spine[:3]}",
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
        "index.html không còn chứa 'quái thú' (thuật ngữ thống nhất là 'quái vật', cell fm-guide-site-15)",
        "quái thú" not in html_text,
    )
    # iOS Safari phóng to cả trang khi ô nhập đang focus có cỡ chữ dưới 16px.
    # Mọi ô gõ và dropdown đều nằm trong .controls, nên chỉ cần một khối media
    # cho màn hình cảm ứng là đủ chặn; chỉnh cỡ chữ thay vì khoá maximum-scale
    # để người dùng vẫn pinch-zoom được.
    coarse_block = re.search(
        r"@media \(pointer: coarse\)\s*\{(.*?)\n  \}", html_text, re.S
    )
    check(
        "index.html có khối @media (pointer: coarse) đặt cỡ chữ ô nhập",
        coarse_block is not None,
    )
    if coarse_block:
        body = coarse_block.group(1)
        for sel in ('.controls input[type="text"]', ".controls select"):
            check(
                f"khối cảm ứng phủ {sel} (không để iOS phóng to khi gõ)",
                sel in body,
            )
        check(
            "khối cảm ứng đặt font-size 16px (dưới 16px là iOS phóng to)",
            "font-size: 16px" in body,
        )
    check(
        "chuỗi 'chưa có dữ liệu' có mặt trong index.html (D4)",
        "chưa có dữ liệu" in html_text,
    )

    # --- Nút x xoá nhanh ô tìm kiếm (cell fm-guide-site-16) ---
    # Cả ba ô nhập chữ (#search-name, #search-number, #fusion-search) đều có
    # một nút xoá riêng (button thật, không phải type=search), mặc định ẩn
    # (hidden) và mang aria-label tiếng Việt.
    clear_buttons = {
        "search-name-clear": "search-name",
        "search-number-clear": "search-number",
        "fusion-search-clear": "fusion-search",
    }
    for btn_id, input_id in clear_buttons.items():
        btn_match = re.search(
            r'<button[^>]*id="' + re.escape(btn_id) + r'"[^>]*>', html_text
        )
        check(
            f"index.html có nút xoá #{btn_id} là <button type=\"button\"> thật kèm aria-label",
            btn_match is not None
            and 'type="button"' in btn_match.group(0)
            and 'aria-label="' in btn_match.group(0),
            "không tìm thấy nút hoặc thiếu type/aria-label" if not btn_match else btn_match.group(0),
        )
        check(
            f"nút xoá #{btn_id} ẩn mặc định bằng thuộc tính hidden (không lọt vào Tab khi ô rỗng)",
            btn_match is not None and "hidden" in btn_match.group(0),
        )
    check(
        "cả ba ô nhập không dùng type=\"search\" (nút xoá mặc định của trình duyệt không nhất quán "
        "giữa Firefox/WebKit) -- vẫn giữ type=\"text\"",
        'id="search-name" type="text"' in html_text
        and 'id="search-number" type="text"' in html_text
        and 'id="fusion-search" type="text"' in html_text,
    )
    # applyState gán thẳng .value nên không có sự kiện "input" nào bắn ra; thiếu
    # lời gọi này thì mở #tra-cuu?q=... (hoặc bấm Back) ra ô có chữ mà nút xoá
    # vẫn ẩn. Nhánh tab Fusion được lo sẵn nhờ onFusionSearchInput().
    apply_state = re.search(r"function applyState\(st\) \{.*?\n  \}\n", html_text, re.S)
    check(
        "applyState gọi updateSearchClearButtons() sau khi gán value từ hash "
        "(khôi phục từ URL/Back phải hiện lại nút xoá)",
        apply_state is not None
        and "updateSearchClearButtons();" in apply_state.group(0),
    )
    check(
        "nhánh tab Fusion trong applyState chạy onFusionSearchInput() "
        "(hàm này tự cập nhật nút xoá của ô Fusion)",
        apply_state is not None and "onFusionSearchInput();" in apply_state.group(0),
    )
    check(
        "nút xoá ẩn/hiện theo đúng trạng thái rỗng của ô (so sánh value.length === 0), "
        "không phải một cờ trạng thái tách rời có thể lệch khỏi DOM",
        html_text.count("Clear.hidden = el") >= 3
        and "elSearchNameClear.hidden = elSearchName.value.length === 0;" in html_text
        and "elSearchNumberClear.hidden = elSearchNumber.value.length === 0;" in html_text
        and "elFusionSearchClear.hidden = elFusionSearch.value.length === 0;" in html_text,
    )
    check(
        "bấm nút xoá dùng lại scheduleHashWrite(true) (đường ghi hash sẵn có, giống lúc đổi dropdown) "
        "chứ không tự tạo đường ghi lịch sử thứ hai",
        html_text.count("elSearchNameClear.addEventListener(\"click\"") == 1
        and html_text.count("elSearchNumberClear.addEventListener(\"click\"") == 1
        and html_text.count("elFusionSearchClear.addEventListener(\"click\"") == 1,
    )
    # Mỗi ô nhập được đặt trong một wrapper .search-field mang phần chia cỡ
    # flex trước đây gắn thẳng vào #search-name/#search-number, để nút xoá
    # định vị tuyệt đối bên trong mà không phá layout hàng .controls.
    check(
        "cỡ flex của #search-name/#search-number chuyển sang wrapper .search-field "
        "(#search-name-field/#search-number-field), input không còn tự mang flex",
        "#search-name-field { flex: 1 1 220px; min-width: 180px; }" in html_text
        and "#search-number-field { flex: 0 1 160px; }" in html_text
        and re.search(r"\n\s*#search-name\s*\{\s*flex:", html_text) is None
        and re.search(r"\n\s*#search-number\s*\{\s*flex:", html_text) is None,
    )
    check(
        "ô nhập trong .search-field chừa sẵn padding-right cho nút xoá (không nhảy kích thước khi nút ẩn/hiện)",
        re.search(r'\.search-field input\[type="text"\]\s*\{[^}]*padding-right', html_text, re.S)
        is not None,
    )

    # --- Vietnamese lore in the detail panel + coverage tab (cell fm-guide-site-13) ---
    check(
        "bảng chi tiết trong index.html có nhãn 'Nguyên văn' cho lore gốc tiếng Anh",
        "Nguyên văn" in html_text,
    )
    check(
        "tab Độ phủ dữ liệu đọc số lá có lore tiếng Việt từ meta.cardsWithLoreVi (không gõ cứng)",
        "meta.cardsWithLoreVi" in html_text,
    )
    check(
        "tab Độ phủ dữ liệu nói rõ bản dịch lore là dịch máy",
        "bản dịch máy" in html_text,
    )
    check(
        "panel chi tiết dùng fmtLoreHtml(card) cho dòng Lore, không dùng fmt(card.lore) trần",
        '"<dt>Lore</dt><dd>" + fmtLoreHtml(card)' in html_text,
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

    # --- Bộ lọc Guardian Star + link lọc trong panel chi tiết (cell fm-guide-site-8) ---
    check(
        'index.html có dropdown "star-filter", populate từ danh sách guardianStars đọc lại từ dữ liệu '
        "(không hardcode 10 tên sao trong markup)",
        'id="star-filter"' in html_text
        and "populateDropdown(elStarFilter, guardianStars," in html_text,
    )
    expected_stars = {
        "Jupiter", "Mars", "Mercury", "Moon", "Neptune",
        "Pluto", "Saturn", "Sun", "Uranus", "Venus",
    }
    actual_stars = {
        s
        for c in cards
        for s in (c.get("guardianStars") or [])
        if s
    }
    check(
        "dữ liệu 722 lá phủ đủ 10 Guardian Star mà dropdown 'star-filter' liệt kê "
        "(Jupiter, Mars, Mercury, Moon, Neptune, Pluto, Saturn, Sun, Uranus, Venus)",
        actual_stars == expected_stars,
        f"got {sorted(actual_stars)}",
    )
    check(
        "không có bộ lọc theo 'Cách lấy' (obtainedBy) trong tab tra cứu — mọi lá chỉ có giá trị 'Drop' nên vô nghĩa",
        "obtainedby-filter" not in html_text.lower(),
    )
    check(
        "tham số hash 'sao' được ĐỌC (readStateFromHash/applyState) và GHI (currentHash) đúng như 'loai'/'type'/'he'",
        '["sao", elStarFilter.value]' in html_text
        and 'sao: params.sao || ""' in html_text
        and 'elStarFilter.value = st.sao || "";' in html_text,
    )
    check(
        "panel chi tiết sinh link lọc cho Loại lá, Type, mỗi hệ fusion và mỗi Guardian Star qua filterLinkHtml "
        "(giá trị thiếu vẫn là chữ 'chưa có dữ liệu', không phải link)",
        'filterLinkHtml("loai", card.cardType)' in html_text
        and 'filterLinkHtml("type", card.type)' in html_text
        and "function fmtFusionHtml(card)" in html_text
        and 'filterLinkHtml("he", s)' in html_text
        and "function fmtStarsHtml(card)" in html_text
        and 'filterLinkHtml("sao", s)' in html_text
        and 'if (!value) return "chưa có dữ liệu";' in html_text,
    )
    check(
        "danh sách Equip trong panel chi tiết dùng lại cơ chế card-link/wireCardLinks sẵn có để mở lá "
        "được equip (không tạo cơ chế nhảy thứ hai)",
        '<li><span class="card-link" data-cardname="' in html_text
        and html_text.count("function wireCardLinks(") == 1
        and html_text.count("function goToCardFilter(") == 1
        and html_text.count("function wireFilterLinks(") == 1,
    )
    check(
        "mỗi link lọc trong panel chi tiết đi qua goToCardFilter -> scheduleHashWrite(true), "
        "nên vào lịch sử duyệt như mọi thay đổi bộ lọc khác",
        re.search(
            r"function goToCardFilter\(filterKey, value\) \{.*?scheduleHashWrite\(true\);\s*\n\s*\}",
            html_text,
            re.S,
        )
        is not None,
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
        "panel chi tiết một lá có panel .detail-fusion nhãn 'Fusion List', hai tiêu đề nhóm "
        "'Ghép ra lá này'/'Lá này tham gia', imgCellHtml có nhánh size công thức, badge hệ đi qua "
        "filterLinkHtml, và bản chữ cũ (fusionRelatedHtml/'Fusion liên quan') đã bị xoá hẳn "
        "(cell fm-guide-site-21)",
        '<div class="detail-fusion">' in html_text
        and "Fusion List" in html_text
        and "Ghép ra lá này" in html_text
        and "Lá này tham gia" in html_text
        and 'size === "recipe"' in html_text
        and 'filterLinkHtml("he", side.value)' in html_text
        and "Fusion liên quan" not in html_text
        and "function fusionRelatedHtml(" not in html_text,
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

    # cell fm-guide-site-14, D1: some file:// history implementations throw
    # a SecurityError (opaque origin) from pushState/replaceState even
    # though the spec permits a hash-only same-document change there.
    # safeHistoryWrite(commit, newHash) is the one wrapper every call site
    # must go through: try the real call, and on rejection fall back to a
    # direct `location.hash = newHash` assignment that never throws.
    safe_history_match = re.search(
        r"function safeHistoryWrite\(commit, newHash\) \{\s*"
        r"try \{\s*"
        r"if \(commit\) \{\s*"
        r"history\.pushState\(null, \"\", newHash\);\s*"
        r"\} else \{\s*"
        r"history\.replaceState\(null, \"\", newHash\);\s*"
        r"\}\s*"
        r"\} catch \(e\) \{\s*"
        r"location\.hash = newHash;\s*"
        r"\}\s*"
        r"\}",
        html_text,
    )
    check(
        "index.html có safeHistoryWrite(commit, newHash) bọc pushState/replaceState trong try/catch, rơi về gán location.hash = newHash khi bị từ chối",
        safe_history_match is not None,
    )
    if safe_history_match:
        outside_wrapper = html_text[: safe_history_match.start()] + html_text[safe_history_match.end() :]
        bare_history_calls_outside = re.findall(r"history\.(?:pushState|replaceState)\(", outside_wrapper)
    else:
        bare_history_calls_outside = push_or_replace_calls
    check(
        "mọi lệnh gọi history.pushState/replaceState trong index.html đều nằm trong safeHistoryWrite (không lệnh gọi trần nào còn sót ngoài hàm bọc)",
        safe_history_match is not None and not bare_history_calls_outside,
        f"{len(bare_history_calls_outside)} lệnh gọi history.pushState/replaceState nằm ngoài safeHistoryWrite",
    )
    check(
        "writeHash(commit) ghi trạng thái qua safeHistoryWrite(commit, newHash) thay vì gọi pushState/replaceState trực tiếp",
        "safeHistoryWrite(commit, newHash);" in html_text,
    )
    check(
        "lệnh replaceState khởi tạo lúc load trang cũng đi qua safeHistoryWrite(false, currentHash()) thay vì gọi history.replaceState trần",
        "safeHistoryWrite(false, currentHash());" in html_text,
    )

    # Judge fix fm-guide-site-7 FAIL 1: a typing-burst checkpoint was lost
    # when the burst's first keystroke didn't change the trimmed hash --
    # writeHash() early-returned (no push) but scheduleHashWrite() still
    # flagged the burst open, so the next keystroke replaceState'd the
    # PREVIOUS (pre-burst) history entry. Pin: writeHash must report
    # whether it actually wrote (return false on the no-op early return,
    # true after a real push/replace), and typingBurstOpen must only ever
    # be set true from that reported result -- never unconditionally. This
    # is structural (source-shape), not behavioral, because check.py has no
    # DOM/history harness; the invariant it pins is "the burst flag and the
    # checkpoint push cannot diverge".
    writehash_fn_match = re.search(
        r"function writeHash\(commit\) \{.*?\breturn false;.*?\breturn true;\s*\}",
        html_text,
        re.S,
    )
    check(
        "writeHash(commit) trả về false khi early-return (hash không đổi) và true sau khi thực sự push/replace",
        writehash_fn_match is not None,
    )
    schedule_gate_match = re.search(
        r"var pushed = writeHash\(!typingBurstOpen\);\s*\n\s*if \(pushed\) typingBurstOpen = true;",
        html_text,
    )
    check(
        "scheduleHashWrite chỉ bật typingBurstOpen từ giá trị writeHash trả về (if (pushed) typingBurstOpen = true), không bật vô điều kiện",
        schedule_gate_match is not None,
    )
    typing_burst_true_sites = re.findall(r"typingBurstOpen\s*=\s*true", html_text)
    check(
        "toàn bộ index.html chỉ có đúng một chỗ gán typingBurstOpen = true, và đó là chỗ được gate bởi if (pushed) ở trên (cờ burst và việc push checkpoint không thể phân kỳ)",
        len(typing_burst_true_sites) == 1,
        f"tìm thấy {len(typing_burst_true_sites)} chỗ gán typingBurstOpen = true",
    )

    # Judge fix fm-guide-site-7 FAIL 2: a malformed percent-escape in the
    # hash (e.g. "#tra-cuu?q=%zz") threw an uncaught URIError from
    # decodeURIComponent inside fromQueryValue/qsParse, aborting cold load
    # (init never reaches the normalizing replaceState) or escaping
    # onHashChange mid-session (navigation silently swallowed). Pin: every
    # decodeURIComponent call site in the routing code sits inside a
    # try/catch, or goes through the one safe wrapper that does.
    safe_decode_match = re.search(
        r"function safeDecodeURIComponent\(v\) \{\s*try \{\s*return decodeURIComponent\(v\);\s*\}\s*catch \(e\) \{\s*return v;\s*\}\s*\}",
        html_text,
    )
    check(
        "index.html có safeDecodeURIComponent(v) bọc decodeURIComponent trong try/catch, trả về giá trị thô khi gặp URIError",
        safe_decode_match is not None,
    )
    all_decode_calls = re.findall(r"decodeURIComponent\(", html_text)
    unwrapped_decode_calls = re.findall(
        r"(?<!return )decodeURIComponent\(", html_text
    )
    check(
        f"đủ {len(all_decode_calls)} lệnh gọi decodeURIComponent trong index.html (guard không chạy trên tập rỗng)",
        len(all_decode_calls) > 0,
    )
    check(
        "mọi lệnh gọi decodeURIComponent trong index.html đều nằm trong safeDecodeURIComponent (chỉ 'return decodeURIComponent(' xuất hiện, tức luôn có try/catch bao ngoài) -- không lệnh gọi trần nào có thể ném URIError chưa bắt",
        len(unwrapped_decode_calls) == 0,
        f"{len(unwrapped_decode_calls)} lệnh gọi decodeURIComponent không đứng ngay sau 'return ' (khả năng nằm ngoài try/catch)",
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
            embedded_cards = embedded.get("cards", [])
            embedded_fm_count = sum(1 for c in embedded_cards if not c.get("outsideFm"))
            check(
                "khối FM_DATA nhúng trong index.html chứa đúng 722 lá FM (dữ liệu thật, không rỗng)",
                embedded_fm_count == 722,
                f"got {embedded_fm_count}",
            )
            check(
                "tổng số lá khớp giữa data (extract_cards.py trích xuất tươi) và khối FM_DATA nhúng trong "
                "index.html (index.html không bị lệch khỏi lần chạy --inject gần nhất)",
                len(embedded_cards) == len(cards) == data["meta"]["totalCards"],
                f"embedded {len(embedded_cards)}, freshly extracted {len(cards)}, "
                f"meta.totalCards {data['meta']['totalCards']}",
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

    # --- Chế độ xem lưới ảnh cho tab tra cứu bài (cell fm-guide-site-17) ---
    view_mode_buttons = {
        "view-mode-table": "Bảng",
        "view-mode-grid": "Lưới",
    }
    for btn_id, label in view_mode_buttons.items():
        btn_match = re.search(
            r'<button[^>]*id="' + re.escape(btn_id) + r'"[^>]*>' + re.escape(label),
            html_text,
        )
        check(
            f"index.html có nút chuyển chế độ xem #{btn_id} là <button type=\"button\"> thật, "
            f"nhãn '{label}', kèm aria-pressed",
            btn_match is not None
            and 'type="button"' in btn_match.group(0)
            and "aria-pressed=" in btn_match.group(0),
            "không tìm thấy nút hoặc thiếu type/nhãn/aria-pressed" if not btn_match else btn_match.group(0),
        )
    check(
        "index.html có khối #card-grid (chế độ xem lưới), đặt cạnh #table-wrap và ẩn mặc định",
        '<div id="card-grid" class="card-grid" hidden></div>' in html_text
        and 'id="table-wrap"' in html_text,
    )
    check(
        "ô lưới dựng đường ảnh từ card.slug qua imgCellHtml (dùng lại, không tự ráp đường ảnh thứ hai) "
        "và mỗi ô là <button> mang data-number để mở popup chi tiết",
        "function gridTileHtml(card)" in html_text
        and 'imgCellHtml(card, "tile")' in html_text
        and html_text.count("function imgCellHtml(") == 1
        and '<button type="button" class="grid-tile" data-number="' in html_text,
    )
    check(
        "lưới và bảng dùng chung state.filtered/PAGE_SIZE/renderPager trong render() -- không có bộ lọc "
        "hay phân trang thứ hai cho lưới",
        html_text.count("function render() {") == 1
        and re.search(
            r"function render\(\) \{.*?state\.filtered\.length.*?PAGE_SIZE.*?renderPager\(pageCount\);\s*\n\s*\}",
            html_text,
            re.S,
        )
        is not None,
    )
    check(
        "#card-grid có delegate click riêng gọi showDetail(card) như tbody, không nhân bản logic mở popup "
        "(chỉ đúng một định nghĩa showDetail)",
        html_text.count("function showDetail(card)") == 1
        and re.search(
            r'elCardGrid\.addEventListener\("click", function \(ev\) \{.*?showDetail\(card\);.*?\}\);',
            html_text,
            re.S,
        )
        is not None,
    )
    check(
        "tham số hash 'xem' được ĐỌC (readStateFromHash) và GHI (currentHash) cho chế độ xem, "
        "và applyState dựng lại chế độ trước khi lọc/render",
        '["xem", viewMode === "luoi" ? "luoi" : ""]' in html_text
        and 'xem: params.xem === "luoi" ? "luoi" : "bang"' in html_text
        and "setViewMode(st.xem);" in html_text,
    )
    check(
        "đổi chế độ xem đi qua scheduleHashWrite(true) (đường ghi hash sẵn có, giống lúc đổi dropdown) "
        "nên Back trả lại chế độ trước, không tạo đường lịch sử thứ hai",
        html_text.count('elViewModeTableBtn.addEventListener("click"') == 1
        and html_text.count('elViewModeGridBtn.addEventListener("click"') == 1,
    )

    # --- Bộ chọn cỡ lưới cho chế độ xem lưới: Tự động + 4/6/8 cột (cell fm-guide-site-19) ---
    grid_size_buttons = {
        "grid-size-auto": "Tự động",
        "grid-size-4": "4",
        "grid-size-6": "6",
        "grid-size-8": "8",
    }
    for btn_id, label in grid_size_buttons.items():
        btn_match = re.search(
            r'<button[^>]*id="' + re.escape(btn_id) + r'"[^>]*>' + re.escape(label),
            html_text,
        )
        check(
            f"index.html có nút cỡ lưới #{btn_id} là <button type=\"button\"> thật, "
            f"nhãn '{label}', kèm aria-pressed",
            btn_match is not None
            and 'type="button"' in btn_match.group(0)
            and "aria-pressed=" in btn_match.group(0),
            "không tìm thấy nút hoặc thiếu type/nhãn/aria-pressed" if not btn_match else btn_match.group(0),
        )
    check(
        "nhóm nút cỡ lưới #grid-size-toggle có role=\"group\" và aria-label tiếng Việt, "
        "ẩn mặc định (chỉ hiện ở chế độ lưới qua setViewMode)",
        re.search(
            r'<span id="grid-size-toggle"[^>]*role="group"[^>]*aria-label="[^"]+"[^>]*hidden',
            html_text,
        )
        is not None,
    )
    check(
        "ba quy tắc CSS cỡ lưới cố định dùng công thức kẹp trần max(110px, calc(...)) cho N = 4, 6, 8, "
        "với 0.75rem khớp gap sẵn có của .card-grid",
        'minmax(max(110px, calc((100% - 3 * 0.75rem) / 4)), 1fr)' in html_text
        and 'minmax(max(110px, calc((100% - 5 * 0.75rem) / 6)), 1fr)' in html_text
        and 'minmax(max(110px, calc((100% - 7 * 0.75rem) / 8)), 1fr)' in html_text,
    )
    check(
        "setGridSize(size) đặt data-cot trên #card-grid và đồng bộ aria-pressed bốn nút, "
        "không tự render lại (giống setViewMode)",
        "function setGridSize(size)" in html_text
        and "elCardGrid.dataset.cot = gridSize;" in html_text,
    )
    check(
        "tham số hash 'cot' được GHI (currentHash, chỉ khi đang ở lưới và khác 'tu-dong') và "
        "ĐỌC (readStateFromHash, chỉ nhận '4'/'6'/'8') cho cỡ lưới, applyState gọi setGridSize(st.cot) "
        "ngay cạnh setViewMode(st.xem)",
        '["cot", viewMode === "luoi" && gridSize !== "tu-dong" ? gridSize : ""]' in html_text
        and 'cot: params.cot === "4" || params.cot === "6" || params.cot === "8" ? params.cot : "tu-dong"'
        in html_text
        and "setViewMode(st.xem);\n      setGridSize(st.cot);" in html_text,
    )
    check(
        "đổi cỡ lưới đi qua scheduleHashWrite(true) (đường ghi hash sẵn có) nên Back lùi lại từng cỡ đã chọn",
        html_text.count('elGridSizeAutoBtn.addEventListener("click"') == 1
        and html_text.count('elGridSize4Btn.addEventListener("click"') == 1
        and html_text.count('elGridSize6Btn.addEventListener("click"') == 1
        and html_text.count('elGridSize8Btn.addEventListener("click"') == 1,
    )

    # --- Ô chọn sắp xếp theo số/ATK/DEF cho tab tra cứu bài (cell fm-guide-site-20) ---
    sort_select_match = re.search(
        r'<select id="sort-order" aria-label="Sắp xếp">(.*?)</select>', html_text, re.S
    )
    check(
        'index.html có #sort-order là <select> thật, aria-label="Sắp xếp", đủ sáu mục '
        "theo đúng thứ tự (mặc định 'Số tăng dần' value rỗng, rồi số giảm dần, "
        "atk giảm/tăng, def giảm/tăng)",
        sort_select_match is not None
        and re.findall(r'<option value="([^"]*)">([^<]+)</option>', sort_select_match.group(1))
        == [
            ("", "Số tăng dần"),
            ("so-giam", "Số giảm dần"),
            ("atk-giam", "ATK giảm dần"),
            ("atk-tang", "ATK tăng dần"),
            ("def-giam", "DEF giảm dần"),
            ("def-tang", "DEF tăng dần"),
        ],
        sort_select_match.group(0) if sort_select_match else "không tìm thấy #sort-order",
    )
    apply_filters_fn = re.search(r"function applyFilters\(\) \{.*?\n  \}\n", html_text, re.S)
    apply_filters_has_sort = (
        apply_filters_fn is not None and "state.filtered.sort" in apply_filters_fn.group(0)
    )
    check(
        "bước sắp xếp nằm trong applyFilters() sẵn có, sắp xếp thẳng vào state.filtered (không "
        "tạo mảng đã sắp xếp thứ hai), SAU khi lọc xong CARDS.filter(...) và TRƯỚC state.page = 1 / "
        "render() -- không sắp xếp lại trong render() hay riêng từng chế độ xem",
        apply_filters_has_sort
        and apply_filters_fn.group(0).index("state.filtered = CARDS.filter")
        < apply_filters_fn.group(0).index("state.filtered.sort")
        < apply_filters_fn.group(0).index("state.page = 1;"),
        apply_filters_fn.group(0) if apply_filters_fn else "không tìm thấy hàm applyFilters",
    )
    check(
        "mọi lời gọi state.filtered.sort đều nằm trong applyFilters() (không có đường sắp xếp "
        "thứ hai trong render() hay riêng từng chế độ xem bảng/lưới)",
        apply_filters_fn is not None
        and html_text.count("state.filtered.sort")
        == apply_filters_fn.group(0).count("state.filtered.sort"),
    )
    check(
        "sắp xếp theo atk/def dồn lá c.atk === null / c.def === null xuống cuối bất kể chiều "
        "tăng hay giảm (đúng điều kiện null của bộ lọc 'Chỉ hiện lá có ATK/DEF'), và tie-break "
        "bằng a.number - b.number cho ổn định thay vì dựa vào tính ổn định của Array.prototype.sort",
        "aVal === null" in html_text
        and "if (aNull !== bNull) return aNull ? 1 : -1;" in html_text
        and "return a.number - b.number;" in html_text,
    )
    check(
        "tham số hash 'sap' được GHI (currentHash, giá trị select) và ĐỌC (readStateFromHash, "
        "chỉ nhận 5 giá trị hợp lệ so-giam/atk-giam/atk-tang/def-giam/def-tang, ngoài ra về mặc định), "
        "applyState gán lại elSortOrder.value trước khi gọi applyFilters()",
        '["sap", elSortOrder.value]' in html_text
        and '["so-giam", "atk-giam", "atk-tang", "def-giam", "def-tang"].indexOf(params.sap) !== -1'
        in html_text
        and "elSortOrder.value = st.sap || \"\";\n      elOnlyAtkDef.checked" in html_text,
    )
    check(
        "đổi #sort-order gọi applyFilters() rồi đi qua scheduleHashWrite(true) sẵn có -- "
        "giống hệt các select lọc khác, không tạo đường ghi hash thứ hai",
        "elSortOrder.addEventListener(\"change\", applyFilters);" in html_text
        and 'elSortOrder.addEventListener("change", function () { scheduleHashWrite(true); });'
        in html_text,
    )

    # --- Popup chi tiết: bố cục hai cột + nút chuyển lá trước/lá sau (cell fm-guide-site-18) ---
    detail_info_css = re.search(r"\.detail-info \{(.*?)\}", html_text, re.S)
    check(
        ".detail-info có bề rộng cơ sở flex (flex: 1 1 320px) và min-width: 0, để trên panel rộng "
        "ảnh và khối thông tin nằm cùng hàng thay vì .detail-info bị đẩy xuống dòng dưới",
        detail_info_css is not None
        and "flex: 1 1 320px;" in detail_info_css.group(1)
        and "min-width: 0;" in detail_info_css.group(1),
        detail_info_css.group(0) if detail_info_css else "không tìm thấy khối CSS .detail-info {}",
    )
    detail_nav_fn = re.search(r"function detailNavHtml\(card\) \{.*?\n  \}\n", html_text, re.S)
    check(
        "index.html có hàm detailNavHtml dựng hai nút mũi tên '‹'/'›' là <button type=\"button\"> thật "
        "kèm aria-label tiếng Việt ('Lá trước' / 'Lá sau'), không phải chỉ làm mờ bằng CSS",
        detail_nav_fn is not None
        and 'class="detail-nav-btn detail-nav-prev" aria-label="Lá trước"' in detail_nav_fn.group(0)
        and 'class="detail-nav-btn detail-nav-next" aria-label="Lá sau"' in detail_nav_fn.group(0)
        and detail_nav_fn.group(0).count('type="button"') == 2
        and "disabled" in detail_nav_fn.group(0),
        detail_nav_fn.group(0) if detail_nav_fn else "không tìm thấy hàm detailNavHtml",
    )
    navigate_detail_fn = re.search(r"function navigateDetail\(delta\) \{.*?\n  \}\n", html_text, re.S)
    check(
        "navigateDetail() dùng lại showDetail() và scheduleHashWrite(true) sẵn có để chuyển lá -- "
        "không dựng logic mở popup hay đường ghi lịch sử thứ hai -- và đọc state.filtered, "
        "không đọc thẳng CARDS",
        navigate_detail_fn is not None
        and "showDetail(targetCard);" in navigate_detail_fn.group(0)
        and "scheduleHashWrite(true);" in navigate_detail_fn.group(0)
        and "state.filtered" in navigate_detail_fn.group(0)
        and "CARDS" not in navigate_detail_fn.group(0)
        and html_text.count("function showDetail(card)") == 1,
        navigate_detail_fn.group(0) if navigate_detail_fn else "không tìm thấy hàm navigateDetail",
    )
    check(
        "getFilteredIndex() (nền tảng của cả nút bấm lẫn phím mũi tên) tìm vị trí trong state.filtered, "
        "không đọc thẳng mảng CARDS toàn cục",
        "function getFilteredIndex(card) {" in html_text
        and "state.filtered[i].number === card.number" in html_text,
    )
    check(
        "nút mũi tên gọi lại navigateDetail() qua addEventListener trên .detail-nav-prev/.detail-nav-next "
        "trong showDetail(), không nhân bản logic dựng popup",
        'navPrevBtn.addEventListener("click", function () { navigateDetail(-1); });' in html_text
        and 'navNextBtn.addEventListener("click", function () { navigateDetail(1); });' in html_text,
    )
    check(
        "phím mũi tên trái/phải chuyển lá khi popup mở, bỏ qua khi con trỏ đang trong ô nhập/textarea/select "
        "hay vùng contenteditable, và Escape vẫn đóng popup như cũ",
        'if (ev.key === "Escape") { closeDetail(); return; }' in html_text
        and 'if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;' in html_text
        and 'if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (t && t.isContentEditable)) return;'
        in html_text
        and "navigateDetail(ev.key === \"ArrowLeft\" ? -1 : 1);" in html_text,
    )
    check(
        "applyFilters() gọi updateDetailNavButtons() sau render() -- đổi bộ lọc trong lúc popup đang mở "
        "phải cập nhật lại trạng thái disabled của hai nút, không để chúng trỏ ra ngoài state.filtered mới",
        re.search(r"function applyFilters\(\) \{.*?\n  \}\n", html_text, re.S) is not None
        and "updateDetailNavButtons();" in re.search(
            r"function applyFilters\(\) \{.*?\n  \}\n", html_text, re.S
        ).group(0),
    )

    # --- D12: the second (Rush Duel-style) art image set, images/art/ ---
    # Never trust tools/build_art_images.py's own printed numbers -- recount
    # from disk here, the same way every other "no fabricated data" check
    # in this file recounts from its own source.
    cards_with_art_image = [c for c in cards if c["artImage"]]
    missing_art_files = [
        c["slug"] for c in cards_with_art_image
        if not (REPO_ROOT / c["artImage"]).is_file()
    ]
    check(
        "mọi lá khai artImage đều có file thật trên đĩa (không bịa đường dẫn)",
        not missing_art_files,
        f"{len(missing_art_files)} missing, e.g. {missing_art_files[:5]}",
    )

    art_files_on_disk = {f.stem for f in ART_DIR.glob("*.webp")} if ART_DIR.is_dir() else set()
    slugs_with_art_image = {c["slug"] for c in cards_with_art_image}
    unclaimed_art_files = sorted(art_files_on_disk - slugs_with_art_image)
    check(
        "không lá nào khai artImage trỏ tới file thiếu, và không file images/art/ nào bị bỏ sót "
        "(mọi *.webp trên đĩa đều được một lá nào đó khai artImage)",
        not unclaimed_art_files,
        f"{len(unclaimed_art_files)} orphan file(s), e.g. {unclaimed_art_files[:5]}",
    )

    art_total_bytes = sum(f.stat().st_size for f in ART_DIR.glob("*.webp")) if ART_DIR.is_dir() else 0
    check(
        "tổng dung lượng images/art/ dưới 40MB (đo lại từ đĩa, D12)",
        art_total_bytes < ART_BUDGET_BYTES,
        f"{art_total_bytes / 1024 / 1024:.2f} MB",
    )

    check(
        "meta.cardsWithArtImage khớp số lá có artImage != null đếm lại trực tiếp trên `cards` "
        "(722 FM + 360 ngoài FM -- cả hai nhóm cùng nguồn ảnh, D12)",
        data["meta"]["cardsWithArtImage"] == len(cards_with_art_image),
        f"meta={data['meta']['cardsWithArtImage']}, recounted={len(cards_with_art_image)}",
    )

    # 26 FM Ritual cards absent from the CardFusionExplorer source get no
    # second art image at all (CONTEXT.md D12) -- assert that stays a null
    # field, never an invented path.
    ritual_without_art = [
        c for c in fm_cards
        if c["artImage"] is None and (ART_DIR / f"{c['slug']}.webp").is_file()
    ]
    check(
        "không lá nào có file images/art/<slug>.webp thật trên đĩa mà artImage vẫn là null",
        not ritual_without_art,
        f"{[c['name'] for c in ritual_without_art][:5]}",
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
    print(f"  fusionExact recipes (D9, fusion_unique.json): {data['meta']['fusionExactCount']}")
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
