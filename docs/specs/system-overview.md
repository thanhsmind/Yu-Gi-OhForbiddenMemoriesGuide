# System Overview

Dự án này xuất bản **một trang hướng dẫn chơi Yu-Gi-Oh! Forbidden Memories**,
đọc được offline, không cần máy chủ, không gọi mạng lúc xem.

Sản phẩm giao cho người dùng chỉ gồm hai thứ: một file trang và một thư mục
ảnh. Mọi thứ còn lại trong repo là công cụ để dựng lại file trang đó.

## Các vùng

| Vùng | Việc nó làm |
|---|---|
| Trang hướng dẫn (`docs/specs/guide-site.md`) | Toàn bộ thứ người dùng nhìn thấy: tra cứu bài, hướng dẫn chơi, tra cứu fusion, báo cáo độ phủ dữ liệu |
| Nguồn dữ liệu | Hai nguồn tách vai: bộ dữ liệu bài 722 lá cho bảng tra cứu; ba tài liệu hướng dẫn tiếng Việt cho công thức fusion, danh sách trang bị và nội dung hướng dẫn |
| Công cụ sinh dữ liệu | Đọc hai nguồn, ghép lại, rồi ghi dữ liệu vào đúng một vùng đánh dấu bên trong trang. Chạy lại phải cho kết quả không đổi |

## Nguyên tắc xuyên suốt

- **Không bịa.** Trường không có nguồn thì hiện "chưa có dữ liệu", không hiện
  `0` và không để trống. Thứ dự án không có (công thức Ritual, bảng drop,
  password đầy đủ) được nói thẳng trên trang chứ không suy ra.
- **Trang tự chứa.** Không địa chỉ mạng, không mã hay phông chữ bên ngoài,
  không đọc file dữ liệu rời — vì trang phải chạy khi nhấp đúp vào file.
- **Số liệu thống kê đọc từ dữ liệu**, không gõ cứng vào nội dung.

Các ràng buộc trên được kiểm tra tự động bằng `commands.test`.
