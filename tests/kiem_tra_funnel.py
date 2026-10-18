"""Giả lập request đi qua Tailscale Funnel (gắn header Tailscale-Funnel-Request: ?1)
và kiểm tra: chức năng quản trị bị chặn, người dùng thường vẫn làm việc được.

    python tests/kiem_tra_funnel.py http://127.0.0.1:8090   (cần PB_EMAIL, PB_PASSWORD)
"""
import json
import os
import sys
import urllib.error
import urllib.request

URL = sys.argv[1].rstrip("/")
FUNNEL = {"Tailscale-Funnel-Request": "?1"}


def goi(method, path, body=None, headers=None, token=None):
    req = urllib.request.Request(URL + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if token:
        req.add_header("Authorization", token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}") if "json" in r.headers.get("Content-Type", "") else {}
    except urllib.error.HTTPError as ex:
        return ex.code, {}


sai = 0


def ky_vong(ten, thuc, mong):
    global sai
    ok = thuc in mong if isinstance(mong, tuple) else thuc == mong
    print(("✓ " if ok else "✗ ") + f"{ten}: {thuc}")
    sai += not ok


# Đăng nhập superuser TRONG LAN (không header) → được
s, r = goi("POST", "/api/collections/_superusers/auth-with-password",
           {"identity": os.environ["PB_EMAIL"], "password": os.environ["PB_PASSWORD"]})
ky_vong("LAN: superuser đăng nhập", s, 200)
tok_admin = r.get("token")

# Tạo 1 người dùng thường để thử
email, mk = "nhanvien.thu@apg.local", "MatKhauThu-12345"
goi("POST", "/api/collections/users/records",
    {"email": email, "password": mk, "passwordConfirm": mk}, token=tok_admin)

# Người lạ không tự đăng ký được (cả trong LAN lẫn qua Internet)
dk = {"email": "nguoila@x.com", "password": "12345678abc", "passwordConfirm": "12345678abc"}
ky_vong("Người lạ tự đăng ký qua Internet", goi("POST", "/api/collections/users/records", dk,
        headers={"X-Forwarded-For": "113.161.5.7"})[0], (400, 403))
ky_vong("Người lạ tự đăng ký trong LAN", goi("POST", "/api/collections/users/records", dk)[0], (400, 403))

# Qua Funnel: chặn quản trị
ky_vong("Funnel: mở trang quản trị /_/", goi("GET", "/_/", headers=FUNNEL)[0], 403)
ky_vong("Funnel: superuser đăng nhập", goi("POST", "/api/collections/_superusers/auth-with-password",
        {"identity": os.environ["PB_EMAIL"], "password": os.environ["PB_PASSWORD"]}, headers=FUNNEL)[0], 403)
ky_vong("Funnel: dùng token superuser lấy được trong LAN",
        goi("GET", "/api/collections/giao_dich/records", headers=FUNNEL, token=tok_admin)[0], 403)
ky_vong("Funnel: API cài đặt", goi("GET", "/api/settings", headers=FUNNEL, token=tok_admin)[0], 403)
ky_vong("Funnel: API sao lưu", goi("GET", "/api/backups", headers=FUNNEL, token=tok_admin)[0], 403)
ky_vong("Funnel: API cấu trúc bảng", goi("GET", "/api/collections/giao_dich", headers=FUNNEL)[0], 403)

# Qua Funnel: người dùng thường vẫn làm việc
ky_vong("Funnel: kiểm tra sống", goi("GET", "/api/health", headers=FUNNEL)[0], 200)
s, r = goi("POST", "/api/collections/users/auth-with-password", {"identity": email, "password": mk}, headers=FUNNEL)
ky_vong("Funnel: nhân viên đăng nhập", s, 200)
tok_nv = r.get("token")
s, r = goi("GET", "/api/collections/tong_du_an/records", headers=FUNNEL, token=tok_nv)
ky_vong("Funnel: nhân viên xem báo cáo dự án", s, 200)
ky_vong("Funnel: chưa đăng nhập thì không xem được dữ liệu",
        len(goi("GET", "/api/collections/giao_dich/records", headers=FUNNEL)[1].get("items", [])), 0)

# Tailscale bản cũ không có header Funnel: nhận diện qua X-Forwarded-For là IP công cộng
XFF_NGOAI = {"X-Forwarded-For": "113.161.5.7"}
ky_vong("XFF IP ngoài: mở /_/", goi("GET", "/_/", headers=XFF_NGOAI)[0], 403)
ky_vong("XFF IP ngoài: superuser đăng nhập", goi("POST", "/api/collections/_superusers/auth-with-password",
        {"identity": os.environ["PB_EMAIL"], "password": os.environ["PB_PASSWORD"]}, headers=XFF_NGOAI)[0], 403)
ky_vong("XFF IP ngoài: nhân viên xem báo cáo",
        goi("GET", "/api/collections/tong_du_an/records", headers=XFF_NGOAI, token=tok_nv)[0], 200)
ky_vong("XFF IP Tailscale riêng (100.x): mở /_/ được", goi("GET", "/_/", headers={"X-Forwarded-For": "100.101.102.103"})[0], 200)
ky_vong("XFF IP LAN: mở /_/ được", goi("GET", "/_/", headers={"X-Forwarded-For": "192.168.1.50"})[0], 200)
ky_vong("Trang chẩn đoán tạm đã gỡ", goi("GET", "/api/apg/chan-doan", headers=XFF_NGOAI)[0], 404)

# Trong LAN: trang quản trị vẫn mở được
ky_vong("LAN: mở trang quản trị /_/", goi("GET", "/_/")[0], 200)

sys.exit(1 if sai else 0)
