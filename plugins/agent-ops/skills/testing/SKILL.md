---
name: testing
description: Chiến lược và quy ước test chung (kim tự tháp, tối thiểu mỗi endpoint, đường lỗi ghi DB, mock dịch vụ ngoài, chạy nhanh/đầy đủ, bằng chứng chạy test). Dùng khi viết/sửa test, test lỗi, hoặc nghiệm thu. Lệnh, fixture, framework cụ thể: skill dự án trong .claude/project-profile.md.
---

# Testing

Framework, fixture, lệnh chạy và ngưỡng coverage của dự án: skill dự án mà `.claude/project-profile.md` liệt kê (thường `project-testing`) và mục lệnh trong `CLAUDE.md`.

## Kim tự tháp
- **Unit** (nhiều nhất): hàm thuần, validator, hook giao diện.
- **Slice/integration**: mỗi endpoint test qua HTTP với **DB thật** (container hoặc DB test), không mock DB. Handler tự `commit()` nên không dựa vào "rollback session sau mỗi test". Hai cách cô lập:
  - **Mặc định — savepoint:** mỗi test một transaction ngoài; mỗi request một session riêng join vào transaction đó (`create_savepoint`), đóng session khi request xong; `commit()` của handler chỉ chốt savepoint. Bước kiểm/đọc lại trong test dùng **session khác**, không dùng lại session của request. Cuối test rollback transaction ngoài.
  - **Ngoại lệ — dọn bảng:** test cần nhiều connection thật (request song song, khoá `FOR UPDATE`) → đánh dấu marker riêng, dùng session thường và truncate các bảng liên quan sau test.
- **E2E**: Playwright cho các luồng chính trong AC.

## Backend
- Test nằm cạnh code của slice/module; fixture dùng chung ở thư mục test gốc, nạp cho mọi test.
- Mỗi endpoint tối thiểu: happy path · validation 422 · chưa đăng nhập 401 · truy cập dữ liệu user khác (404/403) · edge case từ AC.
- Endpoint tạo bản ghi với ID do client sinh: thêm ca gửi lại cùng `id`, `id` của người khác, `id` sai định dạng.
- Đường lỗi có ghi DB (thu hồi phiên, đếm sai, khoá, audit): sau response lỗi **đọc lại DB bằng session khác** để chắc thay đổi đã commit; dùng chung session thì test vẫn pass khi handler quên `commit()`.
- Dịch vụ ngoài (LLM, giọng nói, email, lưu trữ): mock ở mức adapter, không gọi mạng thật.
- Tên test mô tả hành vi: `test_create_item_retry_same_id_returns_200`.
- Test dùng thời gian thật (`sleep`, `now`, TTL): không tính lại giá trị phụ thuộc đồng hồ sau `sleep`; tiêm đồng hồ hoặc gửi lại đúng giá trị cũ.

## Frontend
- Test đơn vị (Vitest) + Testing Library; mock API bằng MSW. Không test chi tiết cài đặt; test cái người dùng thấy.

## Chạy
Hai chế độ (script/lệnh cụ thể: skill dự án):
- **fast** (vòng dev, mỗi subtask): chỉ test của phần code đã đổi (working tree + commit từ `main`); chạm hạ tầng dùng chung, migration, fixture, cấu hình, file chưa map → tự chạy full. Test chậm gắn marker `slow`, bị bỏ qua ở fast trừ khi chính file test đó bị sửa.
- **full**: cả bộ. Không thay thế cho nhau. Khi nào chạy full:
  - **CI trên mỗi PR** (mở PR nháp khi task vào `in_review`): cửa cả bộ chính; QA dẫn link CI xanh, không chạy cả bộ local. Không merge PR có check chưa xanh.
  - **Local hằng tuần**, QA chạy trước retro (CI khác môi trường local); CI định kỳ trên `main`.
  - **Ca ép chạy full local:** đổi script dev/DB ngoài phạm vi CI, CI không chạy được, trước phát hành, trước deploy production.
- Không bật coverage ở vòng dev (chậm); chỉ CI chạy coverage.

## Bằng chứng chạy test (`--record`)
- Dev chạy lệnh test của dự án với tuỳ chọn ghi bằng chứng vào `management/tasks/<epic>/<task>/evidence/`: file `test-run.json` (`sha`, `dirty`, `mode`, `command`, `exit_code`, `passed`/`failed`/`skipped`, `duration_s`, `finished_at`, `log`).
- Reviewer/qa **không chạy lại** unit/integration khi `sha` = HEAD của nhánh, `dirty=false`, `exit_code=0` và CI trên head SHA xanh. QA chỉ chạy E2E và kiểm AC chưa có test tự động.
- Chạy lại khi SHA lệch, `dirty=true`, hoặc nghi flaky; ghi lý do vào báo cáo.
