---
name: lessons-learned
description: Học từ lỗi - gắn mã nhóm lỗi khi review/QA/phản biện, ghi bài học (/lesson), retro hằng tuần (/retro), đề xuất rào chắn và sửa luật qua phiếu DR. Dùng khi review, nghiệm thu, phản biện, khi PO chỉ ra lỗi, hoặc khi retro.
---

# Học từ lỗi

Luật và mã nhóm lỗi: `management/lessons/README.md`.

## 1. Reviewer / QA / decision-reviewer: gắn nhóm cho mọi nhận xét
- Bảng nhận xét có cột **Nhóm** (mã trong README mục 1). Không bỏ trống.
- Nhận xét trùng một `LL-xxx` đã có rào chắn → ghi thêm `tái phạm LL-xxx` trong nhận xét. Đây là tín hiệu rào chắn chưa đủ.

## 2. `/lesson` — PO chỉ ra lỗi trực tiếp
1. Ghi một dòng vào `LESSONS.md` với trạng thái `ghi nhận`, nguồn = "PO (ngày)", kèm trích lời PO và file/task liên quan.
2. Không sửa luật ngay. Bài học được xử lý ở retro gần nhất.
3. Nếu lỗi đang nằm trong một sản phẩm chưa xong → sửa sản phẩm đó như việc bình thường của task.

## 3. `/retro` — hằng tuần (PM chủ trì)
1. `python3 "${CLAUDE_PLUGIN_ROOT}/tools/retro_stats.py" --since <thứ Hai tuần này>`; `--dump` để xem từng nhận xét.
2. Nhận xét thiếu nhóm → PM gắn nhóm (ghi trong báo cáo retro, không sửa bảng của reviewer).
3. So với tuần trước và các LL đang áp dụng: rào chắn nào hiệu quả, nhóm nào không giảm.
4. Mỗi nhóm lặp ≥ 2 lần hoặc có Blocker: tìm nguyên nhân gốc, viết LL-xxx, chọn rào chắn **bậc cao nhất làm được**.
5. Gom mọi đề xuất sửa luật thành **một phiếu DR** (loại 1, quy tắc 1.12 của `decision-policy.md`), mỗi đề xuất một mã `P1, P2…` để PO duyệt từng cái. decision-reviewer phản biện phiếu như mọi phiếu khác.
6. Ghi `management/lessons/retros/YYYY-Www.md` theo `${CLAUDE_PLUGIN_ROOT}/templates/retro.md`.
7. PO duyệt → PM giao người sửa (architect cho skill/CLAUDE.md, pm cho file agent và template), cập nhật trạng thái LL thành `áp dụng (D-xxx)`.

## 4. Viết bài học tốt
- Bằng chứng cụ thể: link task/DR + số dòng nhận xét.
- Nguyên nhân gốc phải sửa được bằng một thay đổi cụ thể ("mẫu DR không có ô nào hỏi về ADR bị sửa"), không phải "agent sơ ý".
- Rào chắn phải kiểm chứng được ở retro sau (đếm được nhóm lỗi giảm hay không).

