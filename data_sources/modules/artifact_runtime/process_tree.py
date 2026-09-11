"""Platform-neutral process-tree controller selection."""

from __future__ import annotations

import os
import subprocess
from typing import Any, Protocol


class ProcessTreeController(Protocol):
    def popen_options(self) -> dict[str, Any]: ...

    def attach(self, process: subprocess.Popen[bytes]) -> None: ...

    def terminate(self, process: subprocess.Popen[bytes]) -> None: ...

    def kill(self, process: subprocess.Popen[bytes]) -> None: ...

    def close(self) -> None: ...


def create_process_tree_controller() -> ProcessTreeController:
    if os.name == "nt":
        from .process_tree_windows import WindowsProcessTreeController

        return WindowsProcessTreeController()
    from .process_tree_posix import PosixProcessTreeController

    return PosixProcessTreeController()
