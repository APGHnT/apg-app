"""Kiểm tra hook giao_dich trên PocketBase đang chạy (sau khi đã nạp dữ liệu mẫu).

    python tests/kiem_tra_hook.py http://127.0.0.1:8090   (cần PB_EMAIL, PB_PASSWORD)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrate"))
from import_excel import PB  # noqa: E402

pb = PB(sys.argv[1], os.environ["PB_EMAIL"], os.environ["PB_PASSWORD"])
da = {x["ma"]: x["id"] for x in pb.tat_ca("du_an", "id,ma")}
cay = {x["ma"]: x["id"] for x in pb.tat_ca("cay_ma", "id,ma")}

hop_le = dict(du_an=da["MAUB"], loai="CHI", ngay="2026-02-01 00:00:00.000Z", noi_dung="KIỂM TRA",
              ma_cay=cay["0.02.02.02"], so_luong=3, don_gia=333.4, phan_bo="RIENG", thanh_tien=999999)

phai_loi = {
    "mã chưa xuống lá": dict(hop_le, ma_cay=cay["0.02.02"]),
    "THU dùng mã chi": dict(hop_le, loai="THU"),
    "thiếu dự án": dict(hop_le, du_an=""),
    "CHUNG gắn dự án": dict(hop_le, phan_bo="CHUNG"),
    "thiếu đơn giá": dict(hop_le, don_gia=0),
    "ngày trước khởi công": dict(hop_le, ngay="2026-01-01 00:00:00.000Z"),
    "xem lại không lý do": dict(hop_le, don_gia=0, can_xem_lai=True),
}
sai = 0
for ten, body in phai_loi.items():
    try:
        pb.tao("giao_dich", body)
        print("✗ lẽ ra phải bị chặn:", ten)
        sai += 1
    except RuntimeError as ex:
        ok = "→ 400" in str(ex)
        print(("✓ bị chặn: " if ok else "✗ lỗi lạ: ") + ten)
        sai += not ok

r = pb.tao("giao_dich", hop_le)
if r["thanh_tien"] != 1000:  # 3 × 333,4 = 1000,2 → làm tròn 1000, bỏ qua giá trị nhập tay 999999
    print("✗ thành tiền tính sai:", r["thanh_tien"])
    sai += 1
else:
    print("✓ thành tiền do máy tính và làm tròn: 1000")
pb.call("DELETE", f"/api/collections/giao_dich/records/{r['id']}")

r = pb.tao("giao_dich", dict(hop_le, don_gia=0, can_xem_lai=True, ly_do_xem_lai="chưa có hoá đơn"))
print("✓ dòng thiếu giá được lưu khi có lý do xem lại")
pb.call("DELETE", f"/api/collections/giao_dich/records/{r['id']}")

sys.exit(1 if sai else 0)
