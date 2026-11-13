"""The blind résumé screen (Claude through the real SDK with canned responses), the console and the CLI."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

from ats.app import SAMPLE, Console, create_app, demo_console
from ats.cli import main
from ats.screen import FALLBACK_BETA, MODEL, Screener, redact, rules


def message(*content: dict[str, Any], stop: str = "tool_use") -> dict[str, Any]:
    return {
        "id": "m",
        "type": "message",
        "role": "assistant",
        "model": MODEL,
        "content": list(content),
        "stop_reason": stop,
        "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


class Script:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses: Iterator[dict[str, Any]] = iter(responses)
        self.requests: list[dict[str, Any]] = []
        self.headers: list[httpx2.Headers] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(json.loads(request.content))
        self.headers.append(request.headers)
        return httpx2.Response(200, json=next(self.responses))


def screener(script: Script) -> Screener:
    client = anthropic.Anthropic(
        api_key="test",
        base_url="http://api.test",
        max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(script)),
    )
    return Screener(client)


def call(*items: dict[str, Any]) -> dict[str, Any]:
    return {"type": "tool_use", "id": "t", "name": "record_evidence", "input": {"evidence": list(items)}}


def test_redaction_removes_identity_and_school_but_keeps_work() -> None:
    text, removed = redact(SAMPLE)
    assert "Jordan" not in text and "Famous University" not in text and "jordan@example.com" not in text
    assert "7700" not in text and "2021-2025" in text and "Mentored two junior engineers" in text and "Skills" in text
    assert removed == ["name line", "education section", "contact details"]
    t2, r2 = redact("Ana\nDate of birth: 1 May 1990\nLed a team of five")
    assert "1990" not in t2 and "date of birth" in r2


def test_request_shape_and_only_quoted_evidence_counts() -> None:
    script = Script(
        [
            message(
                call(
                    {
                        "competency": "problem solving",
                        "level": 4,
                        "quote": "reduced p95 latency by 40% after tracing the root cause",
                    },
                    {"competency": "collaboration", "level": 3, "quote": "Mentored two junior engineers"},
                    {"competency": "communication", "level": 5, "quote": "gave a keynote at a big conference"},
                    {"competency": "technical depth", "level": 9, "quote": "Python, SQL, Kubernetes"},
                )
            )
        ]
    )
    ev = screener(script).read(SAMPLE, "Backend Engineer")
    assert ev.source == "claude" and ev.levels["problem solving"] == 4 and ev.levels["collaboration"] == 3
    assert ev.levels["communication"] is None and ev.levels["technical depth"] is None
    assert any("communication: no quote" in d for d in ev.dropped) and any("not 1-5" in d for d in ev.dropped)
    req = script.requests[0]
    sent = req["messages"][0]["content"]
    assert "Famous University" not in sent and "Jordan" not in sent and "<resume>" in sent
    assert req["model"] == MODEL and req["output_config"] == {"effort": "low"} and req["fallbacks"] == "default"
    assert "thinking" not in req and "tool_choice" not in req and req["tools"][0]["strict"] is True
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert FALLBACK_BETA in script.headers[0]["anthropic-beta"]


def test_refusal_falls_back_to_rules() -> None:
    ev = screener(Script([message({"type": "text", "text": "no"}, stop="refusal")])).read(SAMPLE, "x")
    assert ev.source == "rules" and ev.levels["technical depth"] and "Claude gave no answer" in ev.dropped[-1]
    assert rules("nothing relevant here").levels["communication"] is None


@pytest.fixture(scope="module")
def console() -> Console:
    return demo_console()


@pytest.fixture(scope="module")
def client(console: Console) -> TestClient:
    return TestClient(create_app(console))


def test_console_pages(client: TestClient, console: Console) -> None:
    assert client.get("/healthz").json()["requisitions"] == len(console.outcomes)
    assert "Requisitions" in client.get("/").text
    page = client.get("/reqs/0").text
    assert "Calibrated" in page and "offer" in page
    assert client.get("/reqs/999").status_code == 404
    assert "Own-group gap" in client.get("/interviewers").text
    fair = client.get("/fairness").text
    assert "Ratio B/A" in fair and "screen" in fair
    assert "Blind résumé screen" in client.get("/screen").text
    assert "Famous University" not in client.get("/screen").text.split("Evidence by competency")[1]


def test_console_api(client: TestClient, console: Console) -> None:
    reqs = client.get("/api/reqs").json()
    assert len(reqs) == len(console.outcomes) and reqs[0]["hired"]
    ints = client.get("/api/interviewers").json()
    assert len(ints) == len(console.company.interviewers) and {"leniency", "gap", "flagged"} <= set(ints[0])
    ev = client.post("/api/screen", json={"resume": SAMPLE}).json()
    assert ev["source"] == "rules" and "education section" in ev["removed"]
    assert client.post("/api/screen", json={"resume": " "}).status_code == 422
    assert client.post("/screen", data={"resume": ""}).status_code == 422
    assert "Evidence by competency" in client.post("/screen", data={"resume": SAMPLE}).text


def test_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    f = tmp_path / "cv.txt"
    f.write_text(SAMPLE, encoding="utf-8")
    assert main(["screen", str(f)]) == 0
    assert json.loads(capsys.readouterr().out)["source"] == "rules"
    assert main(["interviewers"]) == 0
    assert "leniency" in capsys.readouterr().out
