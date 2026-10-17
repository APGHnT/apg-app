# APG App – quản lý thu chi dự án An Phát Group

Thay hệ thống hơn 100 file Excel (`TỔNG HỢP/<năm>/<mã dự án>/…`) bằng **một database PocketBase** đặt trên NAS. App Flutter (Android, iOS, Windows, macOS) và Claude cùng đọc/ghi vào database này.

```
App Flutter ─┐
Claude /nhap ┼──► PocketBase (NAS) ──► báo cáo, tra cứu, xuất Excel
Script nạp  ─┘
```

## Cấu trúc repo

| Thư mục | Nội dung |
|---|---|
| `pocketbase/pb_migrations/` | Tạo các bảng `du_an`, `cay_ma`, `map_cu`, `giao_dich`, `chung_tu` và báo cáo `tong_du_an` |
| `pocketbase/pb_hooks/` | Kiểm tra mỗi giao dịch khi lưu (thay cột KIEM_TRA của Excel) |
| `pocketbase/sql/` | Câu SQL báo cáo theo dự án (thu, chi trực tiếp, chi phí chung được chia) |
| `migrate/` | Chuyển dữ liệu từ Excel sang database và đối chiếu với `TONG_HOP.xlsx` |
| `tests/` | Dữ liệu mẫu và các bài kiểm tra chạy tự động trên GitHub |
| `app/` | App Flutter (Richard tự viết theo lộ trình học) |

## Quy tắc kiểm tra khi lưu giao dịch

Mọi nguồn ghi (app, Claude, script, trang quản trị) đều đi qua cùng một hook:

1. **Thành tiền** do máy tính = số lượng × đơn giá, làm tròn đến đồng. Không nhập tay.
   - **Số âm** hợp lệ: tiền thừa nhận về, trừ ứng, chiết khấu.
   - **Đã huỷ** (`trang_thai = DA_HUY`): giao dịch có thật nhưng bị huỷ. Vẫn lưu, giữ SL/ĐG đã ghi để tra lại, nhưng thành tiền luôn bằng 0. Khi chuyển dữ liệu từ Excel, mọi dòng có thành tiền bằng 0 đều được ghi là đã huỷ.
2. **Mã cây** phải có trong cây và đã xuống lá. THU dùng nhánh `1`, CHI dùng nhánh `0.xx`.
3. **RIENG** phải có dự án. **CHUNG** không gắn dự án và phải có ngày, vì chi phí chung được chia đều cho các dự án đang chạy vào ngày đó.
4. Dòng bình thường phải có ngày, số lượng, đơn giá, và ngày phải nằm trong thời gian dự án.
5. Dòng chưa đủ thông tin vẫn lưu được nếu bật `can_xem_lai` và ghi `ly_do_xem_lai`.

## Chạy thử không cần PocketBase (SQLite)

```bash
pip install -r migrate/requirements.txt
python migrate/import_excel.py "đường/dẫn/TỔNG HỢP" --sqlite thu.db --xem-lai can_xem_lai.csv
python migrate/doi_chieu.py "đường/dẫn/TỔNG HỢP/TONG_HOP.xlsx" --sqlite thu.db
```

Kết quả trên bộ backup 17/10/2026 (950 dòng): khớp TONG_HOP từng dự án, lệch dưới 1 đồng do làm tròn thành tiền. Có 15 giao dịch đã huỷ (0 đ) và 17 dòng cần xem lại (nghi trùng, ngày sai năm, thu chưa có ngày).

## Chạy với PocketBase

```bash
cd pocketbase
# tải bản PocketBase 0.40.5 cho máy của mình vào thư mục này
./pocketbase superuser upsert email@cuaanh.vn MatKhauManh
./pocketbase serve            # migration + hook tự chạy
# ở cửa sổ khác:
python migrate/import_excel.py "…/TỔNG HỢP" --pb http://127.0.0.1:8090 --email … --password …
python migrate/doi_chieu.py "…/TỔNG HỢP/TONG_HOP.xlsx" --pb http://127.0.0.1:8090 --email … --password …
```

Chạy lại script nạp nhiều lần vẫn an toàn: dòng đã có (cùng `file#dòng`) sẽ được bỏ qua.

## Kiểm tra tự động (GitHub Actions)

Mỗi lần đẩy code, GitHub sẽ dựng một PocketBase tạm, tạo dữ liệu mẫu, nạp vào, rồi kiểm tra:
- tổng thu/chi và chi phí chung khớp 0 đồng;
- chạy nạp lần 2 không bị nhân đôi;
- hook chặn đúng các dòng sai.

Dữ liệu thật **không** nằm trong repo (`data/` có trong `.gitignore`). Muốn kiểm tra cả dữ liệu thật trên GitHub thì đặt thư mục vào `data/TỔNG HỢP/`, bỏ dòng `data/` trong `.gitignore`, và chỉ làm vậy khi repo đang để private.
