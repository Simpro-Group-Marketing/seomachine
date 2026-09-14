from tools.check_python_structure import forbidden_structure_errors


def test_forbidden_structure_rejects_wildcards_and_dynamic_module_proxies() -> None:
    sources = {
        "wildcard.py": "from package import *\n",
        "module_proxy.py": "import sys\nsys.modules[__name__] = implementation\n",
        "global_proxy.py": "globals()[name] = factory(name)\n",
        "explicit.py": "from package import exported\n",
    }

    assert forbidden_structure_errors(sources) == [
        "global_proxy.py:1 uses globals() for dynamic dispatch",
        "module_proxy.py:2 uses sys.modules for dynamic dispatch",
        "wildcard.py:1 uses a wildcard import",
    ]
