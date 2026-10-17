"""Câu SQL báo cáo trong migration PocketBase phải giống hệt pocketbase/sql/tong_du_an.sql
(bản dùng để chạy thử bằng SQLite)."""
import os
import re
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
js = open(os.path.join(GOC, "pocketbase/pb_migrations/1760700000_khoi_tao.js"), encoding="utf-8").read()
sql = open(os.path.join(GOC, "pocketbase/sql/tong_du_an.sql"), encoding="utf-8").read()
m = re.search(r"viewQuery:\s*`(.*?)`", js, re.S)
norm = lambda s: " ".join(s.split())
if not m or norm(m.group(1)) != norm(sql):
    sys.exit("✗ viewQuery trong migration KHÁC pocketbase/sql/tong_du_an.sql")
print("✓ SQL báo cáo giống nhau")
