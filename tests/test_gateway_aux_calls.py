"""Auxiliary (judge) calls share the session Gateway without joining the policy trajectory."""

from __future__ import annotations

from fastapi.testclient import TestClient

import gateway.app as gateway_app
from evaluator.trajectory_policy import is_trajectory_step, select_reward_target
from gateway.config import GatewayConfig, LLMRouteConfig
from gateway.inference_forwarder import ForwardResult
from gateway.storage import GatewayStorage
from gateway.trajectory_builder import build_gateway_step_row


class _Forwarder:
    def __init__(self, cfg) -> None:
        del cfg
        self.payloads = []

    def build_upstream_headers(self, target, **kwargs):
        del target, kwargs
        return {"Content-Type": "application/json"}

    async def forward_chat(self, target, payload, headers):
        del target, headers
        _Forwarder.instance.payloads.append(payload)
        return ForwardResult(
            body={
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "model": payload["model"],
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": f"reply from {payload['model']}"},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            },
            status_code=200,
            headers={},
            upstream_latency_ms=1.0,
        )

    async def close(self) -> None:
        return None

    def normalize_error(self, exc):
        return 500, {"error": {"message": str(exc)}}


class _Storage:
    def __init__(self) -> None:
        self.records = []

    async def bind_session_environment(self, binding) -> None:
        binding.job_id = "job-1"
        binding.env_name = "env"

    async def record_telemetry_batch(self, batch) -> None:
        self.records.extend(batch)

    async def record_inference_step(self, binding, record) -> None:
        self.records.append((binding, record))

    async def close(self) -> None:
        return None


def _client(monkeypatch, *, max_steps: int):
    def make_forwarder(cfg):
        _Forwarder.instance = _Forwarder(cfg)
        return _Forwarder.instance

    monkeypatch.setattr(gateway_app, "InferenceForwarder", make_forwarder)
    storage = _Storage()
    cfg = GatewayConfig(
        storage_type="sqlite",
        storage_config={"db_url": "sqlite://unused.db"},
        request_log_enabled=False,
        max_steps=max_steps,
        llm_routes={
            "policy-model": LLMRouteConfig(base_url="https://policy.example/v1", api_key="k"),
            "judge-model": LLMRouteConfig(base_url="https://judge.example/v1", api_key="k"),
        },
    )
    return TestClient(gateway_app.create_app(cfg, storage=storage)), storage


def _chat(client, path: str, model: str, content: str):
    return client.post(path, json={"model": model, "messages": [{"role": "user", "content": content}]})


def test_aux_calls_do_not_consume_policy_budget_and_are_audited(monkeypatch) -> None:
    client, storage = _client(monkeypatch, max_steps=1)
    with client:
        policy = _chat(client, "/v1/sessions/s-1/chat/completions", "policy-model", "question")
        judge_1 = _chat(client, "/v1/sessions/s-1/aux/judge/chat/completions", "judge-model", "gold answer A")
        judge_2 = _chat(client, "/v1/sessions/s-1/aux/judge/chat/completions", "judge-model", "gold answer B")
        status = client.get("/v1/sessions/s-1").json()

    assert policy.status_code == judge_1.status_code == judge_2.status_code == 200
    assert judge_2.json()["choices"][0]["message"]["content"] == "reply from judge-model"
    assert status["llm_step_count_by_model"] == {"policy-model": 1}
    assert status["last_model"] == "policy-model"
    assert "judge-model" not in status["truncated_models"]

    records = [record for _, record in storage.records]
    policy_records = [r for r in records if r.call_role == "policy"]
    judge_records = [r for r in records if r.call_role == "judge"]
    assert [r.session_id for r in policy_records] == ["s-1"]
    assert policy_records[0].event_type == "gateway_inference"
    assert policy_records[0].is_truncated is True
    assert [r.session_id for r in judge_records] == ["s-1:aux:judge", "s-1:aux:judge"]
    assert [r.seq_id for r in judge_records] == [1, 2]
    assert all(r.event_type == "gateway_aux_inference" for r in judge_records)
    assert all(r.policy_session_id == "s-1" for r in judge_records)
    assert all(r.is_truncated is False and r.is_session_completed is False for r in judge_records)
    assert judge_records[0].messages == [{"role": "user", "content": "gold answer A"}]


def test_aux_calls_do_not_move_policy_reward_target(monkeypatch) -> None:
    client, _ = _client(monkeypatch, max_steps=-1)
    with client:
        _chat(client, "/v1/sessions/s-2/chat/completions", "policy-model", "q1")
        _chat(client, "/v1/sessions/s-2/chat/completions", "policy-model", "q2")
        _chat(client, "/v1/sessions/s-2/aux/judge/chat/completions", "policy-model", "judge with same model")
        latest = client.get("/v1/sessions/s-2/latest-success-step", params={"model": "policy-model"}).json()
    assert latest == {"step_id": 2}


def test_aux_rows_are_linked_but_excluded_from_policy_trajectory(monkeypatch) -> None:
    client, storage = _client(monkeypatch, max_steps=-1)
    with client:
        _chat(client, "/v1/sessions/s-3/chat/completions", "policy-model", "q")
        _chat(client, "/v1/sessions/s-3/aux/judge/chat/completions", "judge-model", "gold")
    rows = []
    for binding, record in storage.records:
        rows.append(build_gateway_step_row(
            binding=binding,
            record=record,
            messages=record.messages,
            response=record.response,
            metadata=GatewayStorage._metadata(record),
        ))
    policy_row, judge_row = rows
    assert judge_row["session_id"] == "s-3:aux:judge"
    assert judge_row["env_id"] == "s-3"
    assert judge_row["meta_json"]["call_role"] == "judge"
    assert judge_row["meta_json"]["policy_session_id"] == "s-3"
    assert judge_row["record_id"] != policy_row["record_id"]
    assert is_trajectory_step(policy_row) is True
    assert is_trajectory_step(judge_row) is False
    assert select_reward_target(rows, llm_model="judge-model") is None
    assert select_reward_target(rows)["record_id"] == policy_row["record_id"]


def test_invalid_aux_role_and_reserved_session_id_are_rejected(monkeypatch) -> None:
    client, storage = _client(monkeypatch, max_steps=-1)
    with client:
        bad_role = _chat(client, "/v1/sessions/s-4/aux/Judge!/chat/completions", "judge-model", "x")
        reserved = _chat(client, "/v1/sessions/s-4:aux:judge/chat/completions", "policy-model", "x")
    assert bad_role.status_code >= 400
    assert reserved.status_code >= 400
    assert storage.records == []
