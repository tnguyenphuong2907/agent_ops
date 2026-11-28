import unittest

import branch_guard as g


def hit(command: str) -> bool:
    return any(g.tracks_base(words, "main") for words in g.segments(command))


class BranchGuard(unittest.TestCase):
    def test_denied(self):
        for cmd in ("git switch -c feat/x origin/main", "git checkout -b feat/x origin/main",
                    "git fetch && git switch -c feat/x origin/main && ls", "git -C repo branch feat/x origin/main",
                    "git worktree add -b feat/x ../w origin/main", "git fetch\ngit switch --create feat/x origin/main"):
            self.assertTrue(hit(cmd), cmd)

    def test_allowed(self):
        for cmd in ("git switch -c feat/x --no-track origin/main", "git switch -c feat/x",
                    "git switch -c feat/x main", "git diff origin/main", "git switch main",
                    "git checkout -b main origin/main", "git commit -m 'git switch -c a origin/main'",
                    "git branch -u origin/main main", "git log origin/main; git switch -c feat/x",
                    "git worktree add --detach ../w origin/main", "git switch -c feat/x origin/feat/x"):
            self.assertFalse(hit(cmd), cmd)


if __name__ == "__main__":
    unittest.main()
