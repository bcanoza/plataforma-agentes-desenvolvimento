from app.testing.runtime import TestOrchestrator
from app.testing.fs_testing import register_fs_ops, register_fs_tests

def test_fs_suites():
    """
    Executa as suítes de FS registradas (smoke, binary).
    Certifique-se de chamar register_fs_ops antes de register_fs_tests.
    """
    orch = TestOrchestrator()
    register_fs_ops(orch)
    register_fs_tests(orch)

    for suite in ["smoke", "binary"]:
        report = orch.run_suite(suite=suite, run_name="pytest", cleanup=True)
        assert report.get("ok", False), f"Falhas na suíte {suite}: {report}"
