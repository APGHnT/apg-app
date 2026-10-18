"""/nhap – ghi dòng thu/chi thẳng vào PocketBase (thay cho ghi file Excel con).

  python3 nhap_pb.py dong.json            → kiểm tra kỹ rồi GHI
  python3 nhap_pb.py dong.json --thu      → chỉ kiểm tra, KHÔNG ghi gì (dùng cho bước xem trước)
  python3 nhap_pb.py dong.json --ghi-ca-trung   → vẫn ghi dù nghi trùng
  python3 nhap_pb.py --danh-muc           → in dự án đang có (mã, tên, khởi công, kết thúc)

dong.json: [{"MA_DU_AN": "380H81H30PVC" | "CHUNG", "NGAY": "dd/mm/yyyy", "MA_CAY": "0.02.02.02", "NOI_DUNG": "...",
             "QUY_CACH": "D10", "SL": 20, "DVT": "cây", "DON_GIA": 117000, "NGUON_TIEN": "THINH",
             "NHA_CC": "...", "LOAI": "CHI"|"THU", "GHI_CHU": "...",
             "CHUNG_TU": "đường dẫn ảnh/PDF" (tuỳ chọn), "CHIA_THANG": n (tuỳ chọn),
             "XEM_LAI": "lý do" (tuỳ chọn – lưu tạm dòng còn thiếu giá/SL/ngày)}, ...]

Kết nối: biến môi trường APG_PB_URL / APG_PB_TOKEN, nếu không có thì đọc
<thư mục plugin>/config/pocketbase.json  {"url": "...", "token": "..."}.
Token là của tài khoản users "claude.nhap" (không phải superuser): ghi/sửa/huỷ được, không xoá được.

An toàn: kiểm tra TOÀN BỘ các dòng trước (mã, dự án, ngày, nghi trùng) – có lỗi thì không ghi dòng nào.
Chỉ dùng thư viện chuẩn của Python.
"""
import calendar
import datetime
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------- kết nối ----------
def cau_hinh():
    url, tok = os.environ.get("APG_PB_URL"), os.environ.get("APG_PB_TOKEN")
    f = os.path.join(GOC, "config", "pocketbase.json")
    if (not url or not tok) and os.path.exists(f):
        c = json.load(open(f, encoding="utf-8"))
        url, tok = url or c.get("url"), tok or c.get("token")
    if not url or not tok:
        sys.exit("Chưa có cấu hình PocketBase (config/pocketbase.json hoặc APG_PB_URL/APG_PB_TOKEN).")
    return url.rstrip("/"), tok


URL, TOKEN = None, None


def goi(method, path, body=None, data=None, ctype="application/json"):
    if body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(URL + path, data=data, method=method)
    req.add_header("Authorization", TOKEN)
    if data is not None:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as ex:
        msg = ex.read().decode(errors="replace")
        try:
            j = json.loads(msg)
            msg = j.get("message", msg) + ("" if not j.get("data") else " " + json.dumps(j["data"], ensure_ascii=False))
        except ValueError:
            pass
        if ex.code == 401:
            msg += " → token hết hạn hoặc bị thu hồi: tạo token mới (users › claude.nhap › Impersonate)."
        raise RuntimeError(f"{ex.code}: {msg}") from None


def tat_ca(col, fields, filt=None):
    out, page = [], 1
    while True:
        q = {"page": page, "perPage": 500, "fields": fields, "skipTotal": 1}
        if filt:
            q["filter"] = filt
        r = goi("GET", f"/api/collections/{col}/records?" + urllib.parse.urlencode(q))
        out += r["items"]
        if len(r["items"]) < 500:
            return out
        page += 1


def gui_tep(giao_dich_id, duong_dan, ghi_chu=""):
    ranh = uuid.uuid4().hex
    ten = os.path.basename(duong_dan)
    loai = mimetypes.guess_type(ten)[0] or "application/octet-stream"
    phan = []
    for k, v in (("giao_dich", giao_dich_id), ("ghi_chu", ghi_chu)):
        phan.append(f'--{ranh}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    phan.append(f'--{ranh}\r\nContent-Disposition: form-data; name="tep"; filename="{ten}"\r\n'
                f"Content-Type: {loai}\r\n\r\n".encode() + open(duong_dan, "rb").read() + b"\r\n")
    phan.append(f"--{ranh}--\r\n".encode())
    return goi("POST", "/api/collections/chung_tu/records", data=b"".join(phan),
               ctype=f"multipart/form-data; boundary={ranh}")


# ---------- xử lý số, ngày ----------
def so(v):
    """Số, hoặc biểu thức số học thuần ('250*156+27000')."""
    if v in (None, ""):
        return 0
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip().lstrip("=+").replace(",", "")
    if not re.fullmatch(r"[0-9.+\-*/() ]+", s):
        raise ValueError(f"không đọc được số: {v}")
    return eval(s, {"__builtins__": {}}, {})


def doc_ngay(s):
    if s in (None, ""):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(str(s).strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"ngày không đọc được: {s}")


def cong_thang(d, k):
    m = d.month - 1 + k
    y, m = d.year + m // 12, m % 12 + 1
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))


def chia_thang(it):
    """CHIA_THANG = n → n dòng hằng tháng, tổng giữ đúng đến đồng."""
    n = int(it.get("CHIA_THANG") or 1)
    if n <= 1:
        return [it]
    d0 = doc_ngay(it.get("NGAY"))
    if not d0:
        raise ValueError("chia theo tháng cần NGAY bắt đầu")
    tong = round((so(it.get("SL")) or 1) * so(it.get("DON_GIA")))
    moi = tong // n
    out = []
    for k in range(n):
        x = dict(it)
        x.pop("CHIA_THANG", None)
        x.update(NGAY=cong_thang(d0, k).strftime("%d/%m/%Y"), NOI_DUNG=f"{it['NOI_DUNG']} (tháng {k+1}/{n})",
                 SL=1, DVT="tháng", DON_GIA=moi if k < n - 1 else tong - moi * (n - 1),
                 GHI_CHU=" | ".join(v for v in (it.get("GHI_CHU"), f"Tổng {tong:,.0f} chia {n} tháng từ {d0:%d/%m/%Y}") if v))
        if k:
            x.pop("CHUNG_TU", None)  # chứng từ chỉ đính vào tháng đầu
        out.append(x)
    return out


def pb_ngay(d):
    return f"{d:%Y-%m-%d} 00:00:00.000Z" if d else ""


def tien(x):
    return f"{x:,.0f}".replace(",", ".")


# ---------- chính ----------
def main():
    global URL, TOKEN
    URL, TOKEN = cau_hinh()
    co = [a for a in sys.argv[1:] if a.startswith("--")]
    ts = [a for a in sys.argv[1:] if not a.startswith("--")]

    du_an = {x["ma"]: x for x in tat_ca("du_an", "id,ma,ten,khoi_cong,ket_thuc,ghi_chu")}
    if "--danh-muc" in co:
        for x in du_an.values():
            print(f"{x['ma']:<14} {x['ten'][:40]:<40} KC {x['khoi_cong'][:10]}  KT {x['ket_thuc'][:10] or '—':<10}  {x['ghi_chu']}")
        return
    if not ts:
        sys.exit(__doc__)

    cay = {x["ma"]: x for x in tat_ca("cay_ma", "id,ma,ten,la")}
    vao = [x for it in json.load(open(ts[0], encoding="utf-8")) for x in chia_thang(it)]
    thu, trung_ok = "--thu" in co, "--ghi-ca-trung" in co
    loi, canh_bao, ban_ghi = [], [], []

    for i, it in enumerate(vao, 1):
        nhan = f"Dòng {i} ({it.get('NOI_DUNG', '?')})"
        try:
            ma = str(it.get("MA_CAY", "")).strip()
            c = cay.get(ma)
            if not c:
                raise ValueError(f"mã {ma} không có trong cây")
            if not c["la"]:
                raise ValueError(f"mã {ma} chưa xuống lá")
            loai = it.get("LOAI") or ("THU" if ma == "1" or ma.startswith("1.") else "CHI")
            if loai == "THU" and not (ma == "1" or ma.startswith("1.")):
                raise ValueError("khoản THU phải dùng mã nhánh 1")
            if loai == "CHI" and not ma.startswith("0."):
                raise ValueError("khoản CHI phải dùng mã nhánh 0.xx")
            d = doc_ngay(it.get("NGAY"))
            sl, dg = so(it.get("SL")), so(it.get("DON_GIA"))
            xem_lai = (it.get("XEM_LAI") or "").strip()
            mda = str(it.get("MA_DU_AN", "")).strip()
            if mda == "CHUNG":
                if loai != "CHI":
                    raise ValueError("chỉ khoản CHI mới được phân bổ CHUNG")
                if not d:
                    raise ValueError("chi phí CHUNG phải có ngày")
                da_id, phan_bo = "", "CHUNG"
            else:
                da = du_an.get(mda)
                if not da:
                    raise ValueError(f"dự án {mda} chưa có trong PocketBase")
                da_id, phan_bo = da["id"], "RIENG"
            if not xem_lai:
                if not d:
                    raise ValueError("thiếu ngày (hoặc ghi XEM_LAI kèm lý do)")
                if not sl:
                    raise ValueError("thiếu số lượng (hoặc ghi XEM_LAI kèm lý do)")
                if not dg:
                    raise ValueError("thiếu đơn giá (hoặc ghi XEM_LAI kèm lý do)")
                if da_id:
                    kc, kt = du_an[mda]["khoi_cong"][:10], du_an[mda]["ket_thuc"][:10]
                    if f"{d:%Y-%m-%d}" < kc:
                        raise ValueError(f"ngày {d:%d/%m/%Y} trước khởi công {kc}")
                    if kt and f"{d:%Y-%m-%d}" > kt:
                        raise ValueError(f"ngày {d:%d/%m/%Y} sau ngày kết thúc {kt}")
            ct = it.get("CHUNG_TU")
            if ct and not os.path.isfile(ct):
                raise ValueError(f"không thấy file chứng từ {ct}")
            ban_ghi.append(dict(
                _nhan=nhan, _ct=ct, _ma=ma, _ten_cay=c["ten"], _mda=mda or "CHUNG",
                du_an=da_id, loai=loai, ngay=pb_ngay(d), noi_dung=str(it["NOI_DUNG"]).strip(), ma_cay=c["id"],
                dvt=it.get("DVT") or "", so_luong=sl, don_gia=dg, nguon_tien=it.get("NGUON_TIEN") or "",
                phan_bo=phan_bo, trang_thai="HIEU_LUC", nha_cc=it.get("NHA_CC") or "",
                quy_cach=it.get("QUY_CACH") or "", ghi_chu=it.get("GHI_CHU") or "",
                nguon_goc="CLAUDE_NHAP", can_xem_lai=bool(xem_lai), ly_do_xem_lai=xem_lai))
        except (ValueError, KeyError) as ex:
            loi.append(f"{nhan}: {ex}")

    if loi:
        print("CÓ LỖI – CHƯA GHI GÌ:")
        [print("  ✗", x) for x in loi]
        sys.exit(1)

    # Nghi trùng: cùng dự án, ngày, mã, nội dung, SL, ĐG đã có (còn hiệu lực)
    for b in ban_ghi:
        if not b["ngay"]:
            continue
        f = (f'ngay = "{b["ngay"]}" && ma_cay = "{b["ma_cay"]}" && du_an = "{b["du_an"]}" && '
             f'so_luong = {b["so_luong"]} && don_gia = {b["don_gia"]} && trang_thai = "HIEU_LUC"')
        for o in tat_ca("giao_dich", "id,noi_dung,created", f):
            if o["noi_dung"].strip().upper() == b["noi_dung"].upper():
                canh_bao.append(f"{b['_nhan']}: đã có dòng giống hệt (id {o['id']}, nhập {o['created'][:10]})")
    if canh_bao and not trung_ok:
        print("NGHI TRÙNG – CHƯA GHI GÌ:")
        [print("  ·", x) for x in canh_bao]
        print("Hỏi Richard; nếu đúng là mua thêm thì chạy lại với --ghi-ca-trung.")
        sys.exit(2)

    tong = sum(round(b["so_luong"] * b["don_gia"]) for b in ban_ghi)
    if thu:
        print(f"KIỂM TRA OK – {len(ban_ghi)} dòng, tổng {tien(tong)} đ (chưa ghi):")
        for b in ban_ghi:
            print(f"  {b['ngay'][:10] or '—':<10} {b['_mda']:<13} {b['_ma']:<11} {b['noi_dung'][:35]:<35} "
                  f"{b['quy_cach'][:10]:<10} {b['so_luong']:>8g} {b['dvt']:<5} × {tien(b['don_gia']):>12} = "
                  f"{tien(round(b['so_luong'] * b['don_gia'])):>14}" + ("  ⚠ " + b["ly_do_xem_lai"] if b["can_xem_lai"] else ""))
        return

    da_ghi, tep_cache = [], {}
    try:
        for b in ban_ghi:
            body = {k: v for k, v in b.items() if not k.startswith("_")}
            r = goi("POST", "/api/collections/giao_dich/records", body)
            da_ghi.append((b, r))
            if b["_ct"] and b["_ct"] not in tep_cache:  # 1 hoá đơn nhiều dòng → đính 1 lần vào dòng đầu
                gui_tep(r["id"], b["_ct"], f"Chứng từ cho {sum(x['_ct'] == b['_ct'] for x in ban_ghi)} dòng nhập cùng lúc")
                tep_cache[b["_ct"]] = r["id"]
    except RuntimeError as ex:
        print(f"LỖI KHI GHI: {ex}")
        print(f"Đã ghi {len(da_ghi)}/{len(ban_ghi)} dòng trước khi lỗi:")
        [print("  ✓", r["id"], b["noi_dung"]) for b, r in da_ghi]
        print("Không ghi lại các dòng trên; sửa dòng lỗi rồi chỉ chạy phần còn lại.")
        sys.exit(3)

    print(f"ĐÃ GHI {len(da_ghi)} dòng, tổng {tien(sum(r['thanh_tien'] for _, r in da_ghi))} đ"
          + (f", {len(tep_cache)} chứng từ" if tep_cache else "") + ":")
    for b, r in da_ghi:
        print(f"  ✓ {r['id']}  {b['_mda']}  {b['_ma']}  {b['noi_dung']}  {tien(r['thanh_tien'])}"
              + ("  ⚠ cần xem lại" if b["can_xem_lai"] else ""))


if __name__ == "__main__":
    main()
