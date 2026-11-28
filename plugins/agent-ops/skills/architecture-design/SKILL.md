---
name: architecture-design
description: Thiết kế kiến trúc - sơ đồ C4, hợp đồng API, luồng gọi dịch vụ ngoài, quan sát hệ thống (log, chỉ số, cảnh báo), red flags. Dùng khi viết/sửa docs/02-architecture, docs/05-api/conventions.md, ADR, hoặc mục 2 "Thiết kế kỹ thuật" của task. Phần riêng dự án nằm ở skill dự án trong .claude/project-profile.md.
---

# Architecture Design

Ràng buộc gốc: mục tech stack và nguyên tắc kiến trúc trong `CLAUDE.md` của dự án. Skill này không nhắc lại, chỉ hướng dẫn cách áp dụng. Thành phần, luồng, red flags riêng của dự án: skill dự án mà `.claude/project-profile.md` liệt kê cho vai architect.
Nguồn tham khảo (đã chọn lọc, viết lại): addyosmani/agent-skills `api-and-interface-design`, `observability-and-instrumentation`, `documentation-and-adrs` (MIT); mô hình C4 (c4model.com).

## 1. Sơ đồ C4 (Mermaid, trong `docs/02-architecture/overview.md`)
Chỉ vẽ đủ cấp cần cho câu hỏi đang trả lời; không vẽ cấp 4 (code).
| Cấp | Câu hỏi |
|---|---|
| 1. Context | Hệ thống nói chuyện với ai (người dùng, admin, dịch vụ ngoài)? |
| 2. Container | Gồm những khối chạy riêng nào (client, API, worker, DB, proxy)? |
| 3. Component | Bên trong một container chia thế nào? |
Quy ước:
- Mỗi mũi tên ghi **việc gì + giao thức** (vd `"gọi dịch vụ chấm điểm (HTTPS, token ngắn hạn)"`), không để mũi tên trống.
- Đánh dấu **ranh giới tin cậy** (subgraph) và chỗ đi qua secret/dữ liệu cá nhân.
- Luồng động (đăng nhập, gọi dịch vụ ngoài, tác vụ nền) dùng `sequenceDiagram`, mỗi luồng có nhánh lỗi chính.
- Sơ đồ sửa cùng commit với thay đổi kiến trúc; sơ đồ lệch code là lỗi.

## 2. Hợp đồng API (contract-first)
Thiết kế hợp đồng (schema vào/ra, mã lỗi, hành vi) trong mục 2 của task **trước** khi backend-dev code. Quy ước chi tiết đặt ở `docs/05-api/conventions.md` (file chủ; chưa có thì architect tạo, quy ước mới là quyết định loại 2).
1. **Hyrum's Law:** mọi hành vi nhìn thấy được (thứ tự, câu chữ lỗi, thời gian) sẽ có người phụ thuộc. Chỉ để lộ điều đã cam kết; ghi rõ cái gì *không* được đảm bảo.
2. **Một định dạng lỗi** cho mọi endpoint, mã lỗi máy đọc được + map status code cố định. Không endpoint nào trả hình dạng khác tuỳ điều kiện.
3. **Chỉ thêm, không phá:** trường mới là optional; không xoá/đổi kiểu trường cũ. Bắt buộc phá → ghi rõ trong tài liệu API + ADR + kế hoạch chuyển đổi cho client (kể cả app bản cũ).
4. **Validate ở biên:** input người dùng, cấu hình, **phản hồi bên thứ ba** là dữ liệu không tin cậy. Bên trong không validate lại dữ liệu đã có kiểu.
5. **Danh sách luôn phân trang**; `PATCH` cho cập nhật một phần; tên URL là danh từ số nhiều, không động từ.
6. **Ghi an toàn khi retry:** theo ADR/quy ước ghi an toàn của dự án (khoá do client sinh, `version`). Thiết kế mới có tác dụng ngoài (gọi dịch vụ tốn tiền, gửi email) phải trả lời: claim khoá nguyên tử bằng unique constraint (không SELECT-rồi-INSERT); cùng khoá khác payload → lỗi; trùng khi đang chạy → `409`/`202`; ghi ý định trước khi gọi ngoài để phân biệt thành công/thất bại/không rõ.
7. Schema vào và ra tách riêng; biến thể dùng discriminated union.

## 3. Luồng gọi dịch vụ ngoài ở mức kiến trúc
Mỗi luồng mới gọi dịch vụ ngoài (AI, giọng nói, thanh toán, email…) phải trả lời đủ trong mục 2 của task (dự án có pipeline/mẫu riêng cho luồng AI: xem skill dự án):
- **Adapter:** gọi qua interface/adapter của dự án; thành phần nghiệp vụ không import SDK nhà cung cấp.
- **Chi phí:** ước lượng đơn vị tính phí mỗi lần gọi và số lần/người/ngày; đi qua cơ chế hạn mức/usage của dự án.
- **Độ trễ:** đồng bộ (người dùng chờ, mục tiêu p95), nền (job) hay stream.
- **Lỗi và retry:** timeout rõ ràng; retry có giới hạn + backoff chỉ với lỗi tạm thời (429/5xx/timeout); không retry lỗi do người dùng (key sai, hết quota); có **fallback** (nhà cung cấp khác, nội dung soạn sẵn, hoặc thông báo mềm).
- **Cache:** kết quả xác định được thì cache; nội dung cá nhân hoá thì không. Ghi khoá cache và thời hạn.
- **Đánh giá:** đổi nhà cung cấp/model/prompt phải chạy lại bộ mẫu đánh giá của dự án.
- **Quan sát:** log tên tác vụ, nhà cung cấp, đơn vị tính phí, độ trễ, kết quả kiểm tra; **không log** nội dung người dùng, key, token.

## 4. Quan sát hệ thống (observability)
Mục tiêu: khi có sự cố, tìm ra nguyên nhân **chỉ bằng log/metric**, không cần vào server đoán. Giữ đúng hạ tầng hiện có; công cụ mới (Prometheus, Grafana, OpenTelemetry collector, dịch vụ log trả phí) là thành phần hạ tầng mới → ADR + phiếu DR.
1. **Log có cấu trúc:** JSON, mỗi dòng có `event` (tên cố định, vd `ai.call.completed`), `request_id`, `entry_point` (`api` / `worker` / `cli`), `level`. Không ghép chuỗi tự do.
   - `error` = cần điều tra; `warn` = suy giảm đã xử lý (fallback, retry); `info` = sự kiện nghiệp vụ quan trọng; `debug` tắt ở production.
   - `request_id` truyền từ API sang job nền (trong payload job) và sang lời gọi ngoài.
2. **Không log** (danh sách cho phép, không phải danh sách cấm): chỉ log trường đã liệt kê; không bao giờ log body request/response, key, token, nội dung do người dùng nhập (quy tắc bảo mật của dự án).
3. **Chỉ số RED** cho mỗi endpoint và mỗi phụ thuộc ngoài: số lần, tỉ lệ lỗi, thời gian (đọc p95/p99, không dùng trung bình). **USE** cho hàng đợi và pool: độ dài hàng đợi, tuổi job cũ nhất, số tài nguyên còn dùng được. Nhãn (label) chỉ dùng giá trị hữu hạn: route template, nhóm status, provider — **không** dùng `user_id`, URL thô, câu lỗi.
4. **Cảnh báo theo triệu chứng người dùng thấy** (tỉ lệ lỗi, p95 chậm, job tồn quá lâu), không theo nguyên nhân (CPU, disk) trừ khi sắp đầy. Mỗi cảnh báo có ngưỡng + thời gian có lý do và link tới runbook ở `docs/runbooks/` (bắt đầu 3 dòng: dấu hiệu, kiểm gì, xử lý gì). Hai mức: xử lý ngay / xử lý trong tuần.
5. Thiết kế tính năng mới có retry, hàng đợi hoặc gọi ngoài thì mục 2 của task phải ghi: event log mới, chỉ số RED/USE, cảnh báo (nếu có).

## 5. Red flags (dừng lại, sửa thiết kế)
- Thêm thành phần hạ tầng mới khi thành phần hiện có đủ dùng — muốn thêm phải ADR + DR loại 1.
- Thành phần nghiệp vụ import trực tiếp SDK nhà cung cấp thay vì qua adapter.
- Bảng dữ liệu người dùng thiếu `user_id`; trạng thái giữ trong RAM của API.
- Luồng gọi dịch vụ ngoài không có fallback hoặc không có ước tính chi phí.
- Endpoint danh sách không phân trang; lỗi khác định dạng chuẩn; phá tương thích không ghi ADR.
- Sơ đồ có mũi tên không nhãn, hoặc thiếu ranh giới tin cậy ở chỗ đi qua key/dữ liệu cá nhân.
- Câu "luôn / không thể / bảo đảm" không kèm kịch bản phản chứng (skill `agent-ops:decision-requests` mục 2).
- Tính năng có retry/hàng đợi/gọi ngoài mà không thêm log/chỉ số; log ghép chuỗi hoặc thiếu `request_id`; nhãn chỉ số chứa `user_id`.
- Red flags riêng của dự án: skill dự án trong profile.

## 6. Tự kiểm trước khi giao
- [ ] `python3 "${CLAUDE_PLUGIN_ROOT}/skills/architecture-design/scripts/check_arch_docs.py"` đạt; sơ đồ C4 đúng cấp, mũi tên có nhãn, có ranh giới tin cậy, khớp code/ADR hiện tại.
- [ ] Mỗi endpoint mới: schema vào/ra, mã lỗi theo chuẩn, phân trang (nếu danh sách), hành vi retry/idempotent.
- [ ] Mỗi luồng gọi dịch vụ ngoài mới: đủ các câu ở mục 3.
- [ ] Tính năng có retry/hàng đợi/gọi ngoài: đủ event log, chỉ số RED/USE, cảnh báo + runbook (mục 4).
- [ ] Không chạm red flag nào ở mục 5; nếu buộc phải chạm → ADR `proposed` + phiếu DR.
- [ ] `grep` repo trước khi nhắc component/thư viện/hàm có sẵn; thiết kế dừng ở hành vi và hợp đồng, không xuống tên file/hàm nội bộ (tên endpoint, schema, mã lỗi vẫn thuộc hợp đồng).
- [ ] Mỗi hợp đồng có ca biên: `null`/rỗng, PATCH không đổi gì (theo `docs/05-api/conventions.md`), trường lạ, timeout khoá, lỗi mạng/5xx.
- [ ] Đã tự kiểm danh sách của skill dự án (nếu có).
- [ ] Hợp đồng API trong task: điền đủ bảng `api` (H1–H7) của `${CLAUDE_PLUGIN_ROOT}/templates/design-selfcheck.md` vào file subtask; người rà đối chiếu từng câu trả lời.

## 7. Tài nguyên trong skill
- `scripts/check_arch_docs.py`: chạy ở gốc dự án `python3 "${CLAUDE_PLUGIN_ROOT}/skills/architecture-design/scripts/check_arch_docs.py"`. Kiểm mũi tên Mermaid có nhãn (flowchart, sequenceDiagram) trong `docs/02-architecture/`, và ADR đúng mẫu (tên file, số thứ tự, heading bắt buộc, trạng thái, `superseded by` trỏ ADR có thật). Exit 1 nếu có lỗi; `--warn-only` để chỉ báo. Chạy trước khi giao mọi thay đổi trong `docs/02-architecture/`.
