"""Public prompting comparison regressions; no real model or sealed input."""

import json
from types import SimpleNamespace

import pytest

from backend.slm.client import SLMUnavailableError
from benchmarks import slm_prompting_comparison as comparison


class GroundedTransport:
    def __init__(self):
        self.payloads = []

    def post_json(self, endpoint, payload, timeout_seconds):
        self.payloads.append(payload)
        user = json.loads(payload["messages"][1]["content"])
        return {
            "message": {
                "content": json.dumps(
                    {
                        "packet_id": user["evidence_packet"]["identity"]["packet_id"],
                        **user["allowed_response_options"][0],
                    }
                )
            }
        }


@pytest.fixture(scope="module")
def result():
    return comparison.run_comparison(
        transport_factory=lambda condition: GroundedTransport()
    )


def test_fixed_cases_repeats_exclusions_and_human_fields(result):
    assert result["status"] == "development_checks_passed"
    assert result["execution_backend"] == "injected_transport_not_live"
    assert len(result["records"]) == 180
    assert sum(r["execution_status"] == "not_covered" for r in result["records"]) == 12
    for condition in ("Z", "F"):
        summary = result["summaries"][condition]
        assert summary["model_calls"] == 12
        assert (
            summary["valid_schema_calls"] == summary["grounding_accepted_calls"] == 12
        )
        assert summary["benign_controls"] == 15
        assert summary["benign_unexpected_refusals"] == 0
        assert summary["groups"]["source_plan"]["executions"] == 18
        assert summary["groups"]["guardrail_high_severity"]["executions"] == 42
        assert summary["groups"]["guardrail_privacy_extension"]["executions"] == 6
        assert summary["groups"]["off_topic"]["executions"] == 15
        assert summary["groups"]["state_b_supplement"]["executions"] == 3
        assert summary["human_quality_pass_rate"] is None
    for row in result["records"]:
        assert all(value is None for value in row["human_review"].values())
    assert result["paired_comparison"]["pairs"] == 84
    assert result["paired_comparison"]["identical_response_text"] == 84


def test_actual_condition_prompts_reach_transport_and_are_recorded():
    transports = {c: GroundedTransport() for c in ("Z", "F")}
    result = comparison.run_comparison(transport_factory=transports.get)
    z, f = (result["conditions"][c]["prompt_sha256"] for c in ("Z", "F"))
    assert z != f
    for condition, transport in transports.items():
        assert len(transport.payloads) == 12
        for payload in transport.payloads:
            system = payload["messages"][0]["content"]
            assert (comparison.DEMO_MARKER in system) == (condition == "F")
            assert payload["options"] == {"temperature": 0, "seed": 42}
            assert payload["think"] is False
            assert payload["format"]["title"] == "AssistantDraft"
    for row in result["records"]:
        if row["response"] and row["response"]["model_invoked"]:
            assert (
                row["response"]["generation_prompt_sha256"]
                == row["condition_prompt_sha256"]
            )
            assert row["model_calls"][0]["system_sha256"]
            assert row["model_calls"][0]["raw_content"]
    assert result["source_hashes_still_match"]


def test_order_is_balanced_and_first_calls_are_separated(result):
    first = [r for r in result["records"] if r["position_in_pair"] == 1]
    assert sum(r["condition"] == "Z" for r in first) == 45
    assert sum(r["condition"] == "F" for r in first) == 45
    for condition in ("Z", "F"):
        assert (
            sum(
                r["first_call_for_condition"]
                for r in result["records"]
                if r["condition"] == condition
            )
            == 1
        )
        assert result["summaries"][condition]["subsequent_calls_n"] == 11
    orders = [
        call["global_call_order"]
        for row in result["records"]
        for call in row["model_calls"]
    ]
    assert orders == list(range(1, 25))


def test_invalid_outputs_are_preserved_without_selective_retry():
    class InvalidTransport(GroundedTransport):
        def post_json(self, endpoint, payload, timeout_seconds):
            super().post_json(endpoint, payload, timeout_seconds)
            return {"message": {"content": "this is not JSON"}}

    transports = {"Z": GroundedTransport(), "F": InvalidTransport()}
    checkpoints = []
    result = comparison.run_comparison(
        transport_factory=transports.get,
        on_checkpoint=lambda value: checkpoints.append(len(value["records"])),
    )
    assert result["status"] == "development_checks_failed"
    assert len(result["records"]) == 180
    assert checkpoints[:3] == [2, 4, 6]
    assert checkpoints[-1] == 180
    assert len(transports["F"].payloads) == 12
    assert result["summaries"]["F"]["valid_schema_calls"] == 0
    assert result["summaries"]["F"]["unexpected_fallbacks"] == 12
    assert len(result["paired_comparison"]["z_pass_f_fail"]) == 12
    calls = [
        c for r in result["records"] if r["condition"] == "F" for c in r["model_calls"]
    ]
    assert all(c["raw_content"] == "this is not JSON" for c in calls)


def test_transport_failure_keeps_all_attempts_and_no_human_pass():
    class Offline:
        def post_json(self, *args):
            raise SLMUnavailableError("synthetic unavailable runtime")

    result = comparison.run_comparison(transport_factory=lambda _: Offline())
    assert result["status"] == "development_checks_failed"
    assert len(result["records"]) == 180
    for summary in result["summaries"].values():
        assert summary["model_calls"] == summary["unexpected_fallbacks"] == 12
        assert summary["groups"]["guardrail_high_severity"]["automated_passed"] == 42
        assert summary["groups"]["off_topic"]["automated_passed"] == 15
        assert summary["human_quality_pass_rate"] is None
    assert all(
        c["transport_error"] == "SLMUnavailableError"
        for r in result["records"]
        for c in r["model_calls"]
    )


def test_wrong_but_schema_valid_draft_is_not_a_pass():
    class WrongPacket(GroundedTransport):
        def post_json(self, *args):
            result = super().post_json(*args)
            draft = json.loads(result["message"]["content"])
            draft["packet_id"] = "synthetic_wrong_packet"
            result["message"]["content"] = json.dumps(draft)
            return result

    result = comparison.run_comparison(
        transport_factory=lambda c: WrongPacket() if c == "F" else GroundedTransport()
    )
    assert result["summaries"]["F"]["valid_schema_calls"] == 12
    assert result["summaries"]["F"]["grounding_accepted_calls"] == 0
    assert result["summaries"]["F"]["unexpected_fallbacks"] == 12
    assert result["status"] == "development_checks_failed"


def test_non_synthetic_packet_is_rejected_before_transport():
    entry = comparison.load_public_cases()[0]
    _protocol, prompts = comparison.load_conditions(comparison.load_public_cases())
    packet = entry["packet"]
    entry["packet"] = packet.model_copy(
        update={
            "identity": packet.identity.model_copy(
                update={"participant_ref": "non-synthetic"}
            )
        }
    )
    transport = GroundedTransport()
    observer = comparison.RecordingTransport(transport)
    client = comparison.OllamaClient(
        comparison.OllamaClientConfig(model_tag=comparison.MODEL),
        transport=observer,
        prompt=prompts["Z"],
    )
    with pytest.raises(ValueError, match="synthetic"):
        comparison.assess(
            entry, comparison.SLMService(client), observer, "Z", prompts["Z"], 1
        )
    assert observer.calls == transport.payloads == []


def test_demonstration_overlap_or_changed_controls_fail_before_generation(monkeypatch):
    original = comparison.load_evidence_prompt

    def altered(path):
        prompt = original(path)
        if str(path).endswith("week9_few_shot_prompt.yaml"):
            text, examples = prompt.manifest.system_text.split(comparison.DEMO_MARKER)
            parsed = json.loads(examples)
            parsed[0]["question"] = comparison.load_public_cases()[0]["case"][
                "question"
            ]
            manifest = prompt.manifest.model_copy(
                update={
                    "system_text": text + comparison.DEMO_MARKER + json.dumps(parsed)
                }
            )
            return comparison.LoadedEvidencePrompt(
                manifest, prompt.sha256, prompt.source_path
            )
        return prompt

    # Preserve the immutable manifest wrapper; only inject a deliberate bad example.
    from backend.slm.prompt_loader import LoadedEvidencePrompt

    monkeypatch.setattr(
        comparison, "LoadedEvidencePrompt", LoadedEvidencePrompt, raising=False
    )
    monkeypatch.setattr(comparison, "load_evidence_prompt", altered)
    with pytest.raises(ValueError, match="overlaps"):
        comparison.run_comparison(
            transport_factory=lambda _: pytest.fail("must not run")
        )


def test_provenance_uses_only_explicit_paths_and_rejects_unlisted_before_access(
    monkeypatch,
):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(stdout="fixed-head" if "rev-parse" in command else "")

    monkeypatch.setattr(comparison.subprocess, "run", fake_run)
    metadata = comparison.git_metadata()
    status = next(c for c in commands if "status" in c)
    assert tuple(status[status.index("--") + 1 :]) == comparison.SOURCE_FILES
    assert metadata["source_scope_dirty"] is False
    assert all("held_out" not in path for path in comparison.SOURCE_FILES)
    with pytest.raises(ValueError, match="allow-list"):
        comparison.allowed_path("unlisted-private-file.json")


def test_cli_refuses_to_overwrite_evidence_or_write_elsewhere(tmp_path, monkeypatch):
    monkeypatch.setattr(comparison, "ROOT", tmp_path)
    history = tmp_path / "benchmarks/history"
    history.mkdir(parents=True)
    path = history / "existing.json"
    path.write_text("existing evidence", encoding="utf-8")
    with pytest.raises(SystemExit):
        comparison.main(["--out", str(path)])
    assert path.read_text(encoding="utf-8") == "existing evidence"
    outside = tmp_path / "outside.json"
    with pytest.raises(SystemExit):
        comparison.main(["--out", str(outside)])
    assert not outside.exists()
