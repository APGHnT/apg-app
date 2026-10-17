"""Chuyển dữ liệu Excel 'TỔNG HỢP' sang PocketBase (hoặc sang SQLite để chạy thử).

Chạy thử, không cần PocketBase (tạo file SQLite có cùng bảng + báo cáo):
    python migrate/import_excel.py "data/TỔNG HỢP" --sqlite thu.db

Đẩy vào PocketBase thật:
    python migrate/import_excel.py "data/TỔNG HỢP" --pb http://127.0.0.1:8090 \
        --email admin@... --password ...

Chạy lại nhiều lần an toàn: giao dịch đã có (cùng ma_import = file#dòng) sẽ được bỏ qua.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from doc_excel import doc_thu_muc, la_cua  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_BAO_CAO = os.path.join(GOC, "pocketbase", "sql", "tong_du_an.sql")


def pb_ngay(s):
    return f"{s} 00:00:00.000Z" if s else ""


# ---------------------------------------------------------------- SQLite (chạy thử)


def ghi_sqlite(bo, path):
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.executescript("""
    CREATE TABLE du_an (id TEXT PRIMARY KEY, ma TEXT, ten TEXT, dia_chi TEXT,
        khoi_cong TEXT, ket_thuc TEXT DEFAULT '', ghi_chu TEXT);
    CREATE TABLE cay_ma (id TEXT PRIMARY KEY, ma TEXT, ten TEXT, ma_cha TEXT, cap INT, la INT, ghi_chu TEXT);
    CREATE TABLE map_cu (id TEXT PRIMARY KEY, cong_tac TEXT, cong_doan TEXT, ma_cay TEXT);
    CREATE TABLE giao_dich (id TEXT PRIMARY KEY, du_an TEXT DEFAULT '', loai TEXT, ngay TEXT DEFAULT '',
        noi_dung TEXT, ma_cay TEXT, dvt TEXT, so_luong REAL, don_gia REAL, thanh_tien REAL,
        nguon_tien TEXT, phan_bo TEXT, nha_cc TEXT, quy_cach TEXT, ghi_chu TEXT,
        ma_import TEXT UNIQUE, nguon_goc TEXT, can_xem_lai INT, ly_do_xem_lai TEXT);
    """)
    la = la_cua(bo.cay)
    for d in bo.du_an:
        db.execute("INSERT INTO du_an VALUES (?,?,?,?,?,?,?)",
                   (d.ma, d.ma, d.ten, d.dia_chi, pb_ngay(d.khoi_cong), pb_ngay(d.ket_thuc), d.ghi_chu))
    for c in bo.cay:
        db.execute("INSERT INTO cay_ma VALUES (?,?,?,?,?,?,?)",
                   (c.ma, c.ma, c.ten, c.ma_cha, c.cap, int(la[c.ma]), c.ghi_chu))
    for (ct, cd), ma in bo.map_cu.items():
        db.execute("INSERT INTO map_cu VALUES (?,?,?,?)", (f"{ct}|{cd}", ct, cd, ma))
    for g in bo.giao_dich:
        db.execute("INSERT INTO giao_dich VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            g.ma_import, g.du_an, g.loai, pb_ngay(g.ngay), g.noi_dung, g.ma_cay, g.dvt,
            g.so_luong or 0, g.don_gia or 0, g.thanh_tien, g.nguon_tien, g.phan_bo, g.nha_cc,
            g.quy_cach, g.ghi_chu, g.ma_import, g.nguon_goc, int(bool(g.ly_do)), "; ".join(g.ly_do)))
    with open(SQL_BAO_CAO, encoding="utf-8") as f:
        db.execute("CREATE VIEW tong_du_an AS " + f.read())
    db.commit()
    db.close()


# ---------------------------------------------------------------- PocketBase


class PB:
    def __init__(self, url, email, password):
        self.url = url.rstrip("/")
        self.token = None
        r = self.call("POST", "/api/collections/_superusers/auth-with-password",
                      {"identity": email, "password": password})
        self.token = r["token"]

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", self.token)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as ex:
            raise RuntimeError(f"{method} {path} → {ex.code}: {ex.read().decode(errors='replace')}") from None

    def tat_ca(self, col, fields="id"):
        out, page = [], 1
        while True:
            q = urllib.parse.urlencode({"page": page, "perPage": 500, "fields": fields, "skipTotal": 1})
            r = self.call("GET", f"/api/collections/{col}/records?{q}")
            out += r["items"]
            if len(r["items"]) < 500:
                return out
            page += 1

    def tao(self, col, body):
        return self.call("POST", f"/api/collections/{col}/records", body)


def ghi_pocketbase(bo, pb: PB):
    la = la_cua(bo.cay)

    co = {x["ma"]: x["id"] for x in pb.tat_ca("du_an", "id,ma")}
    for d in bo.du_an:
        if d.ma not in co:
            co[d.ma] = pb.tao("du_an", {"ma": d.ma, "ten": d.ten, "dia_chi": d.dia_chi,
                                        "khoi_cong": pb_ngay(d.khoi_cong), "ket_thuc": pb_ngay(d.ket_thuc),
                                        "ghi_chu": d.ghi_chu})["id"]
    id_da = co

    id_cay = {x["ma"]: x["id"] for x in pb.tat_ca("cay_ma", "id,ma")}
    for c in bo.cay:
        if c.ma not in id_cay:
            id_cay[c.ma] = pb.tao("cay_ma", {"ma": c.ma, "ten": c.ten, "ma_cha": c.ma_cha, "cap": c.cap,
                                             "la": la[c.ma], "ghi_chu": c.ghi_chu})["id"]

    co_map = {(x["cong_tac"], x["cong_doan"]) for x in pb.tat_ca("map_cu", "cong_tac,cong_doan")}
    for (ct, cd), ma in bo.map_cu.items():
        if (ct, cd) not in co_map:
            pb.tao("map_cu", {"cong_tac": ct, "cong_doan": cd, "ma_cay": id_cay[ma]})

    da_co = {x["ma_import"] for x in pb.tat_ca("giao_dich", "ma_import")}
    moi = bo_qua = 0
    for g in bo.giao_dich:
        if g.ma_import in da_co:
            bo_qua += 1
            continue
        pb.tao("giao_dich", {
            "du_an": id_da[g.du_an] if g.du_an else "", "loai": g.loai, "ngay": pb_ngay(g.ngay),
            "noi_dung": g.noi_dung, "ma_cay": id_cay[g.ma_cay], "dvt": g.dvt,
            "so_luong": g.so_luong or 0, "don_gia": g.don_gia or 0,
            "nguon_tien": g.nguon_tien, "phan_bo": g.phan_bo, "nha_cc": g.nha_cc,
            "quy_cach": g.quy_cach, "ghi_chu": g.ghi_chu, "ma_import": g.ma_import,
            "nguon_goc": g.nguon_goc, "can_xem_lai": bool(g.ly_do), "ly_do_xem_lai": "; ".join(g.ly_do),
        })
        moi += 1
    return moi, bo_qua


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("thu_muc", help="thư mục 'TỔNG HỢP'")
    ap.add_argument("--sqlite")
    ap.add_argument("--pb")
    ap.add_argument("--email", default=os.environ.get("PB_EMAIL"))
    ap.add_argument("--password", default=os.environ.get("PB_PASSWORD"))
    ap.add_argument("--xem-lai", help="ghi danh sách dòng cần xem lại ra file CSV")
    a = ap.parse_args()
    if not (a.sqlite or a.pb):
        ap.error("cần --sqlite hoặc --pb")

    bo = doc_thu_muc(a.thu_muc)
    for c in bo.canh_bao:
        print("CẢNH BÁO:", c)
    xl = [g for g in bo.giao_dich if g.ly_do]
    print(f"Đọc: {len(bo.du_an)} dự án, {len(bo.cay)} mã cây, {len(bo.map_cu)} map, "
          f"{len(bo.giao_dich)} giao dịch ({len(xl)} cần xem lại)")

    if a.xem_lai:
        import csv
        with open(a.xem_lai, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["file#dong", "du_an", "ngay", "noi_dung", "so_luong", "don_gia", "thanh_tien", "ly_do"])
            for g in xl:
                w.writerow([g.ma_import, g.du_an or "CHUNG", g.ngay, g.noi_dung, g.so_luong, g.don_gia,
                            g.thanh_tien, "; ".join(g.ly_do)])
        print("Danh sách cần xem lại:", a.xem_lai)

    if a.sqlite:
        ghi_sqlite(bo, a.sqlite)
        print("Đã ghi SQLite:", a.sqlite)
    if a.pb:
        if not (a.email and a.password):
            ap.error("cần --email/--password (hoặc PB_EMAIL/PB_PASSWORD)")
        moi, bo_qua = ghi_pocketbase(bo, PB(a.pb, a.email, a.password))
        print(f"PocketBase: thêm {moi} giao dịch, bỏ qua {bo_qua} đã có")


if __name__ == "__main__":
    main()
