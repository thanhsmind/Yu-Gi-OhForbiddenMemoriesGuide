---
artifact_contract: bee-plan/v1
mode: standard
---

# Plan: Trang hướng dẫn Yu-Gi-Oh! Forbidden Memories (fm-guide-site)

Mode: `standard` — 1 risk flag: data-model
Why this is the least workflow that protects the work: dữ liệu là toàn bộ giá trị của trang và nó phải được *trích xuất có thể chạy lại*, không gõ tay — một plan có slice giữ được ranh giới "không bịa số liệu" (D4) mà một cell đơn không giữ nổi.

## Requirements (from CONTEXT.md)

- **D1** — một file `index.html`, HTML/CSS/JS thuần, không build step, không framework, không CDN, mở bằng double-click.
- **D2** — dữ liệu nhúng inline trong `index.html` (không `fetch()`), vì `file://` chặn fetch.
- **D3** — ảnh trỏ `images/cards/<slug>.png`, slug = lowercase, ký tự ngoài `a-z0-9` → `-`; thiếu ảnh thì placeholder.
- **D4** — dữ liệu mined từ `docs/guide/`, không bịa; ô không có nguồn = `null` → hiện "chưa có dữ liệu".
- **D5** — nội dung tiếng Việt, tên bài + thuật ngữ game giữ tiếng Anh.
- **D6 (chờ duyệt ở Gate 2)** — `index.html` giao cho người dùng vẫn không phụ thuộc gì; nhưng repo có thêm `tools/*.py` để *sinh lại* khối dữ liệu trong file đó. Python là phụ thuộc của người phát triển, không phải của người đọc trang.

## Discovery

Đo trực tiếp trên ba file nguồn, đã chạy lại và đối chiếu độc lập một lần (review wave bắt được 3 con số sai ở bản nháp đầu; số dưới đây là số đã sửa):

- **653/722** số thứ tự ↔ tên bài từ `Quân Bài Phụ trợ.md` = **621** dòng tiêu đề quái vật + **32** số chỉ xuất hiện ở dòng equip. Thiếu 69 số, chủ yếu magic/trap.
  - Cạm bẫy: `Quân Bài Phụ trợ.md:3617` (`#395 Dancing Elf  (10 Equips) ---...`) có hai dấu cách và dấu gạch cùng dòng. Regex chặt cho **652**, không phải 653.
- **101** lá có ATK/DEF + cặp Guardian Star trong `fusion.md`. Sau khi join với bảng số thứ tự chỉ còn **~96** — đây là con số `CONTEXT.md:71` hỏi, và là con số quyết định bảng tra cứu trông đầy hay rỗng.
- **264** tên trong mục "Dung hợp xung đột" (`fusion.md:732-3367`) khi tách cột bằng `re.split(r'\s{2,}')`; bỏ 3 dòng văn xuôi ngoài code fence còn **261**, trong đó **258 khớp thẳng** bảng 653 tên. Đây là nguồn duy nhất suy ra hệ fusion (`[Zombie]`, `[Female]`…) cho từng lá.
  - **Cột KHÔNG rộng cố định 28 ký tự.** Tên dài hơn 26 ký tự đẩy cột phải ra, cách nhau 3 dấu cách (`fusion.md:1072`, `fusion.md:3326`). Cắt cứng ở 28 sinh 31 mảnh rác (`'vitation'`, `'t'`, `'s'`, `'z Head   Trap Master'`).
- **37** nhóm hệ fusion phân biệt, nhưng chỉ **26** nhóm có danh sách thành viên trong mục 3 — 11 nhóm còn lại không suy ra được thành viên.
- **503** dòng công thức qua 3 mục (141 + 150 + 212).
- Công thức Ritual triệu hồi thật: **không tồn tại** trong repo → giữ deferred.

**Ba tên lệch giữa hai file** (không phải lỗi cắt cột, prefix-matching không cứu được):

| `fusion.md` | `Quân Bài Phụ trợ.md` | Loại |
|---|---|---|
| `Blue-eyed Silver Zombie` | `#139 Blue Eyes Silver Zombie` | sai chính tả nguồn |
| `Doma The Angel of Silence` | `#111 Doma the Angel of Silence` | khác hoa/thường |
| `Stone D.` (2000/2300 Urn/Mrs) | `#426 Stone Dragon` | viết tắt |

## Approach

**Đường đi khuyến nghị:** một extractor Python chạy lại được (`tools/extract_cards.py`) đọc `docs/guide/`, dựng một cấu trúc dữ liệu duy nhất, rồi **ghi đè khối dữ liệu nằm giữa hai marker trong `index.html`** (`/* FM_DATA:BEGIN */` … `/* FM_DATA:END */`). Thỏa D1 về mặt sản phẩm (một file, mở phát chạy, không phụ thuộc) và D2 (inline, không fetch); đổi lại repo có thêm bước sinh dữ liệu — đó là D6, đưa người dùng duyệt ở Gate 2 chứ không tự quyết trong plan.

Tách cột bằng `re.split(r'\s{2,}')` + tra tên không phân biệt hoa thường + **bảng alias 3 dòng** cho ba tên lệch ở trên. Không có subsystem khớp tiền tố mờ.

**Đã cân nhắc và loại:**
- Khớp tiền tố với từ điển 653 tên — bản nháp đầu đề xuất; bỏ, vì nó chỉ tồn tại để vá giả định cột-28 vốn sai. Một regex + ba dòng alias thay được cả hệ thống đó.
- `data/cards.js` sidecar nạp bằng `<script src>` — chạy được trên `file://`, dễ sửa hơn, nhưng phá D1.
- `fetch('cards.json')` — vỡ hoàn toàn trên `file://`.
- Gõ tay 653 dòng — vi phạm D4.

**Risk map:**

| Thành phần | Rủi ro | Bằng chứng cần có |
|---|---|---|
| Tên lệch giữa hai file | MEDIUM — `Stone D.` mang ATK/DEF mà không bao giờ tới được `#426` | check khẳng định đúng 3 alias, và 0 tên roster nào rơi ngoài bảng sau khi áp alias |
| Regex tiêu đề equip | MEDIUM — regex chặt mất `#395`, headline 653 tụt còn 652 im lặng | check khẳng định đúng 653 |
| Công thức trỏ tới lá không có trong DB | MEDIUM — 71/211 tên ở mục "Dung hợp chính xác" không có `#NNN` (`Raigeki`, `Umi`, `Yami`…) | check khẳng định các tên đó lưu dạng chỉ-có-tên, không tạo dòng ma, không crash |
| Ô trống render thành `0` | MEDIUM — im lặng nói dối người đọc, đúng thứ D4 cấm | check khẳng định `null` ở tầng dữ liệu; phần render kiểm bằng demo tay |
| `index.html` lén phụ thuộc mạng | MEDIUM — phá D1/D2 mà không ai thấy | check khẳng định file không chứa `<script src=`, `fetch(`, `http://`, `https://` |
| Slug ảnh trùng nhau | LOW — đã đo: 0 trùng trên 653 tên | check khóa lại bất biến đó |

## Shape

| Phase | What Changes | Why Now | Demo | Unlocks |
|---|---|---|---|---|
| S1 — Bộ xương đi được | `tools/extract_cards.py`, `tools/check.py`, `index.html` (khung + khối dữ liệu + bảng tra cứu có tìm kiếm/lọc + ô ảnh placeholder) | Dữ liệu là rủi ro lớn nhất; chứng minh mạch trích-xuất → trang chạy end-to-end trước khi viết nội dung | Mở `index.html`, gõ `Dark Witch` → thấy số thứ tự, `1800/1700`, `Sun/Npt`, hệ fusion, và ô ảnh ghi rõ cần file `dark-witch.png`. (Card demo cố ý chọn lá **có** join đủ ba nguồn — `Blue-eyes White Dragon` xuất hiện 0 lần trong `fusion.md` nên chứng minh được gì.) | S2, S3 |
| S2 — Nội dung hướng dẫn | Mục hướng dẫn trong `index.html`: luật cơ bản, danh sách Type, bánh xe Guardian Star + luật +500, môi trường/field, giải thích Ritual, bộ bài khởi đầu, farm bài, password, cơ chế Pow/Tec. Responsive + in được làm luôn ở đây. | Đây là phần "hướng dẫn chơi" người dùng hỏi đầu tiên; độc lập với S3 | Đọc hết hướng dẫn không cần mở file `.md` nào | — |
| S3 — Tra cứu fusion + equip | Ba mục fusion (cơ bản / chính xác / xung đột) và danh sách equip theo từng lá, tra cứu hai chiều; bảng chi tiết một lá gộp mọi nguồn | Phần dữ liệu nặng nhất, cần bảng tra cứu của S1 làm nền | Chọn một lá → ghép ra nó bằng gì, nó ghép ra gì, equip được gì | S4 |
| S4 — Báo cáo độ phủ | Một mục trong trang tự khai: 653/722 lá có tên, ~96 lá có ATK/DEF sau join, 261/653 lá có hệ fusion, 26/37 nhóm có danh sách thành viên, 0 công thức Ritual | Chỉ có nghĩa khi cả ba nguồn đã vào trang; đây là thứ giữ D4 trung thực với người đọc | Trang nói rõ chỗ nào còn trống thay vì giả vờ đủ | — |

**Slice hiện tại chuẩn bị cell: S1.**

## Test matrix

`commands.test` khai báo là `python3 tools/check.py` (repo chưa có test nào; đây là suite đầu tiên). Extractor trong test chạy ra **thư mục tạm** rồi so sánh, không bao giờ ghi đè file giao hàng.

- **Happy path** — extractor chạy trên `docs/guide/` thật: đúng **653** cặp số↔tên, **101** lá có ATK/DEF, **≥96** lá join được cả số lẫn ATK/DEF, **261** lá có hệ fusion; `index.html` chứa khối giữa hai marker và khối đó parse được.
- **D1/D2 structural** — `index.html` không chứa `<script src=`, không `fetch(`, không `http://`, không `https://`, không `import ` ở tầng module.
- **D3** — slug sinh đúng cho tên có `#` (`Mystical Sheep #1`), `'` (`Harpie's Feather Duster`), `.` (`Stone D.`), `-` (`Blue-eyes White Dragon`), `,` (`30,000-Year White Turtle`); **0 slug trùng nhau** trên toàn bộ 653 tên; slug chỉ chứa `a-z0-9-`.
- **D4** — ATK/DEF thiếu lưu `null`, không phải `0`; ba alias (`Blue-eyed Silver Zombie`, `Doma The Angel of Silence`, `Stone D.`) join đúng số thứ tự; công thức trỏ tới tên không có `#NNN` lưu được dạng chỉ-có-tên, không tạo dòng ma.
- **Edge cases nguồn** — `#395 Dancing Elf` (dòng tiêu đề dị dạng) vẫn vào bảng; dòng cột lệch (`Wicked Dragon with the Ersatz Head   Trap Master`) tách đúng hai tên; dòng văn xuôi ngoài code fence không lọt vào danh sách tên; `#721` không sinh dòng ma.
- **Idempotent** — chạy extractor hai lần cho ra byte y hệt.
- **Không có test cho D5** (ngôn ngữ) — kiểm bằng đọc, ghi nhận ở đây thay vì bỏ lửng.

## Out of scope

- Bảng công thức Ritual triệu hồi thật — không có nguồn trong repo (deferred, CONTEXT.md).
- Bảng drop bài theo đối thủ và password list đầy đủ — nguồn chỉ có ~13 dòng.
- Tải ảnh lá bài về — người dùng tự đổ vào `images/cards/`.
- Điền tay 69 lá thiếu số thứ tự, các ô ATK/DEF trống, và 11 nhóm hệ không có danh sách thành viên — để người dùng bổ sung sau, đúng D4.
