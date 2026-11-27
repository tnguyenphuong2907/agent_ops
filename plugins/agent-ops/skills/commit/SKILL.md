---
name: commit
description: Gom thay đổi chưa commit thành commit đúng quy ước (Conventional Commits + task ID, mỗi nhóm một commit, add đường dẫn cụ thể, chặn secret). Dùng khi PO gõ /commit hoặc yêu cầu commit, và khi agent tự commit subtask.
---

# Commit

Nguồn quy ước: mục Quy ước Git trong `CLAUDE.md` của dự án. Skill này là quy trình thực hiện.

Tham số (tuỳ chọn) sau `/commit`:
- trống → xét toàn bộ thay đổi chưa commit;
- đường dẫn / thư mục → chỉ xét phần đó;
- ghi chú tự do (vd "tách quy trình DR riêng") → dùng khi chia nhóm.

## 1. Khảo sát (chỉ đọc)
```bash
git branch --show-current
git status --short
git diff --stat
git log --oneline -10        # xem cách đặt message gần đây
```
- Đang ở `main` → **dừng**, đề xuất tạo nhánh `feat|fix|docs|chore/<task-id>-<slug>` và hỏi PO.
- Không có thay đổi → báo "không có gì để commit" và dừng.
- Đọc diff của từng file (`git diff <file>`; file mới: đọc nội dung) trước khi xếp nhóm. Không commit thứ mình chưa xem.

## 2. Chặn trước khi add
Loại khỏi kế hoạch và **báo PO** nếu gặp:
- `.env`, `.env.*` (trừ `.env.example`), `secrets/`, `*.pem`, `*.key`, file credentials;
- nội dung trông như secret: `sk-`, `AKIA`, `-----BEGIN`, chuỗi dài ngẫu nhiên gán cho biến có tên `KEY|TOKEN|SECRET|PASSWORD`;
- file build/cache (`node_modules/`, `dist/`, `__pycache__/`, `.venv/`…) hoặc file > 5 MB;
- file sinh tự động mà repo không theo dõi (kiểm `.gitignore`).

## 3. Chia nhóm
Mỗi commit = một ý thay đổi; **một subtask ≈ một commit**. Thứ tự ưu tiên khi xếp:
1. Theo task/subtask ID (đọc frontmatter file task, hoặc ID trong đường dẫn `management/tasks/...`).
2. Theo loại: quy trình/công cụ (`.claude/`, `CLAUDE.md`, `${CLAUDE_PLUGIN_ROOT}/templates/`, `${CLAUDE_PLUGIN_ROOT}/tools/`) tách khỏi nội dung quản lý (`management/decisions.md`, `BOARD.md`, `daily/`, `tasks/`), tách khỏi tài liệu sản phẩm (`docs/`), tách khỏi code (thư mục mã nguồn của dự án).
3. Một file chứa thay đổi của nhiều nhóm → không tách hunk được (không dùng lệnh tương tác) → xếp vào nhóm hợp lý nhất và ghi rõ trong body commit.

Luật nhánh: nhánh spike không merge main chỉ chứa `spikes/`; file ngoài `spikes/` commit trên nhánh tách từ main (`CLAUDE.md` của dự án). `BOARD.md` là file sinh: chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_board.py"` rồi mới add.

## 4. Message
Conventional Commits, tiếng Anh, kèm ID:
```
<type>(<scope>): <mô tả ngắn, mệnh lệnh, ≤ 72 ký tự> [<ID>]

<body tuỳ chọn: vì sao, phạm vi, ghi chú lẫn thay đổi>

Co-Authored-By: <theo attribution của phiên>
```
- `type`: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`.
- `scope`: slice/module hoặc khu vực (`<module>`, `skills`, `management`, `decisions`, `security`…).
- `<ID>`: subtask (`E02-T01-S02`), task (`E01-T09`), nhiều ID thì `[A] [B]`. Không có task → bỏ ID và ghi lý do ở body (vd thay đổi quy trình do PO làm trực tiếp).
- Dòng `Co-Authored-By` chỉ thêm khi Claude tạo commit, đúng nội dung attribution mà phiên chỉ định.

## 5. Xin xác nhận
Trình bày kế hoạch cho PO trước khi chạy, dạng bảng:

| # | Message | File |
|---|---|---|

kèm danh sách file **bị loại** (mục 2) và file **để lại không commit** (kèm lý do). Chờ PO đồng ý hoặc chỉnh. Nếu PO đã nói rõ "commit luôn, không cần hỏi" trong lần gọi này thì bỏ bước chờ, vẫn in kế hoạch.

## 6. Thực hiện
Với từng nhóm, theo thứ tự:
```bash
git add -- <đường dẫn 1> <đường dẫn 2> ...     # luôn liệt kê cụ thể
git diff --cached --stat                         # kiểm đúng file trước khi commit
git commit -F - <<'EOF'
<message>
EOF
```
- **Cấm**: `git add -A`, `git add .`, `git commit -a`, `--no-verify`, `--amend` commit đã có, `push --force`, sửa `git config`.
- Gặp `index.lock` (agent khác đang commit) → đợi vài giây rồi thử lại, không xoá file lock.
- Hook pre-commit báo lỗi → không bỏ qua; sửa nếu là lỗi của thay đổi này, nếu không thì dừng và báo PO.
- **Không push** trừ khi PO yêu cầu trong lần gọi này.

## 7. Báo cáo
```bash
git log --oneline -<số commit vừa tạo>
git status --short
```
Trả lời PO ngắn gọn: danh sách hash + message, file còn lại chưa commit và vì sao, việc tiếp theo nếu có (vd task chờ commit này để chuyển `done`, mở PR).
