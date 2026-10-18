/// <reference path="../pb_data/types.d.ts" />
// Khoá đăng ký tài khoản: chỉ quản trị (superuser, trong LAN/Tailscale) được tạo, xoá tài khoản.
// Mặc định PocketBase cho PHÉP ai cũng tự đăng ký vào bảng users → người lạ qua Funnel
// có thể tạo tài khoản rồi xem toàn bộ dữ liệu. Migration này đóng lỗ hổng đó.
migrate((app) => {
  const users = app.findCollectionByNameOrId("users");
  users.createRule = null;                      // chỉ superuser tạo tài khoản
  users.deleteRule = null;                      // chỉ superuser xoá tài khoản
  users.listRule = "id = @request.auth.id";     // mỗi người chỉ thấy tài khoản của mình
  users.viewRule = "id = @request.auth.id";
  users.updateRule = "id = @request.auth.id";   // tự đổi tên, mật khẩu của mình
  app.save(users);
}, (app) => {
  const users = app.findCollectionByNameOrId("users");
  users.createRule = "";
  users.deleteRule = "id = @request.auth.id";
  app.save(users);
});
