promote proposal for work item "fm-guide-site" (docs/history/fm-guide-site/CONTEXT.md + docs/history/fm-guide-site/plan.md) — 16 capped cell(s): fm-guide-site-1, fm-guide-site-2, fm-guide-site-3, fm-guide-site-4, fm-guide-site-5, fm-guide-site-6, fm-guide-site-7, fm-guide-site-8, fm-guide-site-9, fm-guide-site-10, fm-guide-site-11, fm-guide-site-12, fm-guide-site-13, fm-guide-site-14, fm-guide-site-15, fm-guide-site-16
anchor: history — docs/history/fm-guide-site/CONTEXT.md, docs/history/fm-guide-site/plan.md
PROPOSAL ONLY — nothing was written. Applying any section below is a human or agent decision.

(a) DELIVERY DRAFT — save as docs/knowledge/work/fm-guide-site/delivery.md

---
type: bee.delivery
title: fm-guide-site — delivery
description: "Delivery record proposed by bee knowledge promote for work item fm-guide-site: 16 capped cell(s), 0 recorded deviation(s)."
timestamp: 2026-08-13
bee:
  id: fm-guide-site-delivery
  lifecycle: active
  areas: [guide-site]
  required_context: [docs/history/fm-guide-site/CONTEXT.md, docs/history/fm-guide-site/plan.md]
  sources: [docs/history/fm-guide-site/CONTEXT.md, docs/history/fm-guide-site/plan.md, .bee/cells/archive/fm-guide-site/fm-guide-site-1.json, .bee/cells/archive/fm-guide-site/fm-guide-site-2.json, .bee/cells/archive/fm-guide-site/fm-guide-site-3.json, .bee/cells/archive/fm-guide-site/fm-guide-site-4.json, .bee/cells/archive/fm-guide-site/fm-guide-site-5.json, .bee/cells/archive/fm-guide-site/fm-guide-site-6.json, .bee/cells/archive/fm-guide-site/fm-guide-site-7.json, .bee/cells/archive/fm-guide-site/fm-guide-site-8.json, .bee/cells/archive/fm-guide-site/fm-guide-site-9.json, .bee/cells/archive/fm-guide-site/fm-guide-site-10.json, .bee/cells/archive/fm-guide-site/fm-guide-site-11.json, .bee/cells/archive/fm-guide-site/fm-guide-site-12.json, .bee/cells/archive/fm-guide-site/fm-guide-site-13.json, .bee/cells/archive/fm-guide-site/fm-guide-site-14.json, .bee/cells/archive/fm-guide-site/fm-guide-site-15.json, .bee/cells/fm-guide-site-16.json]
---

# fm-guide-site — Delivery

## What shipped

- **fm-guide-site-1** — Extractor mines docs/guide into window.FM_DATA (653 cards, 101 ATK/DEF, 257 fusion-system names — corrected from plan.md's 261, a discovery-time parsing artifact); check.py asserts the data-layer invariants (2 file(s) changed)
- **fm-guide-site-2** — index.html card lookup page built with embedded FM_DATA (653 cards) via new --inject flag; check.py green with new D1/D2/D4 structural assertions (3 file(s) changed)
- **fm-guide-site-3** — Card lookup table spine switched to data/cards.json (722 Yugipedia cards); equip lists + fusion joined onto it by name via a 15-entry alias table; index.html shows real images, type/cardType filters, and a full detail panel; tools/check.py rewritten for the new source (3 file(s) changed)
- **fm-guide-site-4** — Filled the Hướng dẫn tab with all 9 sections edited from docs/guide/Game Yu-Gi-Oh Hướng dẫn cơ bản.md, including an inline-SVG Guardian Star wheel and a StarChip password table linked to card detail (1 file(s) changed)
- **fm-guide-site-5** — Tab Fusion tra cuu hai chieu, tab do phu doc tu meta, alias giai duoc ten cong thuc, sentinel starChipCost hien khong mua duoc (3 file(s) changed)
- **fm-guide-site-6** — Broadened the conflict-fusion top-header parser to accept a plain name (not just [Type]) on the general line, recovering all 10 dropped stanzas (212/212, triples match source 1-for-1); re-injected index.html and added source-recounted assertions for all three fusion sections to tools/check.py (3 file(s) changed)
- **fm-guide-site-7** — Deep-link hash router cho tab, bo loc, phan trang va la dang mo; Back/Forward dung; sua mat checkpoint burst go phim va URIError hash hong (2 file(s) changed)
- **fm-guide-site-8** — Detail-panel values (cardType, Type, fusion systems, Guardian Star) now link into the card-lookup filters, equip rows reuse the existing card-link jump; added the missing Guardian Star (sao) filter wired through the hash router. (2 file(s) changed)
- **fm-guide-site-9** — Translated cards #1-181 lore into Vietnamese, natural spoken register, card/type names kept in English (1 file(s) changed)
- **fm-guide-site-10** — Translated 181 card lore entries (#182-362) into natural spoken-register Vietnamese, verified key count/order/non-empty/non-English (1 file(s) changed)
- **fm-guide-site-11** — Translated cards #363-543 lore into Vietnamese in data/lore-vi/part-3.json (1 file(s) changed)
- **fm-guide-site-12** — Translated 179 card lore entries (#544-#722) into Vietnamese in data/lore-vi/part-4.json (1 file(s) changed)
- **fm-guide-site-13** — Embed loreVi from data/lore-vi into FM_DATA, show it in the detail panel above a labelled English original, add a machine-translated coverage row read from meta.cardsWithLoreVi, extend tools/check.py with the new invariants (4 file(s) changed)
- **fm-guide-site-14** — Wrapped all History API call sites in safeHistoryWrite, falling back to location.hash on SecurityError; verified byte-identical behavior with working history and no uncaught/console errors with rejecting history via a jsdom harness with the pushState/replaceState file:// bug patched out (2 file(s) changed)
- **fm-guide-site-15** — Unified monster term to quái vật across lore-vi + index.html, restored Resurrection of Chakra's English name for card #694, fixed three flagged sentences (#514/#262/#233), and added two regression assertions to tools/check.py (6 file(s) changed)
- **fm-guide-site-16** — Added a self-drawn clear (x) button to #search-name, #search-number, and #fusion-search that appears only when the field has text, clears+refilters+refocuses on click, and commits a real history entry via the existing scheduleHashWrite(true) path (2 file(s) changed)

## Verify

Each cell below was capped only against a recorded passing verify result — bee refuses a cap without one.

- **fm-guide-site-1** — `python3 tools/check.py`
- **fm-guide-site-2** — `python3 tools/check.py`
- **fm-guide-site-3** — `python3 tools/check.py`
- **fm-guide-site-4** — `python3 tools/check.py`
- **fm-guide-site-5** — `python3 tools/check.py`
- **fm-guide-site-6** — `python3 tools/check.py`
- **fm-guide-site-7** — `python3 tools/check.py`
- **fm-guide-site-8** — `python3 tools/check.py`
- **fm-guide-site-9** — `python3 tools/check.py`
- **fm-guide-site-10** — `python3 tools/check.py`
- **fm-guide-site-11** — `python3 tools/check.py`
- **fm-guide-site-12** — `python3 tools/check.py`
- **fm-guide-site-13** — `python3 tools/check.py`
- **fm-guide-site-14** — `python3 tools/check.py`
- **fm-guide-site-15** — `python3 tools/check.py`
- **fm-guide-site-16** — `python3 tools/check.py`

## Deviations

None recorded in the capped cell traces.

## Provenance

Proposed by `bee knowledge promote --work fm-guide-site` from 16 capped cell trace(s) in `.bee/cells/` and the anchor `docs/history/fm-guide-site/CONTEXT.md`, `docs/history/fm-guide-site/plan.md`. Every line above is copied from a trace or from the work item; nothing here is curated truth until a human or agent accepts it.

(b) AREA UPDATES — candidate spec-sync bullets, each citing its cell

areas: from the scribing stamp for "fm-guide-site" — .bee/logs/scribing-runs.jsonl's most recent entry (2026-08-13T16:47:35.222Z), the work item declares no bee.areas.

area guide-site:
  - [fm-guide-site-1] Extractor mines docs/guide into window.FM_DATA (653 cards, 101 ATK/DEF, 257 fusion-system names — corrected from plan.md's 261, a discovery-time parsing artifact); check.py asserts the data-layer invariants — feature-wide sync per the scribing stamp, 2 file(s) changed (trace .bee/cells/archive/fm-guide-site/fm-guide-site-1.json)
  - [fm-guide-site-2] index.html card lookup page built with embedded FM_DATA (653 cards) via new --inject flag; check.py green with new D1/D2/D4 structural assertions — feature-wide sync per the scribing stamp, 3 file(s) changed (trace .bee/cells/archive/fm-guide-site/fm-guide-site-2.json)
  - [fm-guide-site-3] Card lookup table spine switched to data/cards.json (722 Yugipedia cards); equip lists + fusion joined onto it by name via a 15-entry alias table; index.html shows real images, type/cardType filters, and a full detail panel; tools/check.py rewritten for the new source — feature-wide sync per the scribing stamp, 3 file(s) changed (trace .bee/cells/archive/fm-guide-site/fm-guide-site-3.json)
  - [fm-guide-site-4] Filled the Hướng dẫn tab with all 9 sections edited from docs/guide/Game Yu-Gi-Oh Hướng dẫn cơ bản.md, including an inline-SVG Guardian Star wheel and a StarChip password table linked to card detail — feature-wide sync per the scribing stamp, 1 file(s) changed (trace .bee/cells/archive/fm-guide-site/fm-guide-site-4.json)
  - [fm-guide-site-5] Tab Fusion tra cuu hai chieu, tab do phu doc tu meta, alias giai duoc ten cong thuc, sentinel starChipCost hien khong mua duoc — feature-wide sync per the scribing stamp, 3 file(s) changed (trace .bee/cells/archive/fm-guide-site/fm-guide-site-5.json)
  - [fm-guide-site-6] Broadened the conflict-fusion top-header parser to accept a plain name (not just [Type]) on the general line, recovering all 10 dropped stanzas (212/212, triples match source 1-for-1); re-injected index.html and added source-recounted assertions for all three fusion sections to tools/check.py — feature-wide sync per the scribing stamp, 3 file(s) changed (trace .bee/cells/archive/fm-guide-site/fm-guide-site-6.json)
  - [fm-guide-site-7] Deep-link hash router cho tab, bo loc, phan trang va la dang mo; Back/Forward dung; sua mat checkpoint burst go phim va URIError hash hong — feature-wide sync per the scribing stamp, 2 file(s) changed (trace .bee/cells/archive/fm-guide-site/fm-guide-site-7.json)
  - [fm-guide-site-8] Detail-panel values (cardType, Type, fusion systems, Guardian Star) now link into the card-lookup filters, equip rows reuse the existing card-link jump; added the missing Guardian Star (sao) filter wired through the hash router. — feature-wide sync per the scribing stamp, 2 file(s) changed (trace .bee/cells/archive/fm-guide-site/fm-guide-site-8.json)
  - [fm-guide-site-13] Embed loreVi from data/lore-vi into FM_DATA, show it in the detail panel above a labelled English original, add a machine-translated coverage row read from meta.cardsWithLoreVi, extend tools/check.py with the new invariants — feature-wide sync per the scribing stamp, 4 file(s) changed (trace .bee/cells/archive/fm-guide-site/fm-guide-site-13.json)
  - [fm-guide-site-14] Wrapped all History API call sites in safeHistoryWrite, falling back to location.hash on SecurityError; verified byte-identical behavior with working history and no uncaught/console errors with rejecting history via a jsdom harness with the pushState/replaceState file:// bug patched out — feature-wide sync per the scribing stamp, 2 file(s) changed (trace .bee/cells/archive/fm-guide-site/fm-guide-site-14.json)
  - [fm-guide-site-15] Unified monster term to quái vật across lore-vi + index.html, restored Resurrection of Chakra's English name for card #694, fixed three flagged sentences (#514/#262/#233), and added two regression assertions to tools/check.py — feature-wide sync per the scribing stamp, 6 file(s) changed (trace .bee/cells/archive/fm-guide-site/fm-guide-site-15.json)
  - [fm-guide-site-16] Added a self-drawn clear (x) button to #search-name, #search-number, and #fusion-search that appears only when the field has text, clears+refilters+refocuses on click, and commits a real history entry via the existing scheduleHashWrite(true) path — feature-wide sync per the scribing stamp, 2 file(s) changed (trace .bee/cells/fm-guide-site-16.json)

(c) PATTERN CANDIDATES — candidate bee.pattern concepts, bee.polarity pitfall

from cell fm-guide-site-5 — save as docs/knowledge/patterns/fm-guide-site-fm-guide-site-5-pitfall.md

---
type: bee.pattern
title: fm-guide-site cell fm-guide-site-5 — pitfall candidate
description: "Pitfall candidate mined from cell fm-guide-site-5's capped trace: Hai lá bài có thật (#480 Kuwagata α, #606 Twin Long Rods 2) hiện không link trong bảng Fusion vì đường dẫn tên công thức không tra bảng alias; và meta.cardsWit…"
timestamp: 2026-08-13
bee:
  id: fm-guide-site-fm-guide-site-5-pitfall
  lifecycle: draft
  areas: [guide-site]
  sources: [.bee/cells/archive/fm-guide-site/fm-guide-site-5.json]
  polarity: pitfall
---

# fm-guide-site cell fm-guide-site-5 — pitfall candidate

## What the cell did

Tab Fusion tra cuu hai chieu, tab do phu doc tu meta, alias giai duoc ten cong thuc, sentinel starChipCost hien khong mua duoc

## Recorded evidence (verbatim from .bee/cells/archive/fm-guide-site/fm-guide-site-5.json)

- **failure_signature** — Hai lá bài có thật (#480 Kuwagata α, #606 Twin Long Rods 2) hiện không link trong bảng Fusion vì đường dẫn tên công thức không tra bảng alias; và meta.cardsWithFusionSystems hiển thị trên tab độ phủ không có khẳng định đếm lại trong check.py.

## Status

Candidate only. `bee knowledge promote` proposes; naming the pattern, generalizing it beyond this cell, and moving `bee.lifecycle` to `active` are a human or agent decision.

from cell fm-guide-site-7 — save as docs/knowledge/patterns/fm-guide-site-fm-guide-site-7-pitfall.md

---
type: bee.pattern
title: fm-guide-site cell fm-guide-site-7 — pitfall candidate
description: "Pitfall candidate mined from cell fm-guide-site-7's capped trace: Hai loi: (1) checkpoint cua mot burst go phim bi mat khi ky tu dau tien khong lam doi hash sau khi trim (vi du go them dau cach) — writeHash early-return nhung…"
timestamp: 2026-08-13
bee:
  id: fm-guide-site-fm-guide-site-7-pitfall
  lifecycle: draft
  areas: [guide-site]
  sources: [.bee/cells/archive/fm-guide-site/fm-guide-site-7.json]
  polarity: pitfall
---

# fm-guide-site cell fm-guide-site-7 — pitfall candidate

## What the cell did

Deep-link hash router cho tab, bo loc, phan trang va la dang mo; Back/Forward dung; sua mat checkpoint burst go phim va URIError hash hong

## Recorded evidence (verbatim from .bee/cells/archive/fm-guide-site/fm-guide-site-7.json)

- **failure_signature** — Hai loi: (1) checkpoint cua mot burst go phim bi mat khi ky tu dau tien khong lam doi hash sau khi trim (vi du go them dau cach) — writeHash early-return nhung typingBurstOpen van bat, nen cac ky tu sau replaceState de len entry truoc; Back nhay qua mat mot trang thai. (2) hash chua percent-escape hong (#tra-cuu?q=%zz) nem URIError khong bat, nuot luon lan dieu huong.

## Status

Candidate only. `bee knowledge promote` proposes; naming the pattern, generalizing it beyond this cell, and moving `bee.lifecycle` to `active` are a human or agent decision.

knowledge promote: 16 capped cell(s) mined, 1 delivery draft, 12 area bullet(s), 2 pattern candidate(s), 0 file(s) written.
---

## Review outcome (2026-08-14)

Đã soi từng phần của đề xuất trên. Kết quả:

- **(a) Delivery draft → không áp.** Đề xuất ghi vào `docs/knowledge/work/…`,
  nhưng repo này không có bundle `docs/knowledge/`; state layer là
  `docs/specs/`. Nội dung delivery là bản kể lại 16 cell trace — git log và
  `.bee/cells/` đã giữ đúng thông tin đó, chép lại chỉ tạo bản sao dễ mục.
- **(b) 12 area bullet → đã có sẵn.** Đối chiếu từng bullet với
  `docs/specs/guide-site.md`: mọi hành vi được nêu (bộ lọc, router hash, tab
  Fusion, tab độ phủ, lore hai bản, nút xoá nhanh, Guardian Star) đều đã nằm
  trong spec bằng ngôn ngữ nghiệp vụ. Không bullet nào thêm nghĩa mới.
- **(c) 2 pattern candidate → không nâng lên.** Cả hai là chữ ký lỗi của một
  cell cụ thể (alias tên công thức ở cell 5; checkpoint burst gõ phím và hash
  hỏng ở cell 7), đã sửa và đã có khẳng định trong `tools/check.py` canh giữ.
  Không đạt bar "tái diễn ở nhiều feature".

Đã ghi thay vào đó: `docs/history/learnings/2026-08-14-fm-guide-site.md` (bài
học của cell 17-20) và hai mục trong `docs/history/learnings/critical-patterns.md`.
