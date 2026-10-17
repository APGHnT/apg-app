"""Đóng gói bộ cài PocketBase cho NAS: dist/apg-pocketbase/ và dist/apg-pocketbase.zip

    python nas/dong_goi.py

Giải nén zip vào thư mục docker/apg-pocketbase trên NAS (các file nằm ngay trong thư mục, không lồng thêm cấp).
"""
import os
import shutil
import zipfile

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(GOC, "dist")
OUT = os.path.join(DIST, "apg-pocketbase")

HUONG_DAN = """BỘ CÀI POCKETBASE – APG (NAS Synology)

1. File Station: giải nén file zip này vào  docker/apg-pocketbase
   (sau khi giải nén phải thấy: Dockerfile, compose.yaml, pb_data, pb_hooks, pb_migrations)
2. Container Manager → Project → Create
     Project name : apg-pocketbase
     Path         : /docker/apg-pocketbase
     Source       : Use existing docker-compose.yml (compose.yaml)
   → Next → (bỏ qua Web portal) → Done. Lần đầu sẽ build khoảng 1–3 phút.
3. Container Manager → Container → apg-pocketbase → Log:
   tìm dòng có  http://0.0.0.0:8090/_/#/pbinstall/...  (link tạo tài khoản quản trị lần đầu,
   link chỉ dùng được trong thời gian ngắn – làm ngay sau khi container chạy)
   copy, thay 0.0.0.0 bằng IP của NAS, mở bằng trình duyệt, tạo email + mật khẩu MẠNH.
4. Trang quản trị: http://<IP-NAS>:8090/_/   (chỉ trong mạng nội bộ)

DỮ LIỆU nằm trong thư mục pb_data – đưa vào Hyper Backup.
Không sửa tay pb_migrations / pb_hooks – cập nhật bằng bộ cài mới từ GitHub.
"""


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    for f in ("Dockerfile", "compose.yaml"):
        shutil.copy(os.path.join(GOC, "nas", f), OUT)
    for d in ("pb_migrations", "pb_hooks"):
        shutil.copytree(os.path.join(GOC, "pocketbase", d), os.path.join(OUT, d))
    os.makedirs(os.path.join(OUT, "pb_data"))
    open(os.path.join(OUT, "pb_data", ".giu_thu_muc"), "w").close()
    with open(os.path.join(OUT, "HUONG_DAN.txt"), "w", encoding="utf-8") as f:
        f.write(HUONG_DAN)

    z = os.path.join(DIST, "apg-pocketbase.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for r, ds, fs in os.walk(OUT):
            for d in ds:
                p = os.path.join(r, d)
                zf.write(p, os.path.relpath(p, OUT) + "/")
            for f in fs:
                p = os.path.join(r, f)
                zf.write(p, os.path.relpath(p, OUT))
    print("Đã đóng gói:", z)


if __name__ == "__main__":
    main()
