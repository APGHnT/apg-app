/// <reference path="../pb_data/types.d.ts" />
// Ghi lại AI đã nhập / sửa lần cuối mỗi giao dịch và chứng từ (email người đăng nhập).
// Do máy tự điền trong hook nguoi_nhap.pb.js – người dùng không tự gõ được.
// Dữ liệu cũ nạp từ Excel để trống (xem cột nguon_goc).
migrate((app) => {
  for (const ten of ["giao_dich", "chung_tu"]) {
    const c = app.findCollectionByNameOrId(ten);
    c.fields.add(new TextField({ name: "nguoi_tao", max: 200 }));
    c.fields.add(new TextField({ name: "nguoi_sua", max: 200 }));
    app.save(c);
  }
}, (app) => {
  for (const ten of ["giao_dich", "chung_tu"]) {
    const c = app.findCollectionByNameOrId(ten);
    c.fields.removeByName("nguoi_tao");
    c.fields.removeByName("nguoi_sua");
    app.save(c);
  }
});
