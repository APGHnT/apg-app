/// <reference path="../pb_data/types.d.ts" />
// Kiểm tra mỗi giao dịch trước khi lưu – thay cho cột KIEM_TRA của Excel.
// Chạy cho MỌI nguồn ghi: app, Claude, script chuyển dữ liệu, trang quản trị.

onRecordValidate((e) => {
  const r = e.record;
  const loi = (msg) => {
    throw new BadRequestError("Giao dịch không hợp lệ: " + msg);
  };
  const ngay10 = (s) => (s || "").substring(0, 10);

  // 1. Thành tiền luôn do máy tính, làm tròn đến đồng.
  //    Giao dịch đã huỷ: giữ nguyên SL/ĐG đã ghi để tra lại, nhưng thành tiền = 0.
  //    Số âm được phép: tiền thừa nhận về / trừ ứng / chiết khấu.
  const sl = r.getFloat("so_luong");
  const dg = r.getFloat("don_gia");
  const daHuy = r.getString("trang_thai") === "DA_HUY";
  r.set("thanh_tien", daHuy ? 0 : Math.round(sl * dg));

  // 2. Mã cây phải tồn tại, đã xuống lá, đúng nhánh THU/CHI
  let ma;
  try {
    ma = e.app.findRecordById("cay_ma", r.getString("ma_cay"));
  } catch (_) {
    loi("mã cây không tồn tại");
  }
  if (!ma.getBool("la")) loi("mã " + ma.getString("ma") + " chưa xuống lá");
  const code = ma.getString("ma");
  const loai = r.getString("loai");
  if (loai === "THU" && !(code === "1" || code.startsWith("1."))) loi("khoản THU phải dùng mã nhánh 1");
  if (loai === "CHI" && !code.startsWith("0.")) loi("khoản CHI phải dùng mã nhánh 0.xx");

  // 3. Phân bổ: RIÊNG phải có dự án; CHUNG không gắn dự án và bắt buộc có ngày (để chia theo ngày)
  const phanBo = r.getString("phan_bo");
  const duAnId = r.getString("du_an");
  const ngay = ngay10(r.getString("ngay"));
  if (phanBo === "RIENG" && !duAnId) loi("chưa chọn dự án");
  if (phanBo === "CHUNG" && duAnId) loi("chi phí CHUNG không gắn với một dự án");
  if (phanBo === "CHUNG" && !ngay && !daHuy) loi("chi phí CHUNG phải có ngày");
  if (phanBo === "CHUNG" && loai !== "CHI") loi("chỉ khoản CHI mới được phân bổ CHUNG");

  // 4. Dòng nghi vấn được phép lưu tạm, nhưng phải ghi lý do
  const xemLai = r.getBool("can_xem_lai");
  if (xemLai && !r.getString("ly_do_xem_lai").trim()) loi("đánh dấu cần xem lại thì phải ghi lý do");

  // 5. Dòng bình thường (còn hiệu lực, không đánh dấu xem lại): đủ ngày, số lượng, đơn giá
  //    và ngày nằm trong thời gian dự án
  if (!xemLai && !daHuy) {
    if (!ngay) loi("thiếu ngày");
    if (sl === 0) loi("thiếu số lượng");
    if (dg === 0) loi("thiếu đơn giá");
    if (duAnId) {
      const da = e.app.findRecordById("du_an", duAnId);
      const kc = ngay10(da.getString("khoi_cong"));
      const kt = ngay10(da.getString("ket_thuc"));
      if (ngay < kc) loi("ngày " + ngay + " trước ngày khởi công " + kc);
      if (kt && ngay > kt) loi("ngày " + ngay + " sau ngày kết thúc " + kt);
    }
  }

  e.next();
}, "giao_dich");
