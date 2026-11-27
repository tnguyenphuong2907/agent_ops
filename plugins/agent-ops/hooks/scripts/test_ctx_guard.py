"""Tests for ctx_guard.py Run: python3 -m unittest discover -s hooks/scripts -p 'test_*.py'."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).with_name("ctx_guard.py")


def run(payload: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(HOOK)], input=payload, capture_output=True, text=True,
                          env={**os.environ, **(env or {})}, check=False)


class CtxGuard(unittest.TestCase):
    def transcript(self, ctxs: list[int]) -> str:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        self.addCleanup(os.unlink, tmp.name)
        for i, c in enumerate(ctxs):
            tmp.write(json.dumps({"type": "assistant", "message": {"id": str(i), "usage": {
                "input_tokens": 1, "cache_read_input_tokens": c, "cache_creation_input_tokens": 0}}}) + "\n")
        tmp.write("not json\n")
        tmp.close()
        return json.dumps({"transcript_path": tmp.name})

    def test_over_threshold_uses_last_call(self):
        res = run(self.transcript([10, 160_000]))
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertIn("160K", out["systemMessage"])
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")

    def test_under_threshold_silent(self):
        res = run(self.transcript([200_000, 50_000]))
        self.assertEqual((res.returncode, res.stdout), (0, ""))

    def test_threshold_env(self):
        res = run(self.transcript([60_000]), {"CTX_GUARD_THRESHOLD": "50000"})
        self.assertIn("60K", res.stdout)

    def test_exactly_threshold_silent(self):
        res = run(self.transcript([150_000 - 1]))  # +1 input token = exactly 150K
        self.assertEqual(res.stdout, "")

    def test_null_usage_skipped_and_bad_env(self):
        payload = self.transcript([170_000])
        with open(json.loads(payload)["transcript_path"], "a", encoding="utf-8") as f:
            f.write(json.dumps({"type": "assistant", "message": {"usage": None}}) + "\n" + json.dumps([1]) + "\n")
        self.assertIn("170K", run(payload).stdout)
        self.assertEqual(run(payload, {"CTX_GUARD_THRESHOLD": "abc"}).returncode, 0)

    def test_large_file_reads_tail(self):
        payload = self.transcript([10])
        with open(json.loads(payload)["transcript_path"], "a", encoding="utf-8") as f:
            f.write(("x" * 1000 + "\n") * 5000)  # ~5 MB of junk, then the real last call
            f.write(json.dumps({"type": "assistant", "message": {"usage": {"cache_read_input_tokens": 180_000}}}) + "\n")
        self.assertIn("180K", run(payload).stdout)

    def test_bad_input_never_fails(self):
        for payload in ("", "{}", "not json", json.dumps({"transcript_path": "/no/such/file"})):
            res = run(payload)
            self.assertEqual((res.returncode, res.stdout), (0, ""), payload)


if __name__ == "__main__":
    unittest.main()
