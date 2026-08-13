# Trang hướng dẫn Yu-Gi-Oh! Forbidden Memories — Context

**Feature slug:** fm-guide-site
**Date:** 2026-08-13
**Shaping session:** complete
**Scope:** Standard
**Domain types:** SEE | READ

## Feature Boundary

Một file `index.html` thuần (HTML/CSS/JS, không build, không framework, không mạng)
chứa toàn bộ hướng dẫn chơi Yu-Gi-Oh! Forbidden Memories: luật cơ bản, danh sách Type,
bánh xe Guardian Star, môi trường (field), ritual, công thức fusion tra cứu được, và
một bảng tra cứu bài có tên + số thứ tự + ATK/DEF + Guardian Star + ô ảnh.
Kết thúc ở chỗ: bảng tra cứu bài lấy từ `data/cards.json` (722 lá Yugipedia) per D7; fusion,
equip và nội dung hướng dẫn lấy từ `docs/guide/*.md`; ảnh đã có đủ 722 file trong `images/cards/`.

## Locked Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Một file `index.html` duy nhất, HTML/CSS/JS thuần, không build step, không framework, không CDN; mở bằng double-click (`file://`) | User chọn phương án 1-file; yêu cầu gốc "trang thuần html" |
| D2 | Dữ liệu bài nhúng thẳng vào `index.html` dưới dạng biến JS, không `fetch()` file ngoài | `fetch()` JSON trên `file://` bị chặn — file rời sẽ vỡ khi double-click |
| D3 | Ảnh trỏ tới `images/cards/<slug>.png`, slug = tên tiếng Anh lowercase, ký tự ngoài `a-z0-9` thành `-`. Thiếu ảnh thì hiện placeholder, không vỡ layout | User chọn đặt tên theo tên lá bài; ảnh upload sau nên trang phải chịu được ảnh thiếu |
| D4 | ~~DB bài mined từ `docs/guide/`~~ — **phần nguồn bị D7 thay**. Phần còn hiệu lực: không bịa số liệu; ô không có nguồn để `null`, trang hiện "chưa có dữ liệu" | Sinh số từ trí nhớ sẽ sai âm thầm, tệ hơn ô trống |
| D5 | Nội dung trang viết bằng tiếng Việt (theo nguồn), tên lá bài và thuật ngữ game giữ nguyên tiếng Anh | Ba file nguồn đều tiếng Việt, tên bài đều tiếng Anh |
| D6 | Repo có `tools/*.py` (Python) để sinh lại khối dữ liệu trong `index.html`. Trang giao cho người dùng vẫn zero-dependency | Gõ tay hàng trăm dòng vi phạm D4; Python là phụ thuộc của người phát triển, không phải người đọc trang |
| D7 | **Thay phần nguồn của D4.** Bảng tra cứu bài lấy spine từ `data/cards.json` — 722 lá Yugipedia, đủ `type`/`guardianStars`/`level`/ATK/DEF/`password`/`lore`/`obtainedBy`, kèm 722 ảnh sẵn trong `images/cards/`. `docs/guide/` vẫn là nguồn cho công thức fusion, danh sách equip, và toàn bộ nội dung hướng dẫn | Mining `docs/guide/` chỉ cho 653 lá và 98 lá có chỉ số; Yugipedia phủ 722 lá với 621 lá đủ chỉ số. Nguyên tắc "không bịa" giữ nguyên, chỉ đổi nguồn |

### Agent's Discretion

Bố cục, cách điều hướng (tab/anchor), thiết kế bảng tra cứu, cơ chế tìm kiếm/lọc,
và định dạng chính xác của biến dữ liệu JS — miễn thỏa D1–D5.

## Terms

| Term | Meaning in this feature |
|------|-------------------------|
| Slug | Tên lá bài chuyển thành khóa file ảnh: lowercase, ký tự ngoài `a-z0-9` thành `-` |
| Ô trống | Trường không có nguồn trong `docs/guide/` — lưu `null`, hiển thị "chưa có dữ liệu", KHÔNG phải số 0 |
| Bảng tra cứu | Danh sách bài có tìm kiếm + lọc, mỗi dòng mở ra chi tiết một lá |

## Specific Ideas And References

- Người dùng sẽ upload ảnh và bổ sung thông tin sau — trang phải để chỗ trống rõ ràng,
  dễ điền, không giả vờ đã đủ dữ liệu.

## Existing Code Context

Repo chưa có code — đây là file nguồn đầu tiên. Chỉ có tài liệu.

### Reusable Assets

- `data/cards.json` (per D7) — 722 lá Yugipedia, nguồn chính của bảng tra cứu bài.
  Phủ: 621 lá có `type`/`guardianStars`/`level`/ATK/DEF (toàn bộ quái vật), 722 lá có `lore`,
  698 có `password` và `starChipCost`, 640 có `obtainedBy`. Sinh lại bằng `scripts/fetch_yugipedia_cards.py`.
- `images/cards/<slug>.png` — 722 ảnh, khớp 722/722 slug trong `data/cards.json`.
- `docs/guide/Game Yu-Gi-Oh! Forbidden Memories Quân Bài Phụ trợ.md` — 621 khối
  `#NNN <Tên> (N Equips)` → nguồn DUY NHẤT cho cặp số thứ tự ↔ tên bài. Cao nhất `#722`,
  thiếu `#721`.
- `docs/guide/Game Yu-Gi-Oh! Forbidden Memories fusion.md` — 3 mục: "Dung hợp cơ bản"
  (dòng 18, ~116 công thức `[Type] + [Type] = Tên (ATK/DEF Star/Star)`), "Dung hợp chính xác"
  (dòng 575, `Tên + Tên = Tên`, không có chỉ số), "Dung hợp xung đột" (dòng 732).
  Đây là nguồn DUY NHẤT cho ATK/DEF và Guardian Star, và chỉ phủ các lá xuất hiện trong công thức.
- `docs/guide/Game Yu-Gi-Oh Hướng dẫn cơ bản.md` — Phần 1 (dòng 14): danh sách Type
  (dòng 23–61), tên 10 Guardian Star (dòng 67–85), luật +500 ATK (dòng 88), luật field
  (dòng 94), giải thích ritual (dòng 100). Phần 2–6: bộ bài khởi đầu, mẹo fusion, farm bài,
  ~13 password mua bài, cơ chế xếp hạng Pow/Tec.

## Canonical References

- `docs/guide/` — ba file trên là nguồn sự thật duy nhất cho nội dung trang.

## Outstanding Questions

### Đã trả lời (D7 giải quyết cả hai)

- [x] Bao nhiêu lá có cả số lẫn ATK/DEF? — mining `docs/guide/` cho 98. Sau D7: **621**.
- [x] Trường "Type" per-card có ở đâu không? — không có trong `docs/guide/`. Sau D7: **621 lá** có,
      lấy từ `data/cards.json`.

## Deferred Ideas

- Công thức Ritual (tribute summon thật, ví dụ 3× Blue-Eyes) — KHÔNG có trong repo,
  chỉ có link ngoài `gamen.pro/50935`. Trang sẽ giải thích cơ chế ritual nhưng để trống
  bảng công thức cho tới khi có nguồn.
- Bảng drop bài theo đối thủ, password list đầy đủ — nguồn chỉ có ~13 dòng.
- Tải ảnh từ `gamen.pro` về local — chỉ 2 ảnh minh họa, không phải ảnh bài.
- ~~Ảnh lá bài do người dùng đổ vào sau~~ — đã xong: 722 ảnh tải sẵn từ Yugipedia (D7).

## Handoff Note

CONTEXT.md là nguồn sự thật. D1–D5 cố định. Planning đọc locked decisions,
reusable assets (đường dẫn + số dòng ở trên), và hai câu hỏi hoãn sang planning.
