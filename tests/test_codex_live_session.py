from __future__ import annotations

import os
import pwd
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from agents_inc.core.codex_app_client import CodexAppClient, CodexAppServerError


class CodexLiveSessionTests(unittest.TestCase):
    def test_live_codex_session_protocol_success(self) -> None:
        prompt = "Reply with exactly one word: OK. Do not use tools."
        attempt = 0
        started_at = time.time()
        real_home = Path(pwd.getpwuid(os.getuid()).pw_dir).expanduser().resolve()
        codex_home = real_home / ".codex"
        client_env = dict(os.environ)
        client_env["HOME"] = str(real_home)
        client_env["CODEX_HOME"] = str(codex_home)
        while True:
            attempt += 1
            client: CodexAppClient | None = None
            try:
                with tempfile.TemporaryDirectory() as td:
                    client = CodexAppClient(cwd=Path(td), env=client_env, approval_policy="never")
                    client.start()
                    thread_id = client.start_thread()
                    self.assertTrue(thread_id.strip())

                    turn = client.run_turn(thread_id=thread_id, text=prompt, timeout_sec=180.0)
                    self.assertTrue(turn.turn_id.strip())
                    self.assertTrue(turn.text.strip())
                    return
            except (CodexAppServerError, subprocess.SubprocessError, OSError) as exc:
                if attempt == 1 or attempt % 5 == 0:
                    elapsed = int(time.time() - started_at)
                    print(
                        f"[codex-live] retrying after attempt {attempt} (elapsed {elapsed}s): {exc}",
                        flush=True,
                    )
                time.sleep(min(30.0, 1.0 + float(attempt)))
            finally:
                if client is not None:
                    client.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
