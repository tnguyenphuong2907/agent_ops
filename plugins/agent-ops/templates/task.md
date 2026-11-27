---
id: E00-T00
epic: E00
title: "<Tên task>"
type: feature            # feature | bug | chore | doc | design | db | test
lane:                    # L1 | L2 | L3 (xem `<mgmt>/README.md`, quy tắc làn)
flow:                    # F<nn> nếu là task luồng (≤ 3 ngày, ≤ 6 subtask, có BE + FE + E2E); trống nếu không
status: backlog          # backlog | ready | in_progress | in_review | in_qa | done | blocked
priority: P1
assignee:                # <agent hoặc người làm>
reviewer:                # code-reviewer | db-reviewer | idea-reviewer
qa: qa
planned_date:            # ngày dự kiến làm (task lớn = 1 ngày)
estimate_hours:
actual_hours:
depends_on: []
links: []                # D-xxx liên quan, tài liệu, ADR, PR, commit
---

# E00-T00 — <Tên task>

## 1. Yêu cầu & Tiêu chí nghiệm thu  ·  _chủ sở hữu: pm / product-analyst_
### Bối cảnh
<Tại sao cần làm? Liên quan user story nào?>

### Yêu cầu
-

### Tiêu chí nghiệm thu (AC)
- [ ] **AC1** — Given … When … Then …
- [ ] **AC2** —

### Ngoài phạm vi
-

## 2. Thiết kế kỹ thuật  ·  _chủ sở hữu: architect / db-designer / ui-designer_
- API: `METHOD /path` — request/response tóm tắt hoặc link
- DB: bảng/cột thay đổi, migration
- UI: màn hình, link prototype/Figma
- Ghi chú: hiệu năng, bảo mật, edge case

## Subtasks
| ID | Tiêu đề | Người làm | Ước lượng (h) | Trạng thái |
|---|---|---|---|---|
| E00-T00-S01 | | | | backlog |

## 3. Tiến trình thực hiện  ·  _chủ sở hữu: dev được giao_
> Ghi theo thời gian, ngắn gọn. Mỗi subtask xong ghi commit hash.
> Ghi giờ: chạy `date` lúc bắt đầu và lúc kết thúc mỗi subtask, ghi vào dòng subtask.
> Task kiểu "đồng bộ/chuyển quy tắc": sau khi sửa, ghi lệnh `grep` theo ID quy tắc (PT-xx, D-xxx, tên mục), số kết quả và danh sách file (không chép từng dòng). "Chuyển" = bản cũ thay bằng ≤ 1 câu + link trong cùng subtask, không xoá trắng. Người rà: reviewer của task. Kết quả quét ghi **sau subtask sửa cuối**, kèm mã subtask đó; sửa thêm thì quét lại và ghi lại. Reviewer chạy lại đúng lệnh đã ghi, lệch số kết quả hoặc danh sách file = `DRIFT`. Không ghi hash commit.

- [ ] E00-T00-S01 —

**Ghi chú kỹ thuật cho người sau:**
-

## 4. Review  ·  _chủ sở hữu: code-reviewer / db-reviewer_
**Kết quả:** ⏳ Chờ review  <!-- ✅ Approved | 🔁 Changes requested -->

| # | Mức độ | Nhóm | File:dòng | Nhận xét | Đã sửa? |
|---|---|---|---|---|---|

## 5. Nghiệm thu QA  ·  _chủ sở hữu: qa_
**Kết quả:** ⏳ Chưa kiểm thử  <!-- ✅ Passed | ❌ Failed -->

| AC | Cách kiểm tra | Kết quả | Bằng chứng |
|---|---|---|---|
| AC1 | | | `evidence/...` |

**Lỗi phát hiện:** _(mỗi lỗi ghi mức độ + mã nhóm, xem `<mgmt>/lessons/README.md`)_
| # | Mức độ | Nhóm | Mô tả | Xử lý |
|---|---|---|---|---|

## 6. ⚠️ Cần quyết định  ·  _chỉ ghi link tới phiếu DR — xem skill `decision-requests`_
> Bắt buộc: mỗi điểm cần PO ở mục 7/8 một link DR, hoặc ghi `Không có (đã đối chiếu mục 7, 8)`.
<!--
- [DR-012](../../../decision-requests/DR-012-slug.md) — <câu hỏi> · trạng thái: open
-->

## 7. Trao đổi · 8. Lịch sử
> Ghi ở [`log.md`](log.md) cạnh file này (copy `templates/log.md`). Mục 6 "đã đối chiếu mục 7, 8" là đối chiếu `log.md`.
