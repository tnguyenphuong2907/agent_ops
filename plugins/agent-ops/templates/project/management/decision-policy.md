# Chính sách phân loại quyết định

> Mục đích: chỉ đưa tới Product Owner (PO) những quyết định thật sự cần PO, và mọi câu hỏi tới tay PO đều đã được **architect đề xuất** và **decision-reviewer phản biện**.
> Quy trình chi tiết: skill `agent-ops:decision-requests`. Mẫu phiếu: `templates/decision-request.md` của plugin.

## 1. Hai loại quyết định

### Loại 1 — PO quyết (khó đảo ngược hoặc ảnh hưởng lớn)
Một phiếu thuộc loại 1 nếu **đúng ít nhất một** điều sau:

| # | Nhóm | Ví dụ |
|---|---|---|
| 1.1 | **Phạm vi**: thêm/bớt tính năng, chuyển tính năng giữa bản đầu / V1 / sau | "Có làm đăng xuất mọi thiết bị ở bản đầu?" |
| 1.2 | **Tech stack / phụ thuộc mới**: thêm dịch vụ ngoài, hạ tầng, hoặc thư viện ảnh hưởng kiến trúc | thêm một dịch vụ cache, đổi nhà cung cấp email |
| 1.3 | **Nguyên tắc kiến trúc** trong `CLAUDE.md`, chấp thuận ADR (`proposed` → `accepted`) | |
| 1.4 | **Schema đã được PO duyệt** (sau G2) | đổi khoá chính, gộp bảng |
| 1.5 | **Bảo mật**: xác thực, mã hoá, quản lý key, lộ dữ liệu, quyền truy cập | 2FA admin, cách lưu JWT |
| 1.6 | **Chi phí định kỳ** hoặc có thể phát sinh tiền (nâng gói dịch vụ, máy chủ lớn hơn) | |
| 1.7 | **Dữ liệu người dùng**: loại dữ liệu mới được lưu, thời gian giữ dữ liệu cá nhân, xoá dữ liệu | "Có lưu file người dùng tải lên không?" |
| 1.8 | **Trải nghiệm người dùng cốt lõi**: thay đổi cách người dùng dùng sản phẩm (luồng chính) | đổi thứ tự các bước của luồng chính |
| 1.9 | **Đảo ngược hoặc mâu thuẫn** với một D-xxx PO đã chốt | |
| 1.10 | Các agent **không thống nhất** (architect và decision-reviewer còn bất đồng sau vòng phản biện thứ 2) | |
| 1.11 | Nằm trong danh sách "PO luôn muốn tự quyết" (mục 3) | |
| 1.12 | **Thay đổi luật của đội** đề xuất từ retro: file agent, skill, `CLAUDE.md`, chính sách này, template | phiếu sửa luật của retro tuần |

### Loại 2 — Agent quyết tạm (dễ đổi lại, ảnh hưởng hẹp)
Mọi thứ không thuộc loại 1, ví dụ:
- Tham số kỹ thuật trong khoảng hợp lý: timeout, retry, ngưỡng cảnh báo, kích thước trang, TTL của cache/log kỹ thuật.
- Định nghĩa nghiệp vụ nội bộ không đổi trải nghiệm người dùng ("phiên kết thúc khi nào" để tính thống kê).
- Đặt tên, vị trí file, cấu trúc tài liệu, task thuộc epic nào, thứ tự task.
- Thư viện nhỏ nằm trong stack đã chọn, không thêm dịch vụ (ví dụ chọn thư viện sinh QR).
- Chi tiết test, môi trường chạy thử, cách đo trong spike.
- Chi tiết giao diện nằm trong design system đã duyệt.

**Loại 2 có phiếu DR** (đề xuất + phản biện), được áp dụng ngay với trạng thái `provisional`, ghi vào `decisions.md` với nhãn ⏳ *tạm*, và PO có thể bác bất cứ lúc nào bằng `/decide`. Phiếu đầy đủ hay phiếu ngắn: xem mục 1b.

## 1b. Siết nhất quán và phiếu ngắn

### Siết nhất quán — loại 2 kể cả khi thuộc 1.5
Áp **đúng** một quy tắc đã chốt (D-xxx, ADR `accepted`) sang một chỗ tương đương bị sót là **loại 2, kể cả khi thuộc bảo mật (1.5)**, nếu đủ cả 4:
1. Chỉ làm **chặt hơn**, không nới lỏng gì.
2. Không tốn tiền.
3. Không thêm hoặc giữ thêm dữ liệu người dùng.
4. Dễ đảo lại.

Ví dụ: giới hạn số lần nhập sai mật khẩu ở đăng nhập (đã chốt) áp thêm cho đổi mật khẩu. Không phải siết nhất quán: nới một kiểm tra, quy tắc mới chưa có D-xxx nào, đổi cách làm của quy tắc cũ, hoặc chạm 1.6, 1.7, 1.9.

### Phiếu ngắn
Dùng **phiếu ngắn** (`templates/decision-request-short.md` của plugin, ~1 trang) khi đủ cả 5:
1. Là loại 2, hoặc là siết nhất quán (ở trên).
2. Không tốn tiền.
3. Không thêm hoặc giữ thêm dữ liệu người dùng.
4. Dễ đảo lại.
5. **Chỉ có một hướng hợp lý**: không có phương án khác mà PO có lý do để chọn.

Còn có lựa chọn thật, hoặc phân vân → phiếu đầy đủ. Phiếu loại 2 dùng mẫu đầy đủ phải ghi dòng **Vì sao không phiếu ngắn** ở mục 4.
- decision-reviewer **kiểm nhanh 1 lượt**: chỉ xem đủ điều kiện chưa. ✅ → `provisional`; ⬆️ (thiếu điều kiện) → architect chuyển sang phiếu đầy đủ, tính là phiếu mới về số vòng.
- Không có mục 10; hộp quyết định ghi ⚡ *phiếu ngắn* ở nhóm quyết định tạm. PO bác như mọi quyết định tạm.

### Quy tắc khi không chắc
- Xếp loại 1 phải **chỉ ra được quy tắc 1.x cụ thể đang áp dụng** và giải thích một câu. Không chỉ ra được → loại 2.
- **Chi tiết triển khai bên trong một quyết định loại 1 đã chốt** là loại 2, trừ khi tự nó chạm 1.5 (bảo mật), 1.6 (chi phí), 1.7 (dữ liệu người dùng) hoặc 1.9 (đảo ngược D-xxx). Riêng 1.5: siết nhất quán (mục 1b) vẫn là loại 2. Ví dụ: PO đã chốt có lưu nháp bài test → tên trạng thái, thứ tự màn hình, ngưỡng thời gian giữ nháp kỹ thuật là loại 2.
- decision-reviewer được **nâng** loại 2 lên loại 1.

### Hạ loại
- decision-reviewer được kết luận ⬇️ **Không cần PO** khi quy tắc 1.x được dẫn thật ra không áp dụng.
- **Không bao giờ hạ** phiếu thuộc 1.5, 1.6, 1.7, 1.9, 1.11, 1.12. (Siết nhất quán ở mục 1b không cần hạ: nó vốn là loại 2.)
- Phiếu bị hạ → `provisional` với nhãn ⬇️ trong hộp quyết định; PO vẫn thấy và bác được như mọi quyết định tạm.
- PO bác một quyết định tạm → quyết định của PO thay thế; nếu task đã làm theo quyết định tạm, PM tạo task sửa.

## 2. Không phải quyết định
"Việc PO cần làm" (điền `.env`, tạo tài nguyên ở nhà cung cấp, merge PR, cấu hình DNS) **không tạo phiếu DR**; ghi vào mục *Việc bạn cần làm* của `DECISIONS-INBOX.md`.

## 3. PO luôn muốn tự quyết (PO tự điền)
> Những nhóm việc dưới đây luôn là loại 1, dù dễ đổi lại.
-

## Lịch sử
| Ngày | Thay đổi |
|---|---|
