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

## Trang tra cứu bài chỉ có MỘT danh sách thật

`state.filtered` là danh sách đã lọc và đã sắp; bảng, lưới, phân trang, số đếm,
và nút chuyển lá trong popup đều đọc nó. Thêm bộ lọc, sắp xếp hay chế độ xem
mới thì sửa chính mảng đó trong `applyFilters()` — không sắp xếp lại bên trong
`render()`, không dựng danh sách song song, không thêm đường phân trang thứ hai.
(2026-08-14, cell fm-guide-site-20; nối tiếp cell 17 và 18)
