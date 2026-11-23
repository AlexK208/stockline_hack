"""Call report (built in code from the tool log) and the fallback voice when the TTS provider is down."""

import json

from app.schemas import MOCK_TTS_MIME, ChatMessage, ToolCall
from app.services import voice_session
from app.services.call_report import build_report
from app.services.voice_session import Speaker


def tool_round(i, name, args, result):
    call = ToolCall(id=f"c{i}", name=name, arguments=args)
    return [
        ChatMessage(role="assistant", content="", tool_calls=[call]),
        ChatMessage(role="tool", tool_call_id=call.id, name=name, content=json.dumps(result, ensure_ascii=False)),
    ]


def order(status, lines):
    return {"id": "ord_1", "number": "CMD-2026-006259", "status": status, "deliveryDate": "2026-11-26", "lines": lines}


CARD = {"status": "found", "client": {"id": "cli_0001", "name": "Boucherie Peyronnet"}}
FAUX_FILET = {"productName": "Faux-filet", "qty": 8.0, "unit": "kg"}


def test_report_of_a_confirmed_order_needs_no_follow_up():
    history = [
        ChatMessage(role="user", content="Bonjour, c'est Céline, huit kilos de faux-filet et de l'onglet pour jeudi"),
        *tool_round(1, "identify_caller", {"said": "Peyronnet"}, CARD),
        *tool_round(2, "create_draft_order", {}, {"written": False, "problems": ["Onglet de bœuf : rupture (0 kg possibles à cette date)"]}),
        *tool_round(3, "create_draft_order", {}, order("draft", [FAUX_FILET])),
        *tool_round(4, "log_client_event", {"title": "Demande d'onglet non servie"}, {"id": "cev_1"}),
        ChatMessage(role="user", content="Oui, valide"),
        *tool_round(5, "confirm_order", {}, order("confirmed", [FAUX_FILET])),
    ]
    r = build_report(history)
    assert r["clientId"] == "cli_0001"
    body = r["body"]
    assert body["type"] == "call" and body["status"] == "resolved" and body["orderId"] == "ord_1"
    assert "confirmée pour jeudi 26/11" in body["title"]
    assert "8 kg Faux-filet" in body["description"] and "Onglet de bœuf : rupture" in body["description"]
    assert "Demande d'onglet non servie" in body["description"] and "2 tour(s)" in body["description"]


def test_report_flags_a_draft_left_unconfirmed_and_a_refused_peek():
    history = [
        ChatMessage(role="user", content="c'est Céline, huit kilos de faux-filet"),
        *tool_round(1, "identify_caller", {"said": "Peyronnet"}, CARD),
        *tool_round(2, "create_draft_order", {}, order("draft", [FAUX_FILET])),
        *tool_round(3, "get_client_history", {"clientId": "cli_0009"}, {"error": "Refusé : pendant un appel, les outils ne servent que le client qui appelle."}),
    ]
    body = build_report(history)["body"]
    assert body["status"] == "open" and body["severity"] == "medium"
    assert "à valider" in body["title"] and "à rappeler pour valider" in body["description"]
    assert "autre client" in body["description"]


def test_no_report_without_a_client_or_without_anything_to_say():
    assert build_report([ChatMessage(role="user", content="bonjour")]) is None
    only_question = [
        ChatMessage(role="user", content="c'est Céline, il vous reste de l'onglet ?"),
        *tool_round(1, "identify_caller", {"said": "Peyronnet"}, CARD),
        *tool_round(2, "check_products", {}, {"items": []}),
    ]
    assert build_report(only_question) is None
    # a report already written: only what came after it counts
    done = [*only_question, *tool_round(3, "create_draft_order", {}, order("draft", [FAUX_FILET]))]
    assert build_report(done, start=len(done)) is None
    assert build_report(done, start=len(only_question)) is not None


class DeadTTS:
    name = "elevenlabs"
    calls = 0

    async def synthesize(self, text, voice=None):
        DeadTTS.calls += 1
        raise RuntimeError("HTTP 401 quota_exceeded")


async def test_dead_tts_falls_back_to_the_browser_voice(monkeypatch):
    monkeypatch.setitem(voice_session.TTS_HEALTH, "down_until", 0.0)
    DeadTTS.calls = 0
    sent, audio = [], []

    async def send(msg):
        sent.append(msg)

    async def send_bytes(data):
        audio.append(data)

    speaker = Speaker(DeadTTS(), send, send_bytes)
    speaker.speak("Je note.")
    speaker.speak("Dix kilos de bavette, c'est noté.")
    await speaker.finish()
    kinds = [type(m).__name__ for m in sent]
    assert kinds.count("VoiceErrorMessage") == 1  # said once, not once per sentence
    starts = [m for m in sent if type(m).__name__ == "AgentAudioStartMessage"]
    assert len(starts) == 1 and starts[0].mime == MOCK_TTS_MIME  # the page speaks the text itself
    assert kinds[-1] == "AgentAudioEndMessage" and audio
    assert DeadTTS.calls == 1  # the provider is left alone after the first failure

    # next turn, within the minute: straight to the browser voice, no error shown again
    sent.clear()
    speaker = Speaker(DeadTTS(), send, send_bytes)
    speaker.speak("Et avec ça ?")
    await speaker.finish()
    assert DeadTTS.calls == 1 and not any(type(m).__name__ == "VoiceErrorMessage" for m in sent)
    assert [m.mime for m in sent if type(m).__name__ == "AgentAudioStartMessage"] == [MOCK_TTS_MIME]


async def test_warmer_touches_the_cache_at_connection_then_only_after_silence(monkeypatch):
    from app.services import warmup

    w = warmup.Warmer()
    assert w.due() and not w.idle()  # a page just connected: warm at once
    w.used()
    assert not w.due()  # a real turn just used the model: nothing to do
    w.model_used_at -= warmup.WARM_EVERY_S
    assert w.due()  # four minutes without a turn: touch it again
    w.caller_active_at -= warmup.STOP_AFTER_IDLE_S + 1
    assert w.idle()  # nobody has called for a long time: stop costing anything
    assert await warmup.warm_prompt_cache() is None  # and never from the test suite
