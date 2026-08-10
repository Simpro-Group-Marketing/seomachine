import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "data_sources" / "modules" / "dataforseo.py"
)


def load_dataforseo_module():
    spec = importlib.util.spec_from_file_location("dataforseo_under_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DataForSEOResilienceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_dataforseo_module()
        self.client = object.__new__(self.module.DataForSEO)

    def test_get_serp_data_raises_contract_error_when_result_is_missing(self):
        self.client._post = lambda endpoint, data: {
            "status_code": 20000,
            "tasks": [{"status_code": 20000, "result": []}],
        }

        with self.assertRaisesRegex(self.module.DataForSEOContractError, "result"):
            self.client.get_serp_data("test keyword")

    def test_get_keyword_ideas_raises_contract_error_when_result_is_missing(self):
        self.client._post = lambda endpoint, data: {
            "status_code": 20000,
            "tasks": [{"status_code": 20000, "result": []}],
        }

        with self.assertRaisesRegex(self.module.DataForSEOContractError, "result"):
            self.client.get_keyword_ideas("seed keyword")

    def test_analyze_competitor_raises_contract_error_for_missing_result(self):
        self.client._post = lambda endpoint, data: {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "data": {"keyword": "keyword one"},
                    "result": [],
                }
            ],
        }

        with self.assertRaisesRegex(self.module.DataForSEOContractError, "result"):
            self.client.analyze_competitor(
                "competitor.com", ["keyword one"], your_domain="example.com"
            )


if __name__ == "__main__":
    unittest.main()
