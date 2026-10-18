/// <reference path="../pb_data/types.d.ts" />
// Chặn mọi quyền quản trị khi truy cập TỪ INTERNET (qua Tailscale Funnel).
//
// Một request được coi là "từ Internet" khi có MỘT trong hai dấu hiệu:
//   1. Header "Tailscale-Funnel-Request" (Tailscale bản mới tự gắn, người ngoài không giả được).
//   2. Header "X-Forwarded-For" (Tailscale gắn IP thật của người truy cập, ghi đè giá trị người ngoài gửi)
//      chứa IP KHÔNG thuộc mạng nội bộ / mạng Tailscale riêng.
// Truy cập trong LAN (http://192.168.1.169:8090) không đi qua Tailscale nên không có các header này.
// Truy cập qua Tailscale riêng có X-Forwarded-For là IP 100.x.x.x → vẫn được vào quản trị.
//
// Lưu ý JSVM: mỗi handler chạy trong ngữ cảnh riêng, nên mọi hàm phụ phải khai báo BÊN TRONG handler.

routerUse((e) => {
  const laIpNoiBo = (ip) => {
    ip = (ip || "").trim().toLowerCase();
    if (ip.startsWith("[")) ip = ip.slice(1, ip.indexOf("]"));
    if (ip.startsWith("::ffff:")) ip = ip.slice(7);
    if (ip === "::1" || ip.startsWith("fd7a:115c:a1e0:") || ip.startsWith("fc") || ip.startsWith("fd") || ip.startsWith("fe80:")) return true;
    const p = ip.split(".").map((x) => parseInt(x, 10));
    if (p.length !== 4 || p.some((x) => isNaN(x))) return false;
    return p[0] === 127 || p[0] === 10 ||
      (p[0] === 192 && p[1] === 168) ||
      (p[0] === 172 && p[1] >= 16 && p[1] <= 31) ||
      (p[0] === 100 && p[1] >= 64 && p[1] <= 127);   // mạng Tailscale riêng
  };

  const h = e.request.header;
  const xff = h.get("X-Forwarded-For");
  const ipNguon = xff ? xff.split(",")[0] : "";
  const tuInternet = h.get("Tailscale-Funnel-Request") !== "" || (xff !== "" && !laIpNoiBo(ipNguon));

  if (tuInternet) {
    const p = e.request.url.path;
    const cam = ["/_", "/api/collections/_superusers", "/api/settings", "/api/backups", "/api/logs", "/api/crons"];
    const laApiCauTruc = p === "/api/collections" || p === "/api/collections/" ||
      (p.startsWith("/api/collections/") && p.split("/").length <= 4) ||
      p.startsWith("/api/collections/import");
    if (cam.some((x) => p === x || p.startsWith(x + "/")) || laApiCauTruc || e.hasSuperuserAuth()) {
      // Câu báo không dấu: trình duyệt điện thoại hay hiển thị sai tiếng Việt khi xem JSON trực tiếp.
      throw new ForbiddenError("Khong duoc phep truy cap chuc nang quan tri tu Internet.");
    }
  }
  return e.next();
});
