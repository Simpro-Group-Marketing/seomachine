"""POSIX process-group control for bounded subprocesses."""

from __future__ import annotations

import os
import signal
import subprocess
from typing import Any


class PosixProcessTreeController:
    def popen_options(self) -> dict[str, Any]:
        return {"start_new_session": True}

    def attach(self, process: subprocess.Popen[bytes]) -> None:
        del process

    def terminate(self, process: subprocess.Popen[bytes]) -> None:
        self._signal_group(process, signal.SIGTERM)

    def kill(self, process: subprocess.Popen[bytes]) -> None:
        self._signal_group(process, signal.SIGKILL)

    def close(self) -> None:
        return

    @staticmethod
    def _signal_group(process: subprocess.Popen[bytes], signal_number: int) -> None:
        try:
            os.killpg(process.pid, signal_number)
        except ProcessLookupError:
            return
