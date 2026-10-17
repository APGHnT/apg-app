# App Flutter

Chỗ dành cho app Flutter. Richard tự viết theo lộ trình học (tuần 3–5: giao diện, tuần 6–7: kết nối PocketBase).

Bản 1 cần có:
1. Đăng nhập (bảng `users` của PocketBase)
2. Danh sách dự án → xem `tong_du_an` (thu, chi trực tiếp, chi chung, lãi/lỗ)
3. Nhập một giao dịch: chọn dự án, chọn mã cây (chỉ mã lá), nội dung, SL, đơn giá, người trả, ảnh chứng từ
4. Danh sách dòng `can_xem_lai = true` để xử lý dần

Thư viện kết nối: gói `pocketbase` trên pub.dev (kiểm tra phiên bản tương thích với PocketBase 0.40 trước khi dùng).
