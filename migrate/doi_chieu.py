"""Đối chiếu báo cáo trong database với file TONG_HOP.xlsx cũ (sheet DU_AN).

    python migrate/doi_chieu.py "data/TỔNG HỢP/TONG_HOP.xlsx" --sqlite thu.db
    python migrate/doi_chieu.py "data/TỔNG HỢP/TONG_HOP.xlsx" --pb http://127.0.0.1:8090 --email .. --password ..

Thoát với mã 1 nếu bất kỳ dự án nào lệch quá --sai-so (đồng). Lệch nhỏ do làm tròn
thành tiền từng dòng đến đồng (Excel giữ số lẻ, database làm tròn).
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def doc_tong_hop(path):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    rows = wb["DU_AN"].iter_rows(values_only=True)
    hdr = list(next(rows))
    ix = {h: i for i, h in enumerate(hdr) if h}
    out = {}
    for r in rows:
        ma = r[ix["MA_DU_AN"]]
        if ma:
            out[str(ma)] = (float(r[ix["THU"]] or 0), float(r[ix["CHI"]] or 0))
    return out


def bao_cao_sqlite(path):
    db = sqlite3.connect(path)
    rows = db.execute("SELECT ma, thu, chi_truc_tiep, chi_chung FROM tong_du_an").fetchall()
    tong_chung = db.execute(
        "SELECT COALESCE(SUM(thanh_tien),0) FROM giao_dich WHERE phan_bo='CHUNG' AND loai='CHI'").fetchone()[0]
    return {r[0]: (r[1], r[2], r[3]) for r in rows}, tong_chung


def bao_cao_pb(url, email, password):
    from import_excel import PB
    pb = PB(url, email, password)
    rows = pb.tat_ca("tong_du_an", "ma,thu,chi_truc_tiep,chi_chung")
    chung = pb.tat_ca("giao_dich", "thanh_tien,phan_bo,loai")
    tong_chung = sum(x["thanh_tien"] for x in chung if x["phan_bo"] == "CHUNG" and x["loai"] == "CHI")
    return {r["ma"]: (r["thu"], r["chi_truc_tiep"], r["chi_chung"]) for r in rows}, tong_chung


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tong_hop")
    ap.add_argument("--sqlite")
    ap.add_argument("--pb")
    ap.add_argument("--email", default=os.environ.get("PB_EMAIL"))
    ap.add_argument("--password", default=os.environ.get("PB_PASSWORD"))
    ap.add_argument("--sai-so", type=float, default=1000, help="lệch tối đa cho phép mỗi dự án (đồng)")
    a = ap.parse_args()

    cu = doc_tong_hop(a.tong_hop)
    moi, tong_chung = bao_cao_sqlite(a.sqlite) if a.sqlite else bao_cao_pb(a.pb, a.email, a.password)

    loi = 0
    print(f"{'DỰ ÁN':<16}{'THU (Excel)':>18}{'THU (DB)':>18}{'lệch':>10}{'CHI (Excel)':>18}{'CHI (DB)':>18}{'lệch':>10}")
    for ma in sorted(set(cu) | set(moi)):
        t0, c0 = cu.get(ma, (0, 0))
        thu, ctt, cch = moi.get(ma, (0, 0, 0))
        c1 = ctt + cch
        dt_, dc = thu - t0, c1 - c0
        bad = abs(dt_) > a.sai_so or abs(dc) > a.sai_so or ma not in cu or ma not in moi
        loi += bad
        print(f"{ma:<16}{t0:>18,.0f}{thu:>18,.0f}{dt_:>10,.2f}{c0:>18,.0f}{c1:>18,.0f}{dc:>10,.2f}"
              + ("   ✗" if bad else "   ✓"))
    da_chia = sum(v[2] for v in moi.values())
    con = tong_chung - da_chia
    print(f"\nChi phí CHUNG: tổng {tong_chung:,.0f} · đã chia {da_chia:,.2f} · chưa chia được {con:,.2f}"
          + ("   ✗ (có ngày không dự án nào đang chạy)" if abs(con) > 1 else "   ✓"))
    if abs(con) > 1:
        loi += 1
    print("KẾT QUẢ:", "KHỚP" if not loi else f"LỆCH ở {loi} mục")
    sys.exit(1 if loi else 0)


if __name__ == "__main__":
    main()
