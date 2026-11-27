---
name: merge-pr
description: Merge PR đủ điều kiện rồi dọn sau merge bằng script `merge_pr.py` của plugin. Chỉ PO gọi. PO gõ `mp [PR...]` = chạy script, 0 token.
argument-hint: "[PR...]  (bỏ trống = mọi PR đang mở + PR merge tay còn nhánh local)"
disable-model-invocation: true
context: fork
model: haiku
---

PO gõ `/merge-pr` = đồng ý merge các PR trong `$ARGUMENTS`. Mọi cổng (task `done`, xung đột chỉ ở file sinh, CI xanh của đúng head SHA (gồm check quét secret)), merge, dọn nhánh và ghi `management/HANDOFF.md` nằm trong script.

Chạy đúng một lệnh, foreground, không sửa gì thêm:
```bash
cd "${CLAUDE_PROJECT_DIR}" && timeout 1500 python3 "${CLAUDE_PLUGIN_ROOT}/tools/merge_pr.py" $ARGUMENTS
```
Trả về nguyên văn bảng báo cáo script in ra (stdout), thêm dòng `Tool:` nếu lệnh lỗi. Không tự sửa code, xung đột hay task khi script báo bỏ qua.
