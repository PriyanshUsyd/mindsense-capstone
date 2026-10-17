"""Private dual-model acceptance preparation and explicitly gated real HTTP run.

prepare: capture real metadata/data bindings and GET a dedicated application.
check: verify a plan and its captured bindings, without reading questions.
run: requires a complete approved plan and explicit matching hash confirmation.
No synthetic packets, injected model clients, retries, scoring or resume mode.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from urllib import error, request

from backend.statistics.private_files import (
    is_owner_only,
    private_dir,
    write_private_text,
)
from benchmarks import slm_week10_acceptance_readiness as readiness
from benchmarks import slm_week10_acceptance_recorder as recorder

ROOT = Path(__file__).resolve().parents[1]
PREPARATION_ROOT = ROOT / "outputs/week10-acceptance-preparation"
SELF = "benchmarks/slm_week10_acceptance_adapter.py"
TOOLS = (
    SELF,
    "benchmarks/slm_week10_acceptance_recorder.py",
    "benchmarks/slm_week10_acceptance_readiness.py",
)
DEPENDENCIES = ("requirements.txt", "requirements-r.txt", "constraints-python312.txt")
FEATURES = ("gps_distance", "unlock_count")
PROTOCOL = "docs/slm/week10-independent-acceptance-preparation.md"
NORMALIZATION = "v2: remove generated_at; replace process pseudonym in participant_ref and packet_id; retain all other fields"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def local_file(path):
    """Private artifacts stay inside this checkout's ignored outputs tree."""
    path = Path(path).resolve(strict=True)
    require(path.is_relative_to((ROOT / "outputs").resolve()), "private_path_scope")
    require(path.is_file() and is_owner_only(path, is_dir=False), "private_file_acl")
    require(
        subprocess.run(
            ["git", "check-ignore", "-q", "--", str(path)], cwd=ROOT, check=False
        ).returncode
        == 0,
        "private_file_not_ignored",
    )
    return path


def source_files():
    names = set(git("ls-files", "--", "backend").splitlines())
    # Include extra importable/config files even if accidentally Git-ignored.
    for path in (ROOT / "backend").rglob("*"):
        if (
            path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix in {".py", ".yaml", ".yml", ".json", ".toml", ".sql"}
        ):
            names.add(path.relative_to(ROOT).as_posix())
    names.update((*TOOLS, *DEPENDENCIES, PROTOCOL))
    names.add(".gitignore")
    if (ROOT / ".gitattributes").exists():
        names.add(".gitattributes")
    for name in names:
        path = ROOT / name
        require(
            path.resolve().is_relative_to(ROOT) and path.is_file(), "source_path_scope"
        )
    return {name: sha(ROOT / name) for name in sorted(names)}


def data_files():
    from backend.statistics import bootstrap, bootstrap_cache
    from backend.statistics.feature_specs import TIER1_FEATURE_SPECS

    names = ["dataset/Sensing/sensing.csv", "dataset/EMA/general_ema.csv"]
    for feature in sorted(TIER1_FEATURE_SPECS):
        directory = bootstrap_cache.cache_dir(feature, engine=bootstrap.ENGINE_PYTHON)
        for path in (bootstrap_cache.CACHE_ROOT, directory.parent, directory):
            require(is_owner_only(path, is_dir=True), "cache_directory_acl")
        for name in (
            bootstrap_cache.RAW_CHECKPOINT_NAME,
            bootstrap_cache.RAW_FINGERPRINT_NAME,
            bootstrap_cache.AGGREGATED_NAME,
        ):
            path = directory / name
            require(is_owner_only(path, is_dir=False), "cache_file_acl")
            names.append(path.relative_to(ROOT).as_posix())
    return {name: sha(ROOT / name) for name in sorted(names)}


def normalize_packet(packet):
    normalized = json.loads(json.dumps(packet))
    identity = normalized["identity"]
    pseudonym = identity["participant_ref"]
    require(
        isinstance(pseudonym, str)
        and pseudonym.startswith("p_")
        and identity["packet_id"].count(pseudonym) == 1,
        "unexpected_packet_identity",
    )
    identity.pop("generated_at")
    identity["packet_id"] = identity["packet_id"].replace(pseudonym, "local-demo")
    identity["participant_ref"] = "local-demo"
    return normalized


def context_binding():
    from backend.statistics.participant_evidence import (
        _evidence_table,
        build_evidence_packet,
        select_local_demo_participant,
    )

    rows = []
    for feature in FEATURES:
        participant = select_local_demo_participant(feature)
        packet = build_evidence_packet(participant, feature_id=feature)
        table = _evidence_table(feature)
        require(
            table.table is not None and table.unavailable_reason is None,
            "context_cache_unavailable",
        )
        require(packet.feature_window.observed_days > 0, "no_recent_observations")
        require(
            packet.baseline.eligibility_status.value
            in {"eligible", "partial_descriptive_only"},
            "context_not_usable",
        )
        rows.append(
            {
                "feature_id": feature,
                "selection_rule": "existing local-demo resolver independently per feature",
                "as_of_rule": "last sensing day for resolved participant and feature",
                "comparison_days": packet.feature_window.expected_days,
                "eligibility_status": packet.baseline.eligibility_status.value,
                "ineligible_reason": packet.baseline.ineligible_reason,
                "normalized_packet_sha256": canonical_hash(
                    normalize_packet(packet.model_dump(mode="json"))
                ),
            }
        )
    return {"normalization": NORMALIZATION, "features": rows}


def runtime_binding():
    from backend.slm.request_policy import REQUEST_POLICY_VERSION
    from backend.slm.runtime import create_local_service

    installed = {
        m["name"]: m["digest"]
        for m in readiness.get_runtime_metadata("/api/tags")["models"]
    }
    require(
        all(installed.get(m) == h for m, h in readiness.MODELS.items()),
        "model_digest_mismatch",
    )
    clients = {}
    for model in recorder.MODELS:
        client = create_local_service(model_tag=model).client
        clients[model] = {
            "config": client.config.model_dump(mode="json"),
            "prompt_sha256": client.prompt.sha256,
            "prompt_version": client.prompt.manifest.prompt_version,
        }
    return {
        "ollama_version": readiness.get_runtime_metadata("/api/version")["version"],
        "model_digests": readiness.MODELS,
        "clients": clients,
        "policy_version": REQUEST_POLICY_VERSION,
    }


def environment_binding():
    require(os.environ.get("MINDSENSE_SLM_RUNTIME") == "ollama", "runtime_environment")
    return {
        "python_version": platform.python_version(),
        "python_executable_sha256": sha(sys.executable),
        "platform": platform.platform(),
        "distributions": sorted(
            [d.metadata["Name"].lower(), d.version]
            for d in importlib.metadata.distributions()
        ),
        "runtime_environment": {
            k: os.environ.get(k)
            for k in ("MINDSENSE_SLM_RUNTIME", "MINDSENSE_OLLAMA_TIMEOUT_SECONDS")
        },
    }


def check_module_origins():
    for name, module in list(sys.modules.items()):
        if name.startswith(("backend.", "benchmarks.")) and getattr(
            module, "__file__", None
        ):
            require(
                Path(module.__file__).resolve().is_relative_to(ROOT),
                "import_from_other_checkout",
            )


def capture_binding(*, validate_cache=False):
    sources = source_files()
    data = data_files()
    if validate_cache:
        readiness.cache_check()  # Existing B=500, no rebuilding or model requests.
    binding = {
        "format": 2,
        "head": git("rev-parse", "HEAD"),
        "origin_main": git("rev-parse", "refs/remotes/origin/main"),
        "application_changes": git(
            "status", "--porcelain", "--", "backend", *DEPENDENCIES
        ).splitlines(),
        "source_hashes": sources,
        "data_cache_hashes": data,
        "runtime": runtime_binding(),
        "environment": environment_binding(),
        "context": context_binding(),
    }
    tracked_backend = set(git("ls-files", "--", "backend").splitlines())
    binding["application_changes"] += [
        "extra_file " + name
        for name in sources
        if name.startswith("backend/") and name not in tracked_backend
    ]
    check_module_origins()
    require(
        source_files() == sources and data_files() == data,
        "inputs_changed_during_capture",
    )
    return binding


def require_final_binding(plan, binding):
    require(binding["format"] == 2, "binding_format")
    require(
        binding["head"] == binding["origin_main"] == plan["formal_build_commit"],
        "not_approved_main",
    )
    require(not binding["application_changes"], "application_not_clean")
    require(
        binding["runtime"]["policy_version"] == plan["expected_policy_version"],
        "policy_binding",
    )
    require(
        binding["runtime"]["model_digests"]
        == plan["model_digests"]
        == readiness.MODELS,
        "model_binding",
    )
    require(
        binding["source_hashes"][SELF] == plan["execution_adapter_sha256"],
        "adapter_binding",
    )
    require(
        binding["source_hashes"][TOOLS[1]] == plan["execution_harness_sha256"],
        "recorder_binding",
    )
    require(
        binding["source_hashes"][PROTOCOL] == plan["proposed_protocol_sha256"],
        "protocol_binding",
    )


class RequestGate:
    """Dedicated harness boundary; leaves the application's implementation intact."""

    def __init__(self, app, token, execution_enabled):
        self.app, self.token, self.execution_enabled = app, token, execution_enabled

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        authorized = secrets.compare_digest(
            headers.get(b"x-acceptance-session", b""), self.token.encode()
        )
        allowed = scope.get("method") == "GET" and scope.get("path") in {
            "/health",
            "/models",
        }
        allowed |= (
            self.execution_enabled
            and scope.get("method") == "POST"
            and scope.get("path") == "/respond"
        )
        if (
            scope["type"] != "http"
            or not authorized
            or not allowed
            or scope.get("query_string")
        ):
            if scope["type"] == "websocket":
                return await send({"type": "websocket.close", "code": 1008})
            await send(
                {
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [
                        (b"cache-control", b"no-store"),
                        (b"content-type", b"application/json"),
                    ],
                }
            )
            return await send(
                {
                    "type": "http.response.body",
                    "body": b'{"detail":"acceptance gate closed"}',
                }
            )
        return await self.app(scope, receive, send)


class RealApplicationAdapter(AbstractContextManager):
    """Real loopback HTTP to a dedicated same-process production ASGI instance."""

    def __init__(self, binding, *, execution_enabled=False):
        self.binding, self.execution_enabled = binding, execution_enabled
        self.token = secrets.token_hex(32)
        self.opener = request.build_opener(
            request.ProxyHandler({}), readiness.NoRedirects()
        )
        timeout = max(
            c["config"]["timeout_seconds"]
            for c in binding["runtime"]["clients"].values()
        )
        self.http_timeout = timeout + 60
        self.posts = 0
        self.server = self.thread = self.sock = None

    def __enter__(self):
        import uvicorn

        from backend.api.app import create_app

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.base_url = "http://127.0.0.1:" + str(self.sock.getsockname()[1])
        app = RequestGate(
            create_app(runtime_name="ollama"), self.token, self.execution_enabled
        )
        self.server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                loop="asyncio",
                log_config=None,
                log_level="critical",
                access_log=False,
                timeout_graceful_shutdown=5,
            )
        )
        self.thread = threading.Thread(
            target=self.server.run, kwargs={"sockets": [self.sock]}, daemon=True
        )
        self.thread.start()
        deadline = time.monotonic() + 20
        while not self.server.started:
            if not self.thread.is_alive() or time.monotonic() >= deadline:
                self.__exit__(None, None, None)
                raise RuntimeError("dedicated_app_start_failed")
            time.sleep(0.05)
        return self

    def __exit__(self, *exc):
        if self.server:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=7)
        if self.sock:
            self.sock.close()

    def exchange(self, method, path, payload=None):
        require(
            (method, path)
            in {("GET", "/health"), ("GET", "/models"), ("POST", "/respond")},
            "http_path",
        )
        require(method != "POST" or self.execution_enabled, "execution_gate_closed")
        headers = {
            "X-Acceptance-Session": self.token,
            "Content-Type": "application/json",
        }
        body = (
            None
            if payload is None
            else json.dumps(payload, ensure_ascii=False).encode()
        )
        req = request.Request(
            self.base_url + path, data=body, headers=headers, method=method
        )
        if method == "POST":
            self.posts += 1  # A timeout remains an attempt, never silently retried.
        try:
            response = self.opener.open(req, timeout=self.http_timeout)
        except error.HTTPError as exc:
            response = exc  # Preserve the actual non-2xx body and headers too.
        with response:
            raw = response.read()
            result = {
                "status_code": response.code,
                "headers": dict(response.headers),
                "raw_body_base64": base64.b64encode(raw).decode("ascii"),
            }
        try:
            result["body"] = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            result["body"] = None
        return result

    def metadata(self):
        health, models = (
            self.exchange("GET", "/health"),
            self.exchange("GET", "/models"),
        )
        require(
            health["status_code"] == models["status_code"] == 200, "app_metadata_http"
        )
        require(health["body"] == {"status": "ok"}, "app_health")
        catalog = models["body"]
        require(
            catalog["runtime"] == "ollama"
            and catalog["selection_enabled"] is True
            and set(recorder.MODELS) <= set(catalog["available_model_tags"]),
            "app_catalog",
        )
        return {
            "dedicated_live_http": True,
            "catalog": catalog,
            "post_requests": self.posts,
            "outer_http_timeout_seconds": self.http_timeout,
        }

    def verify_binding(self):
        require(capture_binding() == self.binding, "frozen_binding_changed")
        require(self.thread.is_alive(), "dedicated_app_stopped")
        self.metadata()

    def post(self, payload):
        from backend.slm.service import SafeSLMResponse

        require(
            set(payload) == {"participant_id", "question", "model_tag", "variant"}
            and payload["participant_id"] == "local-demo"
            and payload["variant"] == "rag"
            and payload["model_tag"] in recorder.MODELS,
            "formal_payload_scope",
        )
        result = self.exchange("POST", "/respond", payload)
        issues = []
        try:
            response = SafeSLMResponse.model_validate(result["body"])
            expected = self.binding["runtime"]["clients"][payload["model_tag"]][
                "prompt_sha256"
            ]
            if (
                response.generation_prompt_sha256 is not None
                and response.generation_prompt_sha256 != expected
            ):
                issues.append("generation_prompt_hash")
            if (
                response.fallback_prompt_sha256 is not None
                and response.fallback_prompt_sha256
                not in {
                    digest
                    for name, digest in self.binding["source_hashes"].items()
                    if name.startswith("backend/slm/prompts/")
                    and name.endswith(".yaml")
                }
            ):
                issues.append("fallback_prompt_hash")
        except (ValueError, TypeError):
            issues.append("response_schema")
        result["binding_issues"] = issues
        return result


def load_plan(path):
    return json.loads(local_file(path).read_text(encoding="utf-8"))


def validate_plan(plan):
    problems = recorder.plan_problems(plan)
    require(not problems, "plan_incomplete: " + ", ".join(problems))
    require(
        subprocess.run(
            ["git", "check-ignore", "-q", "--", "outputs/week10-formal-acceptance/"],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0,
        "formal_output_not_ignored",
    )
    manifest_path = local_file(plan["local_context_manifest_local_path"])
    require(
        sha(manifest_path) == plan["local_context_manifest_sha256"], "manifest_hash"
    )
    binding = json.loads(manifest_path.read_text(encoding="utf-8"))["binding"]
    require_final_binding(plan, binding)
    require(capture_binding(validate_cache=True) == binding, "captured_binding_changed")
    return binding


def run_formal(plan, confirmation):
    require(
        confirmation == plan.get("question_file_sha256"), "explicit_hash_confirmation"
    )
    binding = validate_plan(plan)  # No question read and no server before all gates.
    question_path = local_file(plan["question_file_local_path"])
    provenance_path = local_file(plan["provenance_file_local_path"])
    require(sha(provenance_path) == plan["provenance_file_sha256"], "provenance_hash")
    require(sha(question_path) == plan["question_file_sha256"], "question_hash")
    with RealApplicationAdapter(binding, execution_enabled=True) as adapter:
        result = recorder.record_once(
            plan,
            question_path,
            post=adapter.post,
            verify_binding=adapter.verify_binding,
        )
    return result


def prepare(name):
    require(
        bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", name)),
        "output_name",
    )
    private_dir(PREPARATION_ROOT)
    directory = PREPARATION_ROOT / name
    directory.mkdir(exist_ok=False)
    private_dir(directory)
    binding = capture_binding(validate_cache=True)
    with RealApplicationAdapter(binding) as adapter:
        metadata = adapter.metadata()
        adapter.verify_binding()
    require(adapter.posts == 0, "unexpected_preparation_post")
    manifest = {
        "status": "CAPTURED_CANDIDATE_NOT_AUTHORIZATION",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "binding": binding,
        "live_http_metadata": metadata,
        "formal_questions_read": 0,
        "respond_requests": 0,
        "generation_requests": 0,
    }
    path = directory / "environment-context-manifest.json"
    write_private_text(path, json.dumps(manifest, indent=2) + "\n")
    report = {
        "technical_preparation_passed": True,
        "formal_ready": False,
        "application_clean": not binding["application_changes"],
        "model_tags": list(recorder.MODELS),
        "manifest_sha256": sha(path),
        "formal_questions_read": 0,
        "respond_requests": 0,
        "generation_requests": 0,
    }
    write_private_text(
        directory / "preparation-summary.json", json.dumps(report, indent=2) + "\n"
    )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("prepare").add_argument("--output-name", required=True)
    for name in ("check", "run"):
        sub = subs.add_parser(name)
        sub.add_argument("--plan", type=Path, required=True)
        if name == "run":
            sub.add_argument("--confirm-once", required=True)
    args = parser.parse_args(argv)
    os.environ["MINDSENSE_SLM_RUNTIME"] = "ollama"
    try:
        if args.command == "prepare":
            result = prepare(args.output_name)
        elif args.command == "check":
            validate_plan(load_plan(args.plan))
            result = {
                "bindings_match": True,
                "approval_authenticity_checked": False,
                "formal_questions_read": 0,
                "formal_execution_performed": False,
            }
        else:
            result = run_formal(load_plan(args.plan), args.confirm_once)
        print(json.dumps(result))
        return 0 if result.get("status") != "incomplete_retained_no_retry" else 1
    except Exception as exc:  # noqa: BLE001 - never expose private exception text
        print(
            json.dumps(
                {
                    "completed": False,
                    "error_type": type(exc).__name__,
                    "automatic_retry": False,
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
