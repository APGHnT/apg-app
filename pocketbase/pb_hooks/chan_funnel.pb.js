/// <reference path="../pb_data/types.d.ts" />
// Chặn mọi quyền quản trị khi truy cập TỪ INTERNET qua Tailscale Funnel.
//
// Tailscale Funnel gắn header "Tailscale-Funnel-Request: ?1" vào mọi request đi từ Internet vào,
// và xoá header này nếu người ngoài tự gửi lên, nên không giả mạo được. Truy cập trong LAN
// (http://192.168.1.169:8090) hoặc qua Tailscale riêng thì không có header này và không bị ảnh hưởng.
//
// Qua Funnel:
//   - không mở được trang quản trị /_/
//   - không đăng nhập được tài khoản superuser
//   - không gọi được các API quản trị (settings, backups, logs, crons, cấu trúc bảng)
//   - token superuser (lỡ bị lộ) cũng không dùng được
// Người dùng thường (users) vẫn đăng nhập, nhập và xem dữ liệu bình thường.

routerUse((e) => {
  if (e.request.header.get("Tailscale-Funnel-Request") !== "") {
    const p = e.request.url.path;
    const cam = [
      "/_",
      "/api/collections/_superusers",
      "/api/settings",
      "/api/backups",
      "/api/logs",
      "/api/crons",
    ];
    const laApiCauTruc = p === "/api/collections" || p === "/api/collections/" ||
      (p.startsWith("/api/collections/") && p.split("/").length <= 4) ||   // /api/collections/{ten}
      p.startsWith("/api/collections/import");
    if (cam.some((x) => p === x || p.startsWith(x + "/")) || laApiCauTruc || e.hasSuperuserAuth()) {
      throw new ForbiddenError("Không được phép truy cập chức năng quản trị từ Internet.");
    }
  }
  return e.next();
});
