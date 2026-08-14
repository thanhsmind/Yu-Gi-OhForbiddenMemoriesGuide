# Learnings — fm-guide-site (2026-08-14)

Bốn cell trên tab tra cứu bài: popup chi tiết hai cột + chuyển lá (17, 18), bộ
chọn cỡ lưới 4/6/8 (19), sắp xếp theo số/ATK/DEF (20). Tất cả xanh
`python3 tools/check.py`, gộp về main qua worktree.

## 1. "Số cột người dùng chọn" nên là trần, và trần đó viết được bằng CSS thuần

Yêu cầu là chọn lưới 4/6/8 ô. Cách hiển nhiên — `repeat(4, 1fr)` — đúng trên màn
rộng và hỏng trên điện thoại: tám ô nhét vào 360px thành tám con tem không nhìn
được. Cách hay bị chọn tiếp theo là nghe `resize` rồi tính số cột bằng JS, hoặc
đẻ ra một dãy `@media` cho từng mức.

Cả hai đều không cần. Giữ nguyên `auto-fill` và chỉ đổi *mức tối thiểu* của track:

```css
grid-template-columns: repeat(auto-fill, minmax(max(110px, calc((100% - (N - 1) * <gap>) / N)), 1fr));
```

Bề rộng lý tưởng của N cột lớn hơn 110px thì `auto-fill` rơi đúng vào N cột; màn
hẹp thì 110px thắng và trình duyệt tự bớt cột. Không listener, không breakpoint,
không đo bằng JS — và mức người dùng chọn vẫn hiện nguyên trên nút, vì nó là
trần chứ không phải mệnh lệnh.

**Rút ra:** khi một lựa chọn số lượng phải nhường màn hình nhỏ, hỏi xem CSS có
diễn đạt được nó dưới dạng *ràng buộc* không, trước khi viết JS diễn đạt nó dưới
dạng *phép tính*. `max()`/`calc()` bên trong `minmax()` biến "đúng N cột" thành
"tối đa N cột" mà không thêm dòng JS nào.

## 2. Một danh sách đã sắp duy nhất, mọi thứ khác ăn theo

Sắp xếp đặt ngay trong `applyFilters()`, ghi thẳng vào `state.filtered`, trước
khi reset trang và render. Hệ quả là không phải sửa thêm gì: phân trang, số đếm,
bảng, lưới, và hai nút "lá trước / lá sau" trong popup đều đọc cùng mảng đó nên
tự đi theo thứ tự mới.

Đường sai đối xứng — sắp xếp bên trong `render()` hoặc bên trong từng chế độ
xem — cũng cho ra màn hình đúng, nhưng lúc đó popup và phân trang lại đi theo
thứ tự cũ, và hai chế độ xem có thể lệch nhau. Cùng một lỗi tư duy đã tránh được
ở cell 17 (lưới và bảng dùng chung một bộ lọc, một phân trang) và cell 18 (nút
chuyển lá đọc `state.filtered` chứ không đọc toàn bộ `CARDS`).

**Rút ra:** với một trang có nhiều khung nhìn, đặt câu hỏi "danh sách thật nằm ở
đâu" và chỉ cho phép một câu trả lời. Thêm bộ lọc, thêm sắp xếp, thêm chế độ
xem — tất cả sửa cùng một mảng, còn khung nhìn chỉ chọn cách vẽ.

## 3. Worker viết được hay không là do session cha đứng ở đâu

Cell 19 bị `[BLOCKED]` nguyên một lượt dispatch. Không phải vì thiết kế sai —
worker đã map xong toàn bộ chỗ cần sửa — mà vì write-guard của repo lấy gốc theo
`CLAUDE_PROJECT_DIR` của session cha. Session cha đứng ở main checkout, file lại
nằm trong worktree của feature, nên mọi lệnh ghi đều bị từ chối y hệt nhau, kể
cả `touch`.

Cách chữa là session cha vào worktree *trước khi* dispatch; sau đó cùng payload
đó chạy trót lọt. Dấu hiệu nhận ra sớm: worker báo bị chặn ở *mọi* đường ghi,
kể cả đường tầm thường nhất — đó là môi trường, không phải phạm vi hay thiết kế.

**Rút ra:** khi một worker báo blocked, phân loại trước theo "chặn đồng đều hay
chặn chọn lọc". Chặn đồng đều thì đừng sửa cell, đừng lên tier — sửa chỗ đứng
rồi dispatch lại.

## 4. Bug được báo có thể là mắt đọc nhầm, không phải code sai

Người dùng báo "sắp xếp ATK nhưng lấy số DEF". Bốn ô đầu trên ảnh chụp có DEF là
2000 / 3000 / 3000 — trông rất giống một dãy tăng dần. Tính lại thứ tự đúng từ
chính dữ liệu trong `index.html` rồi đặt cạnh ảnh cho thấy ATK là 0 / 0 / 0 / 200,
khớp từng ô: code đúng, DEF tăng dần chỉ là trùng hợp.

Chi phí kiểm chứng là một đoạn script đọc dữ liệu và in sáu dòng — rẻ hơn nhiều
so với sửa một comparator vốn không hỏng.

**Rút ra:** với báo lỗi về thứ tự hay số liệu, tính lại kết quả đúng từ nguồn dữ
liệu rồi đối chiếu từng dòng với cái người dùng đang nhìn, trước khi mở code
comparator ra sửa. Và ghi nhận điều màn hình đang không nói: lưới ảnh không hiện
giá trị đang sắp xếp, nên mắt phải tự dò trong ảnh mặt bài — đó là khoảng trống
sản phẩm, đã đưa vào backlog.
