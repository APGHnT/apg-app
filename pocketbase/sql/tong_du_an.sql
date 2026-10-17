SELECT
  d.id AS id,
  d.ma AS ma,
  d.ten AS ten,
  d.khoi_cong AS khoi_cong,
  d.ket_thuc AS ket_thuc,
  (SELECT COALESCE(SUM(g.thanh_tien), 0) FROM giao_dich g
    WHERE g.du_an = d.id AND g.loai = 'THU') AS thu,
  (SELECT COALESCE(SUM(g.thanh_tien), 0) FROM giao_dich g
    WHERE g.du_an = d.id AND g.loai = 'CHI') AS chi_truc_tiep,
  (SELECT COALESCE(SUM(g.thanh_tien * 1.0 / (
      SELECT COUNT(*) FROM du_an d2
      WHERE substr(d2.khoi_cong, 1, 10) <= substr(g.ngay, 1, 10)
        AND (d2.ket_thuc = '' OR substr(d2.ket_thuc, 1, 10) >= substr(g.ngay, 1, 10))
    )), 0) FROM giao_dich g
    WHERE g.phan_bo = 'CHUNG' AND g.loai = 'CHI'
      AND substr(d.khoi_cong, 1, 10) <= substr(g.ngay, 1, 10)
      AND (d.ket_thuc = '' OR substr(d.ket_thuc, 1, 10) >= substr(g.ngay, 1, 10))) AS chi_chung
FROM du_an d
