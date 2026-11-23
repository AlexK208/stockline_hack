"""In-code acknowledgement and caller prefetch (app/services/call_prep.py): the parts that need no ERP."""

from app.schemas import ChatMessage
from app.agent.loop import caller_known
from app.services.call_prep import ack_note, choose_ack
from app.tools import desk


async def test_ack_on_later_turns_needs_no_erp():
    from app.services.call_prep import FILLERS

    assert await choose_ack("Mets dix kilos de bavette au lieu de sept", False, None) in FILLERS
    assert await choose_ack("Corgnac.", False, None) in FILLERS  # a one-word answer still gets a sound: tools follow
    assert await choose_ack("Allez, un seul quartier !", False, None) in FILLERS  # neutral: never sounds like a yes
    assert await choose_ack("c'est tout merci au revoir", False, None) == ""  # closing: no filler
    assert await choose_ack("", False, None) == ""


def test_caller_known_once_identify_caller_found_a_client():
    assert not caller_known([ChatMessage(role="user", content="bonjour")])
    found = ChatMessage(role="tool", name="identify_caller", tool_call_id="x", content='{"status":"found","client":{}}')
    assert caller_known([found])
    asked = ChatMessage(role="tool", name="identify_caller", tool_call_id="x", content='{"status":"ambiguous"}')
    assert not caller_known([asked])


def test_ack_note_names_what_was_said():
    assert "Bonjour Christian." in ack_note("Bonjour Christian.")


def clients():
    def c(i, name, city, *contacts):
        return {
            "id": i, "name": name, "city": city, "status": "active", "contacts": list(contacts), "_name": desk.tokens(name),
            "_first": [t for n in contacts for t in desk.tokens(n)[:1]], "_last": [t for n in contacts for t in desk.tokens(n)[1:]],
            "_city": desk.tokens(city), "_code": "",
        }  # fmt: skip

    rows = [
        c("a", "Hyper Frais Limoges", "Limoges", "Julien Dupont"),
        c("b", "Hyper Frais Limoges Corgnac", "Limoges", "Frédéric Lavaud"),
        c("c", "Boucherie Peyronnet", "Limoges", "Christian Peyronnet"),
        c("d", "Le Bœuf Limousin", "Ambazac", "Éric Garcia"),
        c("e", "Au Bœuf Limousin", "Rochechouart", "Minh Jean"),
    ]
    import math

    df: dict[str, int] = {}
    for r in rows:
        for t in set(r["_name"]):
            df[t] = df.get(t, 0) + 1
    return rows, {t: 1 + math.log(92 / n) for t, n in df.items()}


def test_matcher_never_guesses_between_lookalikes():
    rows, idf = clients()
    assert desk.match_clients("Hyper Frais Limoges", rows, idf)[0] is None  # two plausible → ask
    assert {c["id"] for c in desk.match_clients("Hyper Frais Limoges", rows, idf)[1]} == {"a", "b"}
    assert desk.match_clients("hyper frais corgnac", rows, idf)[0]["id"] == "b"
    assert desk.match_clients("c'est Christian de la boucherie peyronet", rows, idf)[0]["id"] == "c"  # one typo
    assert desk.match_clients("le boeuf limousin", rows, idf)[0] is None
    assert desk.match_clients("le boeuf limousin à Ambazac", rows, idf)[0]["id"] == "d"
    assert desk.match_clients("bonjour je voudrais commander", rows, idf) == (None, [])
