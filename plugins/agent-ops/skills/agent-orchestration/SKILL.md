---
name: agent-orchestration
description: Luật phiên chính khi điều phối agent (chi tiết luật tiết kiệm token trong `CLAUDE.md` của dự án) - spawn mới hay SendMessage, brief, chọn model/effort, gom lượt, đếm token vòng phiếu DR, HANDOFF.md và nhắc /clear. Đọc trước lần spawn agent đầu tiên của phiên, trước vòng phiếu DR, và khi task/phiếu xong hoặc PO chuyển việc.
---

# Điều phối agent (phiên chính)

Nguồn luật: mục tiết kiệm token trong `CLAUDE.md` của dự án (tóm tắt, giữ số quy tắc). File này là chi tiết.

## Quy tắc 1–3: spawn hay SendMessage
1. **Không `SendMessage` giao việc mới hoặc việc tiếp cho agent đã xong quá 5 phút.** Cache đã hết hạn nên toàn bộ context của agent (thường 150–370K token) bị ghi lại từ đầu. Thay vào đó **spawn agent mới** với brief ngắn: mục tiêu, file + mục cần đọc, kết quả của agent trước (tóm tắt ≤ 10 dòng hoặc đường dẫn file).
2. Chỉ `SendMessage` khi agent vừa trả lời trong vòng 5 phút **và** việc tiếp là phần nhỏ của cùng việc (hỏi lại một điểm, sửa một chỗ).
3. Một agent một việc, xong là thôi. Không chạy song song nhiều agent cùng đọc một bộ tài liệu lớn; giao mỗi agent đúng phần nó cần.
   - Mỗi lượt giao việc trong một task (dev → review → sửa → QA) brief kèm **ảnh chụp trạng thái** (kết quả agent trước, `#n` còn mở, mục cần đọc) theo skill `agent-ops:task-management` § Giao việc, để agent sau không đọc lại mục 3–5 để dựng lại.
   - Phiếu DR còn mở mà phương án có thể đổi response hoặc hành vi → chờ chốt rồi mới giao phần phụ thuộc; chỉ chạy song song phần chắc chắn không bị ảnh hưởng, và brief ghi rõ phần đó.

## Quy tắc 7: vòng phiếu DR
Mỗi lượt agent của phiếu ghi `~NK` vào Lịch sử; tổng quá 200K token trên một phiếu thì báo PO ngay (một lần, chỉ báo), kèm bài toán gốc trong 3 câu. Chi tiết: skill `agent-ops:decision-requests` mục 7.

## Quy tắc 8: chọn model và effort
**Luôn truyền tham số `model` khi spawn agent** (agent của plugin gọi bằng `subagent_type: "agent-ops:<tên>"`, vd `agent-ops:architect`), chọn theo độ khó của việc lần này, không theo tên agent. `model` trong frontmatter của agent chỉ là mặc định khi quên truyền.

| Model | Việc |
|---|---|
| `haiku` | Cơ học: tra cứu, tìm file, tóm tắt một file, cập nhật trạng thái task/BOARD, chạy script kiểm tra (`build_inbox.py --check`…) |
| `sonnet` (mặc định) | PRD/user story, phản biện tính năng (idea-reviewer), kế hoạch/báo cáo ngày, code theo task (kể cả code đụng dữ liệu người dùng), test, UI, review code không đụng bảo mật, vòng 2 phản biện chỉ kiểm điểm cũ |
| `opus` | Lập kế hoạch cho subtask `plan: opus`, kiến trúc/ADR, schema và migration, phiếu DR loại 1 (soạn và phản biện vòng 1), review code đụng auth/khoá/mã hoá/dữ liệu người dùng (nguyên tắc bảo mật khoá/bí mật của dự án), bug khó qua nhiều tầng, hoặc khi lần giao trước bằng model thấp hơn bị trả lại vì thiếu sâu |

- Chọn khác mặc định của agent thì ghi lý do một dòng trong brief. Kết quả kém vì model thấp → giao lại bằng model cao hơn, và ghi `/lesson` nếu lặp lại.
- **`effort`:** việc mức `haiku` truyền `effort: "low"` (model không hỗ trợ thì bỏ tham số); vòng 2 phản biện/review chỉ kiểm điểm cũ và QA kiểm lại một điểm truyền `effort: "medium"`; còn lại để mặc định. Kết quả kém vì `effort` thấp → giao lại không đặt `effort`.
- **Việc vặt qua skill fork:** đóng task (`/close-task`), merge + dọn sau merge (`/merge-pr`) chạy trong skill `context: fork` + `model: haiku`: phiên chính chỉ nhận báo cáo ngắn. `/merge-pr` chỉ chạy khi PO gõ (là đồng ý merge). Logic ở `${CLAUDE_PLUGIN_ROOT}/tools/close_task.py`, `${CLAUDE_PLUGIN_ROOT}/tools/merge_pr.py`; PO gõ `ct [task-id]`, `mp [PR...]` thì hook `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/task_shortcuts.py` chạy script không gọi model (0 token).
- **Chia model theo bước:** scout `haiku` (gom ngữ cảnh, ghi context pack) → plan `opus` → thực thi `sonnet` → ghi chép cơ học `haiku`. Mỗi spawn tốn ~15–30K token khởi động: scout và ghi chép chỉ tách khi đáng; việc nhỏ giao một agent. `haiku` không viết PRD/ADR/DR/thiết kế.
- **Bước plan (bắt buộc với subtask `plan: opus`):** phiên chính spawn đúng agent dev của subtask với `model: opus`, brief có dòng `Chế độ: lập kế hoạch` và mã subtask; agent chỉ viết mục "Kế hoạch" rồi trả về. Sau đó spawn agent dev **mới** với `model: sonnet` để code theo kế hoạch. Dev chạy `opus` để **code** chỉ khi lần giao bằng sonnet bị trả lại hoặc bug khó qua nhiều tầng, và brief ghi `Lý do opus: …`. Hook `brief_guard.py` chặn spawn sai các điểm này.
- **Gom lượt cùng agent:** khi thứ tự cho phép, giao liền nhau (trong 5 phút) các lượt cùng loại agent và cùng model để dùng lại cache phần đầu (~15K token); không đổi thứ tự phụ thuộc chỉ vì việc này.

## Quy tắc 9: đổi việc, HANDOFF và /clear
Phiên chính không tự chạy được `/clear` (chỉ PO gõ). Khi:
- PO chuyển sang việc **không liên quan** việc đang làm (task/phiếu khác), hoặc
- một task/phiếu vừa xong (`done`, `decided`), hoặc một PR vừa merge, hoặc
- hook `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/ctx_guard.py` (UserPromptSubmit) báo ngữ cảnh phiên chính > 150K token,

thì xong việc đang làm, ghi `management/HANDOFF.md` (≤ 15 dòng: việc đang làm, mã task/phiếu, trạng thái, file đã sửa chưa commit, bước tiếp theo; ghi đè bản cũ, không commit), rồi nhắc PO một dòng: *"Nên chạy `/clear` trước khi sang việc mới; tóm tắt đã lưu ở `management/HANDOFF.md`."* (việc tiếp nhỏ, cùng chủ đề: gợi ý `/compact`). Chỉ nhắc, không dừng việc.

**Model phiên chính:** gợi ý PO dùng `/model opusplan` (Opus trong plan mode, Sonnet khi thực thi): việc cần suy nghĩ (thiết kế, phiếu DR, bug nhiều tầng) vào plan mode; điều phối, merge, cập nhật trạng thái chạy Sonnet. Đây là lựa chọn của PO, luật chỉ gợi ý.

## Quy tắc 10: đầu phiên mới
PO nói tiếp việc cũ → đọc `management/HANDOFF.md` trước, không đọc lại tài liệu để dựng lại ngữ cảnh.

## Quy tắc 11: context pack
Mỗi task có `management/tasks/<epic>/<task>/context.md` (mẫu `${CLAUDE_PLUGIN_ROOT}/templates/context-pack.md`). Người đầu tiên của task (hoặc scout `haiku`) ghi pack; agent sau đọc pack trước và chỉ mở nguồn theo `offset`/`limit` khi pack thiếu. `based_on` lệch HEAD và nguồn đã đổi thì cập nhật phần đổi, không viết lại cả pack.

## Quy tắc 12: lồng agent
Agent vai chính (pm, architect, product-analyst, backend-dev, frontend-dev, qa, code-reviewer) được spawn subagent **một tầng**, chỉ cho (a) scout: `Explore` hoặc agent `haiku` đọc nguồn và ghi context pack, (b) ghi chép cơ học `haiku`. Luôn truyền `model`. Reviewer độc lập (decision-reviewer, db-reviewer, idea-reviewer) không spawn. Cần `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=2` trong `.claude/settings.json`.
