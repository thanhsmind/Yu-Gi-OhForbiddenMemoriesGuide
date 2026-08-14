# fm-guide-site — nguồn CardFusionExplorer (2026-08-14)

Ba lát, bảy cell, một buổi. Nguồn thứ tư vào trang: bảng công thức đầy đủ, lá
ngoài Forbidden Memories, và ảnh mặt thứ hai.

## Đã giao

| Lát | Cell | Kết quả |
|---|---|---|
| 1 | 23, 24, 25 | Bảng Chính xác từ 150 lên 25.504 công thức; phân trang cả bảng lẫn Fusion List |
| 2 | 26, 27 | 360 lá ngoài FM vào bảng tra cứu; khoá tra cứu đổi từ số sang slug |
| 3 | 28, 29 | 1.056 ảnh WebP (22MB); bấm ảnh trong popup để đảo hai mặt |

`index.html` 1,68MB → 2,13MB. `python3 tools/check.py` xanh ở mọi cap và ở close.

## Bài học

### Đếm dòng nguồn không phải đếm thực thể

`fusion_unique.json` lưu **mỗi công thức theo cả hai chiều** — `A+B` và `B+A`
là hai dòng của cùng một thứ. Tôi báo cho người dùng "50.283 công thức" dựa
trên số dòng, và con số đó sai gấp đôi. Chỉ phát hiện khi chuẩn hoá cặp để mã
hoá.

Nguy hiểm ở chỗ số này đã đi vào một quyết định đã khoá (D9) và suýt vào một
ràng buộc bất biến của `check.py` — trang sẽ tự hào khoe một con số nói dối
gấp đôi. Sửa bằng supersede, không sửa lặng.

Quy tắc rút ra: **trước khi báo bất kỳ con số phủ dữ liệu nào, chuẩn hoá về
thực thể logic rồi mới đếm.** Số dòng, số bản ghi, số file đều là proxy —
proxy sai khi nguồn có dư thừa có chủ ý (hai chiều, nhiều ngôn ngữ, nhiều
phiên bản).

### Dữ liệu mới phá giả định về cỡ ở tầng render

150 công thức render thẳng vào DOM là bình thường. 25.504 thì treo trang. Và
số cực đoan không nằm ở tổng mà ở phân bố: trung vị là 16 công thức một lá,
nhưng `Nekogal #2` có **1.200** công thức ghép ra nó.

Khi thay một nguồn dữ liệu, đo **phân bố** chứ không chỉ đo tổng — chỗ vỡ nằm
ở đuôi. Ở đây nó biến hai cell UI từ "đọc trường mới" thành "thêm phân trang".

### Khoá tra cứu phải chịu được bản ghi thiếu khoá đó

`byNumber[c.number]` chạy hoàn hảo 722 lá. Thêm 360 lá không có số thì tất cả
gom vào một khoá `"undefined"`: popup mở nhầm lá, nút trước/sau lệch, khôi
phục từ địa chỉ hỏng — âm thầm, không lỗi nào ném ra.

Khi một tập dữ liệu mở rộng sang nhóm thiếu trường định danh cũ, đổi khoá
sang trường mọi bản ghi đều có (ở đây là slug) và giữ khoá cũ chỉ như một
đường vào tương thích ngược cho địa chỉ đã lưu.

### Reservation của cell đã cap không tự nhả

Cell 26 báo `[BLOCKED]` vì `index.html` còn bị giữ bởi cell 23/24/25 — cả ba
đã cap và đã commit. Worker làm đúng: không ghi xuyên qua guard, báo lại.
Orchestrator phải quét (`bee reservations release`) trước khi dispatch lát
tiếp theo, hoặc dispatch sẽ chết ở cell đầu tiên chạm file dùng chung.

## Chưa làm được

Không có mắt người xem trang thật: extension Chrome không kết nối. Phân trang,
việc đảo ảnh và bộ lọc phạm vi chỉ được xác nhận qua smoke test bằng node và
qua `check.py` — cả hai đều không mở DOM. Đây là Open Gap đã ghi vào
`docs/specs/guide-site.md`.

## Nợ đã ghi

- Lá 683–685 dịch *monster* thành "Quái thú" viết hoa, lọt qua guard thuật ngữ
  vì guard phân biệt hoa/thường (backlog, P3).
