"""Kiểm tra cột người nhập / người sửa và quyền của tài khoản thường (users).

    python tests/kiem_tra_nguoi_nhap.py http://127.0.0.1:8090   (cần PB_EMAIL, PB_PASSWORD; đã nạp dữ liệu mẫu)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrate"))
from import_excel import PB  # noqa: E402

URL = sys.argv[1]
admin = PB(URL, os.environ["PB_EMAIL"], os.environ["PB_PASSWORD"])
da = {x["ma"]: x["id"] for x in admin.tat_ca("du_an", "id,ma")}
cay = {x["ma"]: x["id"] for x in admin.tat_ca("cay_ma", "id,ma")}

email, mk = "nguoinhap.thu@apg.local", "MatKhauThu-67890"
try:
    admin.tao("users", {"email": email, "password": mk, "passwordConfirm": mk, "verified": True})
except RuntimeError:
    pass  # đã có từ lần chạy trước


class User(PB):
    def __init__(self, url, email, password):
        self.url, self.token = url.rstrip("/"), None
        self.token = self.call("POST", "/api/collections/users/auth-with-password",
                               {"identity": email, "password": password})["token"]


nv = User(URL, email, mk)
sai = 0


def ky_vong(ten, ok, thuc=""):
    global sai
    print(("✓ " if ok else "✗ ") + ten + (f": {thuc}" if thuc != "" else ""))
    sai += not ok


gd = dict(du_an=da["MAUB"], loai="CHI", ngay="2026-02-01 00:00:00.000Z", noi_dung="KIỂM TRA NGƯỜI NHẬP",
          ma_cay=cay["0.02.02.02"], so_luong=2, don_gia=1000, phan_bo="RIENG", trang_thai="HIEU_LUC",
          nguoi_tao="gia.mao@x.com", nguoi_sua="gia.mao@x.com")

r = nv.tao("giao_dich", gd)
ky_vong("Nhân viên nhập → người nhập là nhân viên (không giả được)", r["nguoi_tao"] == email, r["nguoi_tao"])
ky_vong("Nhân viên nhập → người sửa là nhân viên", r["nguoi_sua"] == email, r["nguoi_sua"])

r2 = admin.call("PATCH", f"/api/collections/giao_dich/records/{r['id']}", {"so_luong": 3, "nguoi_tao": "khac@x.com"})
ky_vong("Quản trị sửa → người nhập giữ nguyên", r2["nguoi_tao"] == email, r2["nguoi_tao"])
ky_vong("Quản trị sửa → người sửa là quản trị", r2["nguoi_sua"] == os.environ["PB_EMAIL"], r2["nguoi_sua"])

r3 = nv.call("PATCH", f"/api/collections/giao_dich/records/{r['id']}", {"trang_thai": "DA_HUY"})
ky_vong("Nhân viên huỷ giao dịch được, thành tiền về 0", r3["thanh_tien"] == 0 and r3["nguoi_sua"] == email)

try:
    nv.call("DELETE", f"/api/collections/giao_dich/records/{r['id']}")
    ky_vong("Nhân viên KHÔNG xoá được giao dịch", False)
except RuntimeError as ex:
    ky_vong("Nhân viên KHÔNG xoá được giao dịch", True, str(ex).split(":")[0])

ds = nv.call("GET", "/api/collections/users/records")
ky_vong("Nhân viên chỉ thấy tài khoản của mình", len(ds["items"]) == 1, len(ds["items"]))

admin.call("DELETE", f"/api/collections/giao_dich/records/{r['id']}")  # dọn: không làm lệch đối chiếu
sys.exit(1 if sai else 0)
