import unittest

import branch_guard as g


def hit(command: str) -> bool:
    return any(g.tracks_base(words, "main") for words in g.segments(command))


class BranchGuard(unittest.TestCase):
    def test_denied(self):
        for cmd in ("git switch -c feat/x origin/main", "git checkout -b feat/x origin/main",
                    "git fetch && git switch -c feat/x origin/main && ls", "git -C repo branch feat/x origin/main",
                    "git worktree add -b feat/x ../w origin/main", "git fetch\ngit switch --create feat/x origin/main",
                    "# note\ngit switch -c x origin/main", "cat <<EOF\nit's here\nEOF\ngit switch -c x origin/main",
                    "git switch --create=x origin/main", "git switch -cx origin/main",
                    "echo $((1<<2))\ngit switch -c x origin/main", "ls # it's\ngit switch -c x origin/main"):
            self.assertTrue(hit(cmd), cmd)

    def test_allowed(self):
        for cmd in ("git switch -c feat/x --no-track origin/main", "git switch -c feat/x",
                    "git switch -c feat/x main", "git diff origin/main", "git switch main",
                    "git checkout -b main origin/main", "git commit -m 'git switch -c a origin/main'",
                    "git branch -u origin/main main", "git log origin/main; git switch -c feat/x",
                    "git worktree add --detach ../w origin/main", "git switch -c feat/x origin/feat/x",
                    "git commit -m 'a\ngit switch -c a origin/main'", "cat <<'EOF'\ngit switch -c a origin/main\nEOF",
                    "# git switch -c a origin/main", "git switch --create=main origin/main"):
            self.assertFalse(hit(cmd), cmd)


if __name__ == "__main__":
    unittest.main()
