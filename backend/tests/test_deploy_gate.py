import unittest

from svandoc_backend.deploy_gate import evaluate_runpod_readiness


class DeployGateTests(unittest.TestCase):
    def test_gate_passes_when_primary_and_fallback_are_ok(self) -> None:
        smoke = {
            "result_code": "SMOKE_OK",
            "overall_success": True,
            "checks": [
                {"role": "primary", "status": "ok", "failure_codes": []},
                {"role": "fallback", "status": "ok", "failure_codes": []},
            ],
        }

        passed, summary = evaluate_runpod_readiness(smoke)

        self.assertTrue(passed)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["blocking_failures"], [])

    def test_gate_fails_when_a_required_role_is_missing(self) -> None:
        smoke = {
            "result_code": "SMOKE_OK",
            "overall_success": True,
            "checks": [{"role": "primary", "status": "ok", "failure_codes": []}],
        }

        passed, summary = evaluate_runpod_readiness(smoke)

        self.assertFalse(passed)
        self.assertIn("FALLBACK_CHECK_MISSING", summary["blocking_failures"])

    def test_gate_fails_when_target_check_has_failure_codes(self) -> None:
        smoke = {
            "result_code": "PRIMARY_COMPLETION_FAILED",
            "overall_success": False,
            "checks": [
                {
                    "role": "primary",
                    "status": "failed",
                    "failure_codes": ["PRIMARY_COMPLETION_FAILED"],
                },
                {"role": "fallback", "status": "ok", "failure_codes": []},
            ],
        }

        passed, summary = evaluate_runpod_readiness(smoke)

        self.assertFalse(passed)
        self.assertIn("PRIMARY_COMPLETION_FAILED", summary["blocking_failures"])
        self.assertIn("OVERALL_SUCCESS_FALSE", summary["blocking_failures"])

    def test_gate_fails_when_result_code_is_not_smoke_ok(self) -> None:
        smoke = {
            "result_code": "UNKNOWN",
            "overall_success": True,
            "checks": [
                {"role": "primary", "status": "ok", "failure_codes": []},
                {"role": "fallback", "status": "ok", "failure_codes": []},
            ],
        }

        passed, summary = evaluate_runpod_readiness(smoke)

        self.assertFalse(passed)
        self.assertIn("UNKNOWN", summary["blocking_failures"])


if __name__ == "__main__":
    unittest.main()
