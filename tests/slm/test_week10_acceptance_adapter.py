"""Toy-only adapter checks: never open the sealed candidate, CES or Ollama."""

import asyncio
import base64
import copy
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from benchmarks import slm_week10_acceptance_adapter as adapter
from benchmarks import slm_week10_acceptance_recorder as recorder


@pytest.fixture
def binding():
    return {
        "format": 2,
        "head": "1" * 40,
        "origin_main": "1" * 40,
        "application_changes": [],
        "source_hashes": {
            adapter.SELF: "a" * 64,
            adapter.TOOLS[1]: "b" * 64,
            adapter.PROTOCOL: "c" * 64,
            "backend/slm/prompts/toy.yaml": "d" * 64,
        },
        "runtime": {
            "policy_version": "0.3.5",
            "model_digests": dict(adapter.readiness.MODELS),
            "clients": {
                m: {"config": {"timeout_seconds": 180}, "prompt_sha256": "e" * 64}
                for m in recorder.MODELS
            },
        },
        "context": {"toy": True},
        "data_cache_hashes": {"toy": "f" * 64},
    }


@pytest.fixture
def plan(binding):
    return {
        "formal_run_authorized": True,
        "formal_build_commit": binding["head"],
        "expected_policy_version": "0.3.5",
        "model_tags": list(recorder.MODELS),
        "model_digests": dict(adapter.readiness.MODELS),
        "execution_adapter_sha256": "a" * 64,
        "execution_harness_sha256": "b" * 64,
        "proposed_protocol_sha256": "c" * 64,
        "question_file_sha256": "f" * 64,
        "local_context_manifest_sha256": "d" * 64,
        "hash_publication_at_utc": "2020-01-01T00:00:00Z",
        **{
            field: "TEST-ONLY declaration, no real approval"
            for field in recorder.REFERENCE_FIELDS
        },
    }


def toy_body(model):
    return {
        "response_mode": "normal",
        "text": "Toy response only.",
        "used_fallback": False,
        "rejection_reason": None,
        "model_tag": model,
        "generation_prompt_sha256": "e" * 64,
        "fallback_prompt_sha256": None,
        "metrics": None,
        "request_disposition": "allow",
        "request_category": "in_scope",
        "request_policy_version": "0.3.5",
        "model_invoked": True,
    }


def test_normalization_survives_process_pseudonym_but_preserves_evidence():
    packet = {
        "identity": {
            "participant_ref": "p_alpha",
            "packet_id": "real_gps_p_alpha_2020-01-01",
            "generated_at": "yesterday",
        },
        "evidence": {"value": 8},
    }
    other = copy.deepcopy(packet)
    other["identity"] = {
        "participant_ref": "p_beta",
        "packet_id": "real_gps_p_beta_2020-01-01",
        "generated_at": "today",
    }
    assert adapter.normalize_packet(packet) == adapter.normalize_packet(other)
    other["evidence"]["value"] = 9
    assert adapter.normalize_packet(packet) != adapter.normalize_packet(other)
    assert packet["identity"]["participant_ref"] == "p_alpha"


@pytest.mark.parametrize(
    "field", ["head", "origin_main", "application_changes", "runtime", "source_hashes"]
)
def test_final_gate_rejects_nonfinal_or_mismatched_candidate(binding, plan, field):
    if field in {"head", "origin_main"}:
        binding[field] = "2" * 40
    elif field == "application_changes":
        binding[field] = [" M backend/toy.py"]
    elif field == "runtime":
        binding[field]["model_digests"][recorder.MODELS[1]] = "0" * 64
    else:
        binding[field][adapter.SELF] = "0" * 64
    with pytest.raises(ValueError):
        adapter.require_final_binding(plan, binding)


def test_json_roundtrip_preserves_environment(monkeypatch):
    monkeypatch.setenv("MINDSENSE_SLM_RUNTIME", "ollama")
    value = adapter.environment_binding()
    assert json.loads(json.dumps(value)) == value


def test_cache_paths_use_statistics_names_not_api_aliases(tmp_path, monkeypatch):
    from backend.statistics import bootstrap_cache

    visited = []
    monkeypatch.setattr(adapter, "ROOT", tmp_path)
    monkeypatch.setattr(bootstrap_cache, "CACHE_ROOT", tmp_path / "cache")

    def directory(feature, *, engine):
        assert feature in {"loc_dist_ep_0", "unlock_num_ep_0"}
        visited.append(feature)
        return tmp_path / "cache" / engine / feature

    monkeypatch.setattr(bootstrap_cache, "cache_dir", directory)
    monkeypatch.setattr(adapter, "is_owner_only", lambda *a, **kw: True)
    monkeypatch.setattr(adapter, "sha", lambda path: "a" * 64)
    files = adapter.data_files()
    assert visited == ["loc_dist_ep_0", "unlock_num_ep_0"]
    assert len(files) == 8


@pytest.mark.parametrize(
    "field", ["formal_run_authorized", "reviewer", "hash_publication_reference"]
)
def test_unapproved_run_never_opens_question_or_server(plan, monkeypatch, field):
    plan[field] = None
    monkeypatch.setattr(
        adapter, "local_file", lambda _: pytest.fail("private file read")
    )
    monkeypatch.setattr(
        adapter, "RealApplicationAdapter", lambda *a, **kw: pytest.fail("server opened")
    )
    with pytest.raises(ValueError, match="plan_incomplete"):
        adapter.run_formal(plan, plan["question_file_sha256"])


def test_run_needs_exact_explicit_hash_before_any_plan_read(plan, monkeypatch):
    monkeypatch.setattr(adapter, "validate_plan", lambda _: pytest.fail("plan read"))
    with pytest.raises(ValueError, match="explicit_hash_confirmation"):
        adapter.run_formal(plan, "wrong")


@pytest.mark.parametrize(
    "enabled,method,path,token,status",
    [
        (False, "POST", "/respond", "token", 403),
        (False, "GET", "/models", "token", 200),
        (True, "POST", "/respond", "wrong", 403),
        (True, "POST", "/respond", "token", 200),
        (True, "GET", "/docs", "token", 403),
    ],
)
def test_http_gate_never_passes_preparation_posts_to_app(
    enabled, method, path, token, status
):
    called, sent = [], []

    async def app(scope, receive, send):
        called.append(scope)
        await send({"type": "http.response.start", "status": 200})

    async def receive():
        pytest.fail("toy request body should not be read")

    async def send(event):
        sent.append(event)

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [(b"x-acceptance-session", token.encode())],
    }
    asyncio.run(adapter.RequestGate(app, "token", enabled)(scope, receive, send))
    assert sent[0]["status"] == status
    assert bool(called) == (status == 200)


def test_post_is_blocked_even_before_opener_in_prepare_mode(binding):
    transport = adapter.RealApplicationAdapter(binding)
    with pytest.raises(ValueError, match="execution_gate_closed"):
        transport.exchange("POST", "/respond", {"question": "unused toy"})
    assert transport.posts == 0


class FakeResponse(io.BytesIO):
    code = 200

    def __init__(self, raw):
        super().__init__(raw)
        self.headers = {"Cache-Control": "no-store"}


@pytest.mark.parametrize("model", recorder.MODELS)
def test_selected_model_payload_and_full_wire_reply_preserved(binding, model):
    transport = adapter.RealApplicationAdapter(binding, execution_enabled=True)
    transport.base_url = "http://127.0.0.1:12345"
    raw = json.dumps(toy_body(model)).encode()
    seen = []

    def opened(req, timeout):
        seen.append((req, timeout))
        return FakeResponse(raw)

    transport.opener.open = opened
    payload = {
        "participant_id": "local-demo",
        "question": "Toy only.",
        "model_tag": model,
        "variant": "rag",
    }
    result = transport.post(payload)
    assert len(seen) == transport.posts == 1
    assert json.loads(seen[0][0].data) == payload
    assert seen[0][1] == 240
    assert base64.b64decode(result["raw_body_base64"]) == raw
    assert result["binding_issues"] == []
    assert not recorder.response_problems(result, model, "0.3.5")


def test_timeout_has_no_retry(binding):
    transport = adapter.RealApplicationAdapter(binding, execution_enabled=True)
    transport.base_url = "http://127.0.0.1:12345"

    def timeout(*args, **kwargs):
        raise TimeoutError("toy only")

    transport.opener.open = timeout
    with pytest.raises(TimeoutError):
        transport.exchange("POST", "/respond", {"question": "Toy only."})
    assert transport.posts == 1


def test_http_error_and_non_json_body_preserved(binding):
    transport = adapter.RealApplicationAdapter(binding, execution_enabled=True)
    transport.base_url = "http://127.0.0.1:12345"
    raw = b"toy invalid reply\xff"

    def opened(*args, **kwargs):
        raise HTTPError(
            transport.base_url,
            500,
            "toy",
            {"Cache-Control": "no-store"},
            io.BytesIO(raw),
        )

    transport.opener.open = opened
    result = transport.exchange("POST", "/respond", {"question": "Toy only."})
    assert result["status_code"] == 500 and result["body"] is None
    assert base64.b64decode(result["raw_body_base64"]) == raw
    assert transport.posts == 1


@pytest.mark.parametrize(
    "field", ["generation_prompt_sha256", "fallback_prompt_sha256", "schema"]
)
def test_invalid_prompt_binding_retains_response_and_stops_recorder(binding, field):
    transport = adapter.RealApplicationAdapter(binding, execution_enabled=True)
    body = toy_body(recorder.MODELS[0])
    if field == "schema":
        body["model_invoked"] = "invalid"
    else:
        body[field] = "0" * 64
    transport.exchange = lambda *args: {
        "status_code": 200,
        "headers": {"Cache-Control": "no-store"},
        "body": body,
    }
    result = transport.post(
        {
            "participant_id": "local-demo",
            "question": "Toy only.",
            "model_tag": recorder.MODELS[0],
            "variant": "rag",
        }
    )
    assert result["body"] is body and result["binding_issues"]
    assert "adapter_response_binding" in recorder.response_problems(
        result, recorder.MODELS[0], "0.3.5"
    )


@pytest.mark.parametrize(
    "changed", ["context", "data_cache_hashes", "source_hashes", "runtime"]
)
def test_binding_drift_stops_before_dispatch(binding, monkeypatch, changed):
    transport = adapter.RealApplicationAdapter(binding, execution_enabled=True)
    actual = copy.deepcopy(binding)
    actual[changed] = {"changed": True}
    monkeypatch.setattr(adapter, "capture_binding", lambda: actual)
    with pytest.raises(ValueError, match="frozen_binding_changed"):
        transport.verify_binding()
    assert transport.posts == 0


def test_prepare_receipt_is_not_authorization_and_has_zero_posts(
    tmp_path, binding, monkeypatch
):
    monkeypatch.setattr(adapter, "PREPARATION_ROOT", tmp_path)
    monkeypatch.setattr(
        adapter, "private_dir", lambda p: p.mkdir(exist_ok=True, parents=True)
    )
    monkeypatch.setattr(
        adapter,
        "write_private_text",
        lambda p, text: p.write_text(text, encoding="utf-8"),
    )
    monkeypatch.setattr(adapter, "capture_binding", lambda **kw: binding)

    class FakeAdapter:
        posts = 0

        def __init__(self, received, *, execution_enabled=False):
            assert received == binding and not execution_enabled

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def metadata(self):
            return {"post_requests": 0}

        def verify_binding(self):
            return None

    monkeypatch.setattr(adapter, "RealApplicationAdapter", FakeAdapter)
    result = adapter.prepare("toy")
    assert result["technical_preparation_passed"] and not result["formal_ready"]
    assert result["respond_requests"] == result["generation_requests"] == 0
    manifest = json.loads(
        (tmp_path / "toy/environment-context-manifest.json").read_text()
    )
    assert manifest["binding"] == binding
    assert manifest["status"] == "CAPTURED_CANDIDATE_NOT_AUTHORIZATION"


@pytest.mark.parametrize("qwen_binding_failure", [False, True])
def test_full_toy_recording_through_http_adapter(
    binding, plan, tmp_path, monkeypatch, qwen_binding_failure
):
    cases = []
    for category, count in recorder.COUNTS.items():
        for index in range(count):
            case = {
                "id": f"toy-{len(cases)}",
                "category": category,
                "prompt": f"Recorder-only toy slot {len(cases)}.",
                "expected": "Unscored toy metadata.",
            }
            if category == "crisis":
                case["subtype"] = "direct" if index < 4 else "indirect"
            cases.append(case)
    path = tmp_path / "toy.json"
    path.write_text(json.dumps(cases), encoding="utf-8")
    plan["question_file_sha256"] = adapter.sha(path)
    plan["execution_harness_sha256"] = adapter.sha(Path(recorder.__file__))
    monkeypatch.setattr(recorder, "OUTPUT_ROOT", tmp_path / "records")
    monkeypatch.setattr(
        recorder, "private_dir", lambda p: p.mkdir(exist_ok=True, parents=True)
    )
    monkeypatch.setattr(recorder, "restrict_to_owner", lambda *a, **kw: None)
    transport = adapter.RealApplicationAdapter(binding, execution_enabled=True)
    transport.base_url = "http://127.0.0.1:12345"
    payloads = []

    def opened(req, timeout):
        payload = json.loads(req.data)
        payloads.append(payload)
        body = toy_body(payload["model_tag"])
        if qwen_binding_failure and payload["model_tag"] == recorder.MODELS[1]:
            body["generation_prompt_sha256"] = "0" * 64
        return FakeResponse(json.dumps(body).encode())

    transport.opener.open = opened
    result = recorder.record_once(
        plan, path, post=transport.post, verify_binding=lambda: None
    )
    assert len(payloads) == transport.posts == (25 if qwen_binding_failure else 48)
    assert [p["model_tag"] for p in payloads[:24]] == [recorder.MODELS[0]] * 24
    assert result["completed"][recorder.MODELS[1]] == (
        1 if qwen_binding_failure else 24
    )
    assert result["status"] == (
        "incomplete_retained_no_retry"
        if qwen_binding_failure
        else "recorded_pending_human_review"
    )
    assert result["human_ratings"] is result["safety_decision"] is None
    journal = (
        recorder.OUTPUT_ROOT / plan["question_file_sha256"] / "journal.jsonl"
    ).read_text()
    assert '"raw_body_base64"' in journal
    with pytest.raises(FileExistsError):
        recorder.record_once(
            plan, path, post=transport.post, verify_binding=lambda: None
        )


@pytest.mark.parametrize("model", recorder.MODELS)
def test_real_http_route_with_synthetic_packet_and_fake_model(
    binding, monkeypatch, model
):
    import backend.api.app as api
    from backend.slm.runtime import create_local_service
    from benchmarks.slm_multiturn_eval import synthetic_packet

    calls = []

    class FakeModel:
        def post_json(self, endpoint, payload, timeout_seconds):
            calls.append(payload)
            user = json.loads(payload["messages"][1]["content"])
            return {
                "message": {
                    "content": json.dumps(
                        {
                            "packet_id": user["evidence_packet"]["identity"][
                                "packet_id"
                            ],
                            **user["allowed_response_options"][0],
                        }
                    )
                }
            }

    def service(*, model_tag=None):
        selected = create_local_service(model_tag=model_tag)
        selected.client.transport = FakeModel()
        return selected

    # Test process only: no production files or real dataset/model are modified.
    monkeypatch.setattr(api, "create_local_service", service)
    monkeypatch.setattr(
        api, "select_local_demo_participant", lambda feature: "synthetic-A"
    )
    monkeypatch.setattr(
        api,
        "build_evidence_packet",
        lambda participant, *, feature_id: synthetic_packet(participant, feature_id),
    )
    binding["runtime"]["clients"][model]["prompt_sha256"] = create_local_service(
        model_tag=model
    ).client.prompt.sha256
    with adapter.RealApplicationAdapter(binding, execution_enabled=True) as transport:
        assert transport.metadata()["catalog"]["selection_enabled"]
        result = transport.post(
            {
                "participant_id": "local-demo",
                "model_tag": model,
                "variant": "rag",
                "question": "Summarise my movement over the supported observation window.",
            }
        )
    assert not transport.thread.is_alive()
    assert transport.posts == len(calls) == 1
    assert calls[0]["model"] == result["body"]["model_tag"] == model
    assert not recorder.response_problems(result, model, "0.3.5")
    assert result["body"]["used_fallback"] is False
