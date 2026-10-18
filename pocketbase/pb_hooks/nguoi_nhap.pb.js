/// <reference path="../pb_data/types.d.ts" />
// Tự điền người nhập (nguoi_tao) và người sửa lần cuối (nguoi_sua) theo tài khoản đang đăng nhập.
// Giá trị người dùng gửi lên cho 2 cột này luôn bị bỏ qua → không giả danh người khác được.

onRecordCreateRequest((e) => {
  const email = e.auth ? e.auth.email() : "";
  e.record.set("nguoi_tao", email);
  e.record.set("nguoi_sua", email);
  return e.next();
}, "giao_dich", "chung_tu");

onRecordUpdateRequest((e) => {
  const email = e.auth ? e.auth.email() : "";
  e.record.set("nguoi_tao", e.record.original().getString("nguoi_tao"));  // không cho đổi người nhập
  e.record.set("nguoi_sua", email);
  return e.next();
}, "giao_dich", "chung_tu");
