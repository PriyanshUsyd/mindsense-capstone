from backend.slm.client import SLMUnavailableError
from backend.slm.service import SLMService
from benchmarks.slm_prohibited_request_baseline import ObservableSafeStub
from benchmarks.slm_shadow_smoke import run_smoke


def test_smoke_checks_all_four_paths_without_a_live_model():
    result = run_smoke(service=SLMService(ObservableSafeStub()))
    assert result["summary"] == {"passed": 4, "total": 4}
    assert result["scope"] == "synthetic_development_smoke_not_joint_or_held_out"


def test_smoke_does_not_count_unavailable_model_as_a_successful_happy_path():
    class Unavailable:
        def generate_draft(self, packet, question):
            raise SLMUnavailableError("synthetic offline model")

    result = run_smoke(service=SLMService(Unavailable()))
    assert result["summary"] == {"passed": 3, "total": 4}
    assert result["records"][0]["passed"] is False
