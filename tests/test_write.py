from __future__ import annotations

import agents.write as write_agent


class RateLimitedLLM:
    def __init__(self):
        self.calls = 0

    def invoke(self, _prompt):
        self.calls += 1
        raise RuntimeError("429 rate_limit_exceeded: tokens per day")


def test_rate_limit_stops_more_groq_calls_and_marks_fallback(monkeypatch):
    fake_llm = RateLimitedLLM()
    monkeypatch.setattr(write_agent, "llm", fake_llm)
    monkeypatch.setattr(write_agent, "PAUSE_GROQ", 0)
    monkeypatch.setattr(write_agent.time, "sleep", lambda _seconds: None)
    groups = [{"alerte": {"AnneeMois": f"2024-0{i}"}} for i in range(1, 4)]

    result = write_agent.write({"faits_groupes": groups, "essais": 0})

    assert fake_llm.calls == 1
    assert result["textes"] == [None, None, None]
    assert result["synthese"] is None
    assert result["groq_unavailable"] is True
