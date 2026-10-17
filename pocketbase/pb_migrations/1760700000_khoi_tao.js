/// <reference path="../pb_data/types.d.ts" />
// Cấu trúc dữ liệu APG – thu chi dự án (PocketBase v0.40.x)
// Quyền: người đăng nhập (users) được xem tất cả và nhập/sửa giao dịch;
// chỉ superuser được sửa dự án, cây mã, map và xoá giao dịch.

const DA_DANG_NHAP = '@request.auth.id != ""';

migrate((app) => {
  const snapshot = [
    {
      id: "pbc_du_an",
      name: "du_an",
      type: "base",
      listRule: DA_DANG_NHAP,
      viewRule: DA_DANG_NHAP,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      fields: [
        { name: "ma", type: "text", required: true, presentable: true, pattern: "^[A-Z0-9]+$" },
        { name: "ten", type: "text" },
        { name: "dia_chi", type: "text" },
        { name: "khoi_cong", type: "date", required: true },
        { name: "ket_thuc", type: "date" },
        { name: "ghi_chu", type: "text" },
        { name: "created", type: "autodate", onCreate: true, onUpdate: false },
        { name: "updated", type: "autodate", onCreate: true, onUpdate: true },
      ],
      indexes: ["CREATE UNIQUE INDEX idx_du_an_ma ON du_an (ma)"],
    },
    {
      id: "pbc_cay_ma",
      name: "cay_ma",
      type: "base",
      listRule: DA_DANG_NHAP,
      viewRule: DA_DANG_NHAP,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      fields: [
        { name: "ma", type: "text", required: true, presentable: true, pattern: "^[0-9]+(\\.[0-9]{2})*$" },
        { name: "ten", type: "text", required: true, presentable: true },
        { name: "ma_cha", type: "text" },
        { name: "cap", type: "number", onlyInt: true },
        { name: "la", type: "bool" },
        { name: "ghi_chu", type: "text" },
      ],
      indexes: ["CREATE UNIQUE INDEX idx_cay_ma_ma ON cay_ma (ma)"],
    },
    {
      id: "pbc_map_cu",
      name: "map_cu",
      type: "base",
      listRule: DA_DANG_NHAP,
      viewRule: DA_DANG_NHAP,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      fields: [
        { name: "cong_tac", type: "text", required: true },
        { name: "cong_doan", type: "text", required: true },
        { name: "ma_cay", type: "relation", collectionId: "pbc_cay_ma", maxSelect: 1, required: true },
      ],
      indexes: ["CREATE UNIQUE INDEX idx_map_cu_key ON map_cu (cong_tac, cong_doan)"],
    },
    {
      id: "pbc_giao_dich",
      name: "giao_dich",
      type: "base",
      listRule: DA_DANG_NHAP,
      viewRule: DA_DANG_NHAP,
      createRule: DA_DANG_NHAP,
      updateRule: DA_DANG_NHAP,
      deleteRule: null,
      fields: [
        // để trống khi phan_bo = CHUNG (chi phí chung chia đều cho các dự án đang chạy)
        { name: "du_an", type: "relation", collectionId: "pbc_du_an", maxSelect: 1 },
        { name: "loai", type: "select", values: ["CHI", "THU"], maxSelect: 1, required: true },
        { name: "ngay", type: "date" },
        { name: "noi_dung", type: "text", required: true },
        { name: "ma_cay", type: "relation", collectionId: "pbc_cay_ma", maxSelect: 1, required: true },
        { name: "dvt", type: "text" },
        { name: "so_luong", type: "number" },
        { name: "don_gia", type: "number" },
        // do hook tính lại = làm tròn(so_luong × don_gia), không nhập tay
        { name: "thanh_tien", type: "number" },
        { name: "nguon_tien", type: "text" },
        { name: "phan_bo", type: "select", values: ["RIENG", "CHUNG"], maxSelect: 1, required: true },
        { name: "nha_cc", type: "text" },
        { name: "quy_cach", type: "text" },
        { name: "ghi_chu", type: "text" },
        // dữ liệu chuyển từ Excel: tên file#dòng (khoá để chạy lại không bị nhân đôi)
        { name: "ma_import", type: "text" },
        { name: "nguon_goc", type: "text" },
        // dòng còn thiếu/nghi vấn: được lưu nhưng phải có lý do
        { name: "can_xem_lai", type: "bool" },
        { name: "ly_do_xem_lai", type: "text" },
        { name: "created", type: "autodate", onCreate: true, onUpdate: false },
        { name: "updated", type: "autodate", onCreate: true, onUpdate: true },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_giao_dich_ma_import ON giao_dich (ma_import) WHERE ma_import != ''",
        "CREATE INDEX idx_giao_dich_du_an ON giao_dich (du_an, loai)",
        "CREATE INDEX idx_giao_dich_ngay ON giao_dich (ngay)",
      ],
    },
    {
      id: "pbc_chung_tu",
      name: "chung_tu",
      type: "base",
      listRule: DA_DANG_NHAP,
      viewRule: DA_DANG_NHAP,
      createRule: DA_DANG_NHAP,
      updateRule: null,
      deleteRule: null,
      fields: [
        { name: "giao_dich", type: "relation", collectionId: "pbc_giao_dich", maxSelect: 1, required: true, cascadeDelete: true },
        { name: "tep", type: "file", maxSelect: 1, maxSize: 15728640, required: true,
          mimeTypes: ["image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"] },
        { name: "ghi_chu", type: "text" },
        { name: "created", type: "autodate", onCreate: true, onUpdate: false },
      ],
      indexes: [],
    },
  ];

  app.importCollections(snapshot, false);

  // Báo cáo theo dự án – câu SQL giữ giống hệt pocketbase/sql/tong_du_an.sql
  // (tests/kiem_tra_sql.py so sánh hai bản)
  const view = new Collection({
    id: "pbc_tong_du_an",
    name: "tong_du_an",
    type: "view",
    listRule: DA_DANG_NHAP,
    viewRule: DA_DANG_NHAP,
    viewQuery: `
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
`,
  });
  app.save(view);
}, (app) => {
  for (const name of ["tong_du_an", "chung_tu", "giao_dich", "map_cu", "cay_ma", "du_an"]) {
    try {
      app.delete(app.findCollectionByNameOrId(name));
    } catch (_) {}
  }
});
