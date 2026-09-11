"""persist_state_to_git の自己完結テスト（一時gitリポジトリを使用）"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paper_trading_runner import persist_state_to_git


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def test_persist_state_to_git_commits_and_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        run(["git", "init"], cwd=tmp)
        run(["git", "config", "user.email", "test@example.com"], cwd=tmp)
        run(["git", "config", "user.name", "Test"], cwd=tmp)

        import paper_trading_runner
        paper_trading_runner.SCRIPT_DIR = tmp

        data_file = os.path.join(tmp, "state.json")
        with open(data_file, "w") as f:
            f.write('{"trades": 1}')

        # remote pushなし: git pushはリモート未設定だと失敗するがCalledProcessErrorで捕捉される
        persist_state_to_git(["state.json"])

        log = subprocess.run(
            ["git", "log", "--oneline"], cwd=tmp, capture_output=True, text=True
        )
        assert "update paper trading state" in log.stdout

        # 変更なしで再実行 → 追加コミットが増えない
        commits_before = log.stdout.count("\n")
        persist_state_to_git(["state.json"])
        log2 = subprocess.run(
            ["git", "log", "--oneline"], cwd=tmp, capture_output=True, text=True
        )
        assert log2.stdout.count("\n") == commits_before


if __name__ == "__main__":
    test_persist_state_to_git_commits_and_is_idempotent()
    print("OK")
