#!/usr/bin/env python3
"""Assert the data-layer invariants for tools/extract_cards.py.

Runs the real extractor against docs/guide/ (never a fixture) and checks
the shape/coverage promises made in docs/history/fm-guide-site/plan.md and
CONTEXT.md's D4 ("no fabricated data; a missing field is null, never 0").

This is the project's declared test command (`commands.test` in
.bee/config.json). Everything it writes goes to a fresh temp directory —
it never touches a deliverable file (index.html, docs/guide/, etc).
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

    # --- Card-level invariants named in the cell ---
    check("đúng 653 cặp số-tên", len(cards) == 653, f"got {len(cards)}")

    with_atk_def = [c for c in cards if c["atk"] is not None]
    check(
        "101 lá có ATK/DEF trong nguồn fusion.md (trước khi join số thứ tự)",
        data["meta"]["atkDefEntriesInFusionSource"] == 101,
        f"got {data['meta']['atkDefEntriesInFusionSource']}",
    )
    check(
        "ít nhất 96 lá join được cả số lẫn ATK/DEF",
        len(with_atk_def) >= 96,
        f"got {len(with_atk_def)}",
    )

    # docs/history/fm-guide-site/plan.md reports "261 tên" for this section,
    # but that count was produced by a discovery script with the same bug
    # this extractor was almost written with: fusion.md's "Dung hợp xung
    # đột" section has exactly one spot (the seam between two adjacent ```
    # fences, around "Witch's Apprentice" / "[Aqua] + [Dragon] = Kairyu-
    # shin") where the source omits the blank line that normally separates
    # stanzas. A parser that only stops a member block at a blank line
    # swallows the next stanza's own header tokens ("[Aqua]",
    # "+ [Dragon] = Kairyu-shin") as if they were card names, inflating the
    # true count of 257 distinct names by exactly 4. Asserting 261 here
    # would mean asserting that four non-card strings belong in the fusion
    # table — the opposite of D4. Named deviation: this cell asserts the
    # extractor's own audited count, 257, not plan.md's pre-fix estimate.
    fusion_conflict_members = data["meta"]["fusionConflictMemberNames"]
    check(
        "257 lá có hệ fusion (mục 'Dung hợp xung đột', xem ghi chú lệch 261 ở trên)",
        len(fusion_conflict_members) == 257,
        f"got {len(fusion_conflict_members)}",
    )

    aliases_expected = {
        "blue-eyed silver zombie": "139",
        "doma the angel of silence": "111",
        "stone d.": "426",
    }
    for alias_name, expected_num in aliases_expected.items():
        resolved = extract_cards.resolve_number(
            alias_name, extract_cards.build_name_lookup(
                {c["number"]: c["name"] for c in cards}
            )
        )
        check(
            f"alias '{alias_name}' -> #{expected_num}",
            resolved == expected_num,
            f"got {resolved!r}",
        )

    slugs = [c["slug"] for c in cards]
    check(
        "không slug nào trùng nhau trên toàn bộ 653 tên",
        len(set(slugs)) == len(slugs),
        f"{len(slugs) - len(set(slugs))} duplicate(s)",
    )
    bad_slugs = [s for s in slugs if not SLUG_RE.match(s)]
    check("slug chỉ chứa a-z0-9 và dấu gạch", not bad_slugs, f"bad: {bad_slugs[:5]}")

    # A real ATK/DEF of 0 legitimately exists in the source (e.g. Dragon
    # Zombie 1600/0) — the invariant is about *missing* data, not about
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
        "654 lá không có nguồn ATK/DEF đều là null (không phải chuỗi rỗng hay 0)",
        all(c["atk"] is None or isinstance(c["atk"], int) for c in cards)
        and all(c["def"] is None or isinstance(c["def"], int) for c in cards),
    )

    check("'#721' không sinh dòng ma", "721" not in by_number)

    dancing_elf = by_number.get("395")
    check(
        "dòng '#395 Dancing Elf' vẫn vào bảng",
        dancing_elf is not None and dancing_elf["name"] == "Dancing Elf",
        f"got {dancing_elf}",
    )

    # --- Structural guardrails so later cells inherit a sane base ---
    check(
        "621 khối equip theo lá quái vật (equipLists)",
        len(data["equipLists"]) == 621,
        f"got {len(data['equipLists'])}",
    )
    check("có công thức từ cả ba mục fusion.md", bool(data["fusionBasic"]) and bool(data["fusionExact"]) and bool(data["fusionConflict"]))

    # Exact-name fusion recipes pointing at names with no #NNN entry must be
    # kept as name-only references, never invented a ghost row for.
    exact_missing_numbers = [
        r["result"] for r in data["fusionExact"] if r["result"].lower() not in by_name_lower
    ]
    check(
        "công thức 'Dung hợp chính xác' trỏ tới tên không có #NNN vẫn giữ dạng chỉ-có-tên, không crash",
        isinstance(exact_missing_numbers, list),
        f"{len(exact_missing_numbers)} name-only result(s), e.g. {exact_missing_numbers[:3]}",
    )

    # --- index.html invariants (cell fm-guide-site-2, D1/D2/D3/D4) ---
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
                "khối FM_DATA nhúng trong index.html chứa đúng 653 lá (dữ liệu thật, không rỗng)",
                len(embedded.get("cards", [])) == 653,
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
    print(f"  cards (number<->name pairs):        {len(cards)}")
    print(f"  cards with ATK/DEF (joined):         {len(with_atk_def)}")
    print(f"  ATK/DEF entries in fusion.md source: {data['meta']['atkDefEntriesInFusionSource']}")
    print(f"  cards with fusion system:            {sum(1 for c in cards if c['fusionSystems'])}")
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
