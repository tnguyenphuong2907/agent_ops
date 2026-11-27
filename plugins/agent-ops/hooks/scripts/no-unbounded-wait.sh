#!/bin/bash
# PreToolUse(Bash): chặn vòng chờ không giới hạn thời gian (until/while ... sleep) trừ khi bọc `timeout N`.
# Lý do: vòng chờ như vậy bị chuyển xuống nền, sống lâu hơn subagent và giữ agent cha không được dọn.
# Hook nhận JSON qua stdin; exit 2 = chặn, stderr được gửi lại cho agent.
input=$(cat)
if printf '%s' "$input" | grep -Eq '(until|while)[^"]*sleep'; then
  if ! printf '%s' "$input" | grep -Eq 'timeout +[0-9]'; then
    echo "Bị chặn: vòng chờ until/while + sleep không có giới hạn thời gian. Bọc bằng 'timeout N bash -c ...', hoặc chạy lệnh dài bằng 'sh scripts/dev/test.sh' (foreground) / run_in_background rồi chờ thông báo hoàn thành." >&2
    exit 2
  fi
fi
exit 0
