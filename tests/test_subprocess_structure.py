from tools.check_python_structure import forbidden_structure_errors


def test_subprocess_creation_is_owned_by_bounded_runtime() -> None:
    sources = {
        "subprocess_module.py": "import subprocess as sp\nsp.run(['unsafe'])\n",
        "subprocess_symbol.py": (
            "from subprocess import Popen as launch\nlaunch(['unsafe'])\n"
        ),
        "data_sources/modules/artifact_runtime/subprocesses.py": (
            "import subprocess\nsubprocess.Popen(['owned'])\n"
        ),
    }

    assert forbidden_structure_errors(sources) == [
        "subprocess_module.py:2 bypasses bounded subprocess execution",
        "subprocess_symbol.py:2 bypasses bounded subprocess execution",
    ]
