"""Đóng dữ liệu Excel thành 1 file migration PocketBase, để nạp vào NAS mà không cần
chạy Python trên máy trong mạng nội bộ.

    python migrate/tao_migration_du_lieu.py "…/TỔNG HỢP" ra/1760800000_nap_du_lieu_cu.js

Chép file .js vào docker/apg-pocketbase/pb_migrations trên NAS → Restart container.
PocketBase chạy file này đúng 1 lần, trong 1 transaction (lỗi giữa chừng thì không ghi gì).
File chứa DỮ LIỆU THẬT – không đưa lên GitHub.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from doc_excel import doc_thu_muc, la_cua  # noqa: E402


def pb_ngay(s):
    return f"{s} 00:00:00.000Z" if s else ""


def main():
    goc, out = sys.argv[1], sys.argv[2]
    bo = doc_thu_muc(goc)
    for c in bo.canh_bao:
        print("CẢNH BÁO:", c)
    la = la_cua(bo.cay)
    data = {
        "du_an": [dict(ma=d.ma, ten=d.ten, dia_chi=d.dia_chi, khoi_cong=pb_ngay(d.khoi_cong),
                       ket_thuc=pb_ngay(d.ket_thuc), ghi_chu=d.ghi_chu) for d in bo.du_an],
        "cay_ma": [dict(ma=c.ma, ten=c.ten, ma_cha=c.ma_cha, cap=c.cap, la=la[c.ma], ghi_chu=c.ghi_chu)
                   for c in bo.cay],
        "map_cu": [dict(cong_tac=ct, cong_doan=cd, ma_cay=ma) for (ct, cd), ma in bo.map_cu.items()],
        "giao_dich": [dict(
            du_an=g.du_an, loai=g.loai, ngay=pb_ngay(g.ngay), noi_dung=g.noi_dung, ma_cay=g.ma_cay,
            dvt=g.dvt, so_luong=g.so_luong or 0, don_gia=g.don_gia or 0, thanh_tien=g.thanh_tien,
            nguon_tien=g.nguon_tien, phan_bo=g.phan_bo, trang_thai=g.trang_thai, nha_cc=g.nha_cc,
            quy_cach=g.quy_cach, ghi_chu=g.ghi_chu, ma_import=g.ma_import, nguon_goc=g.nguon_goc,
            can_xem_lai=bool(g.ly_do), ly_do_xem_lai="; ".join(g.ly_do)) for g in bo.giao_dich],
    }
    js = """/// <reference path="../pb_data/types.d.ts" />
// NẠP DỮ LIỆU CŨ TỪ EXCEL – tạo tự động bởi migrate/tao_migration_du_lieu.py
// %d dự án · %d mã cây · %d map · %d giao dịch. Chạy 1 lần; bỏ qua bản ghi đã có (theo mã / ma_import).

migrate((app) => {
  const DATA = %s;

  const col = (n) => app.findCollectionByNameOrId(n);
  const timMot = (n, filter, params) => {
    try { return app.findFirstRecordByFilter(n, filter, params); } catch (_) { return null; }
  };
  const tao = (c, values) => {
    const r = new Record(c);
    for (const k in values) r.set(k, values[k]);
    app.save(r);
    return r;
  };

  const idDa = {}, idCay = {};
  const cDa = col("du_an"), cCay = col("cay_ma"), cMap = col("map_cu"), cGd = col("giao_dich");

  for (const d of DATA.du_an) {
    const co = timMot("du_an", "ma = {:ma}", { ma: d.ma });
    idDa[d.ma] = co ? co.id : tao(cDa, d).id;
  }
  for (const c of DATA.cay_ma) {
    const co = timMot("cay_ma", "ma = {:ma}", { ma: c.ma });
    idCay[c.ma] = co ? co.id : tao(cCay, c).id;
  }
  for (const m of DATA.map_cu) {
    if (!timMot("map_cu", "cong_tac = {:a} && cong_doan = {:b}", { a: m.cong_tac, b: m.cong_doan })) {
      tao(cMap, { cong_tac: m.cong_tac, cong_doan: m.cong_doan, ma_cay: idCay[m.ma_cay] });
    }
  }
  let them = 0;
  for (const g of DATA.giao_dich) {
    if (timMot("giao_dich", "ma_import = {:k}", { k: g.ma_import })) continue;
    tao(cGd, Object.assign({}, g, { du_an: g.du_an ? idDa[g.du_an] : "", ma_cay: idCay[g.ma_cay] }));
    them++;
  }
  console.log("Nạp dữ liệu cũ: thêm " + them + " giao dịch");
}, (app) => {
  // không tự xoá dữ liệu khi lùi migration
});
""" % (len(data["du_an"]), len(data["cay_ma"]), len(data["map_cu"]), len(data["giao_dich"]),
       json.dumps(data, ensure_ascii=False, indent=1))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"Đã tạo {out}: {len(data['giao_dich'])} giao dịch, {os.path.getsize(out) // 1024} KB")


if __name__ == "__main__":
    main()
