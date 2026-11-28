---
name: task-management
description: Quy tắc tạo, chia nhỏ, đổi trạng thái epic/task/subtask trong management/tasks, quyền sửa theo mục, brief giao việc kèm ảnh chụp trạng thái. Dùng khi tạo/chia task, đổi trạng thái, ghi tiến trình/review/nghiệm thu, hoặc giao lượt tiếp trong task.
---

# Quản lý task

Luật đầy đủ: `management/README.md`. Tóm tắt thao tác:

## Tạo
0. Chọn làn L1/L2/L3 và ghi `lane:` ở frontmatter task: luật ở `management/README.md` §7 quy tắc 14.
1. Epic: `management/tasks/E<nn>-<slug>/epic.md` (copy `${CLAUDE_PLUGIN_ROOT}/templates/epic.md`).
2. Task: `management/tasks/E<nn>-<slug>/E<nn>-T<nn>-<slug>/task.md` (copy `templates/task.md`) và `log.md` cạnh nó (copy `templates/log.md`: mục 7 Trao đổi, mục 8 Lịch sử), tạo thêm thư mục `evidence/`.
3. Subtask: file `E<nn>-T<nn>-S<nn>-<slug>.md` cạnh `task.md` (copy `templates/subtask.md`) — hoặc chỉ là một dòng trong bảng Subtasks nếu thật sự nhỏ (≤ 30 phút).
4. Task luồng: gán `flow: F<nn>` ở frontmatter và thêm/cập nhật dòng của luồng trong `management/flows.md`; slice của epic khác nằm trong task luồng tiêu thụ nó đầu tiên.
5. Thêm dòng vào bảng task của `epic.md` rồi chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_board.py"` (BOARD sinh tự động, không sửa tay; xem đầu file BOARD). Luật nhánh: mục Quy ước Git trong `CLAUDE.md` của dự án.
6. AC **dẫn mã nguồn** (D-xxx, mã yêu cầu, mục tài liệu), không diễn giải lại luật: câu diễn giải dễ lệch nguồn.
7. Subtask thiết kế hợp đồng API đặt `selfcheck: api`, đặc tả màn đặt `selfcheck: ui`; "Điều kiện xong" ghi "bảng Tự kiểm đã điền đủ" (mẫu `${CLAUDE_PLUGIN_ROOT}/templates/design-selfcheck.md`).
8. Chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/check_task.py" <task> --stage review` trước khi giao review, và bỏ `--stage` trước khi đóng task; sửa hết dòng `lỗi:`, đọc từng dòng `cảnh báo:`.
9. Đặt `plan: opus` cho subtask code có **một** trong các điểm: transaction hoặc ca đua; luồng nhiều tầng/nhiều trạng thái (nộp, lỗi, thử lại, rời trang); nguồn cần đọc > ~40K token; đụng auth/khoá/mã hoá. Subtask CRUD, khung hợp đồng, E2E theo mẫu có sẵn: để trống. Ghi lý do một dòng ở "Việc cần làm".

## Chia nhỏ — câu hỏi kiểm tra
- Task lớn làm xong trong **1 ngày**? Nếu không → tách. Task luồng: ≤ 3 ngày, ≤ 6 subtask? Màn chạy được với BE thật ở cuối task?
- Subtask **≤ 6 giờ, ≤ 25 file, 1 commit**, có điều kiện xong cụ thể?
- Chia theo **lát cắt dọc có thể kiểm thử** (ví dụ "endpoint tạo + test"), không chia theo lớp ("viết model", "viết schema" riêng rẽ).
- Task kiểu "đồng bộ/chuyển quy tắc": mục Tiến trình ghi lệnh `grep` theo ID quy tắc (PT-xx, D-xxx, tên mục) chạy sau khi sửa, số kết quả và danh sách file (không chép từng dòng). "Chuyển" = bản cũ thay bằng ≤ 1 câu + link trong cùng subtask, không xoá trắng. Người rà: reviewer của task.
- Mục 7 của task chỉ trỏ tới đặc tả và bảng file chủ trong `CLAUDE.md` (link, không chép luật); dev gắn nhãn mỗi lệch với thiết kế `GAP` / `CONFLICT` / `WRONG-ASSUMPTION`.
- Thứ tự cho task luồng: S01 BE khung hợp đồng + `openapi.json` → S02 BE handler + lỗi + test ‖ S03 FE màn bằng kiểu sinh + mock route → S04 E2E với BE thật.

## Đổi trạng thái
- Sửa `status` ở frontmatter **và** thêm một dòng vào mục Lịch sử (`log.md`; task tạo trước 2026-11-26: cuối `task.md`): `| YYYY-MM-DD HH:MM | <agent> | <cũ> → <mới>: <lý do ngắn> |`.
- Chỉ ghi vào mục mình sở hữu (bảng quyền trong README).

## Ghi "Cần quyết định"
Không viết câu hỏi trực tiếp trong task. Tạo **phiếu DR** theo skill `agent-ops:decision-requests`, rồi ghi một dòng vào mục 6 của task:
```
- [DR-012](../../../decision-requests/DR-012-slug.md) — <câu hỏi> · trạng thái: draft
```

## Giao việc / vòng review / sửa cho agent mới
Áp cho mọi cặp làm ↔ rà soát: product-analyst ↔ idea-reviewer, architect ↔ decision-reviewer, db-designer ↔ db-reviewer, backend/frontend-dev ↔ code-reviewer, mọi role ↔ qa. Theo luật tiết kiệm token của dự án (skill `agent-ops:agent-orchestration`), mỗi vòng là **một agent mới**; cuộc trao đổi nằm trong file, không nằm trong trí nhớ agent.

**Người rà soát và người sửa phải ghi vào file** (mục 4 Review của task, hoặc mục 7–8 của phiếu DR):
- Mỗi phát hiện có **số** (`#n`), mức (Blocker/Major/Minor) và **trạng thái**: `mở` / `đã sửa` / `không sửa — lý do` / `để PO quyết`.
- Lý do quan trọng (vì sao bỏ một hướng, vì sao chấp nhận rủi ro) viết ra file, không chỉ để trong báo cáo trả về.

**Phiên chính viết brief cho agent sau** (mọi lượt giao trong task: làm → review → sửa → QA), ≤ 16 dòng:
1. Vòng thứ mấy, việc cần làm, và chỉ đọc mục nào (ví dụ "vòng 2: đọc mục 4 vòng 1, sửa #3, #5, #7").
2. Các phát hiện **đã chốt, không mở lại** (theo số).
3. Điểm **còn bất đồng**: giữ nguyên trong file, để PO quyết, không tranh luận lại.
4. File/mục nguồn cần đối chiếu (đường dẫn + mục, hoặc mã D-xxx để Grep).
5. **Ảnh chụp trạng thái**, chép từ báo cáo ≤ 200 từ của agent trước, không đọc lại task để viết:
   ```
   Trạng thái: <status>; xong: S01, S02 (commit abc1234); đang: S03
   File/interface agent trước đổi: <đường dẫn>; <METHOD /path> hoặc kiểu/props
   Còn mở: #3, #5 (mục 4 vòng 1); lỗi QA: —
   Đọc: task.md mục 1 (AC2, AC3), 2 (phần API) — theo README mục 7 quy tắc 13
   ```
6. **Quyết định đang treo:** DR còn mở hoặc vừa chốt, và phần nào phải làm lại theo nó.
7. **Reviewer sẽ kiểm:** bảng tự kiểm áp dụng và điểm riêng của lượt này. Brief **người làm** ghi cùng danh sách đó, không để chỉ người rà biết.
8. **Đầu ra bắt buộc:** ví dụ bảng Tự kiểm đã điền, kết quả `check_task.py`.
9. **Đóng việc:** ai đánh dấu cột "Đã sửa?" và ai ghi dòng `**Kết quả:**`, theo quyền theo mục của dự án; gộp các điểm còn lại vào một lượt.

Hook `brief_guard.py` chặn brief giao agent (trừ `pm`, lượt `haiku`) có mã task mà thiếu một trong bốn dòng `Quyết định đang treo:`, `Reviewer sẽ kiểm:`, `Đầu ra bắt buộc:`, `Đóng việc:` (không có gì thì ghi `không có`). Lượt lập kế hoạch: brief mở bằng `Chế độ: lập kế hoạch` (luật: skill `agent-ops:agent-orchestration` quy tắc 8).

Người rà soát vòng sau vẫn được nêu phát hiện mới, nhưng ghi rõ "mới ở vòng n".
