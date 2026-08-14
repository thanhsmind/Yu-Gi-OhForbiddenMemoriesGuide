# Critical Patterns

Mandatory pre-planning / pre-execution context for this repository.
bee-capturing appends hard-won patterns here; keep it short and current.

## Dispatch từ đúng chỗ đứng, nếu không worker không ghi được file

Feature work sống trong worktree `--wt--<slug>`, còn write-guard lấy gốc theo
`CLAUDE_PROJECT_DIR` của session cha. Session cha đứng ở main mà dispatch worker
sửa file trong worktree thì MỌI lệnh ghi bị từ chối, kể cả `touch` — worker báo
`[BLOCKED]` dù cell hoàn toàn đúng. Vào worktree trước, rồi mới dispatch.
Dấu hiệu: chặn đồng đều ở mọi đường ghi = môi trường, không phải phạm vi.
(2026-08-14, cell fm-guide-site-19)

## Đếm thực thể, không đếm dòng nguồn

Nguồn hay chứa dư thừa có chủ ý — công thức lưu cả hai chiều, bản ghi nhiều
ngôn ngữ, nhiều phiên bản của một thứ. Đếm dòng rồi báo ra là báo sai, và trang
này có ràng buộc "mọi con số hiển thị khớp số đếm lại từ dữ liệu" nên con số
sai sẽ được kiểm tra tự động bảo vệ. Chuẩn hoá về thực thể logic TRƯỚC khi báo
bất kỳ con số phủ dữ liệu nào, kể cả khi mới chỉ nói với người dùng.
Kèm theo: đo cả **phân bố**, không chỉ tổng — chỗ tầng render vỡ nằm ở đuôi.
(2026-08-14, cell fm-guide-site-23; `fusion_unique.json` 50.937 dòng = 25.504
công thức; trung vị 16 công thức/lá nhưng có lá 1.200)

## Nhả reservation trước khi dispatch lát tiếp theo

`bee cells finish` cap cell nhưng reservation của nó có thể còn giữ file. Lát
sau chạm cùng file thì worker báo `[BLOCKED]` dù cell hoàn toàn đúng và cell
giữ chỗ đã commit xong từ lâu. Orchestrator quét `bee reservations release
--cell <id> --agent <nick>` cho mọi cell đã cap trước khi dispatch.
(2026-08-14, cell fm-guide-site-26 bị chặn bởi cell 23/24/25)

## Trang tra cứu bài chỉ có MỘT danh sách thật

`state.filtered` là danh sách đã lọc và đã sắp; bảng, lưới, phân trang, số đếm,
và nút chuyển lá trong popup đều đọc nó. Thêm bộ lọc, sắp xếp hay chế độ xem
mới thì sửa chính mảng đó trong `applyFilters()` — không sắp xếp lại bên trong
`render()`, không dựng danh sách song song, không thêm đường phân trang thứ hai.
(2026-08-14, cell fm-guide-site-20; nối tiếp cell 17 và 18)
