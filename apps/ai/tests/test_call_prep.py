"""In-code acknowledgement and caller prefetch (app/services/call_prep.py): the parts that need no ERP."""

from app.schemas import ChatMessage
from app.agent.loop import caller_known
from app.services.call_prep import ack_note, choose_ack
from app.tools import desk


async def test_opening_words_fit_what_the_caller_said():
    from app.services.call_prep import TOKENS, kind_of

    assert kind_of("Mets-moi dix kilos de bavette et deux arrières") == "order"
    assert kind_of("Il vous reste de l'onglet pour jeudi ?") == "lookup"
    assert kind_of("Tu me mets comme d'habitude pour jeudi ?") == "lookup"
    assert kind_of("Oui c'est bon, vas-y") == "yes"
    assert kind_of("Ah non attends, le paleron enlève-le") == "change"
    assert kind_of("Non non, pas Le Petit Roger, Le Petit Rocher") != "change"  # correcting us is not changing the order
    assert kind_of("Allez, un seul quartier, tu vas pas me laisser sans viande !") == "plea"
    assert kind_of("J'ai jamais reçu ces côtes de bœuf !") == "complaint"
    assert kind_of("Allez-y, confirmez") == "yes"  # not a plea
    assert kind_of("Pas de problème, mets-moi dix kilos") == "order"  # not a complaint
    assert kind_of("Corgnac.") == "short"
    assert kind_of("Celui de la place Denis-Dussoubs.") == "short"
    assert kind_of("C'est tout, merci, bonne journée") == "closing"
    # a request is never met with a word that accepts it: the stockout may come right after
    for said in ("Mets-moi dix kilos de bavette", "Il vous reste de l'onglet ?", "Corgnac."):
        ack = await choose_ack(said, False, None)
        assert ack in TOKENS["lookup"]
        assert not any(w in ack.lower() for w in ("accord", "marche", "parfait", "entendu", "alors"))
    assert await choose_ack("Ah non attends, enlève le paleron", False, None) in TOKENS["change"]
    assert await choose_ack("Oui c'est bon, vas-y", False, None) == ""  # after a yes: the answer itself
    assert await choose_ack("c'est tout merci au revoir", False, None) == ""  # goodbye: nothing
    assert await choose_ack("", False, None) == ""


async def test_opening_words_vary_and_pause():
    # right after the greeting: allowed
    assert await choose_ack("Mets-moi dix kilos de bavette", False, None, ["Bonjour Kevin."]) == "Je regarde."
    # never on two turns in a row
    assert await choose_ack("Et cinq kilos de paleron", False, None, ["Bonjour Kevin.", "Je regarde."]) == ""
    # and not the same words again within a few turns
    assert await choose_ack("Et deux arrières", False, None, ["Bonjour Kevin.", "Je regarde.", ""]) == "Un instant."
    assert await choose_ack("Et un agneau", False, None, ["Je regarde.", "", "Un instant.", ""]) == "Je vérifie."
    # blocked account: nothing that could sound like the order is being taken
    assert await choose_ack("Livre-moi un arrière pour samedi", False, None, [], blocked=True) == ""
    assert await choose_ack("Allez, tu vas pas me laisser sans viande", False, None, [], blocked=True) == "Je comprends."


def test_caller_known_once_identify_caller_found_a_client():
    assert not caller_known([ChatMessage(role="user", content="bonjour")])
    found = ChatMessage(role="tool", name="identify_caller", tool_call_id="x", content='{"status":"found","client":{}}')
    assert caller_known([found])
    asked = ChatMessage(role="tool", name="identify_caller", tool_call_id="x", content='{"status":"ambiguous"}')
    assert not caller_known([asked])


def test_ack_note_names_what_was_said():
    assert "Bonjour Christian." in ack_note("Bonjour Christian.")


def clients():
    def c(i, name, city, *contacts, address=""):
        return {"id": i, "code": i.upper(), "name": name, "city": city, "status": "active", "address": address, "contacts": [{"name": n} for n in contacts]}

    rows = [
        c("a", "Hyper Frais Limoges", "Limoges", "Julien Dupont", address="2 place Denis-Dussoubs, 87000 Limoges"),
        c("b", "Hyper Frais Limoges Corgnac", "Limoges", "Frédéric Lavaud"),
        c("c", "Boucherie Peyronnet", "Limoges", "Christian Peyronnet"),
        c("d", "Le Bœuf Limousin", "Ambazac", "Éric Garcia"),
        c("e", "Au Bœuf Limousin", "Rochechouart", "Minh Jean"),
        c("f", "Restaurant Leroy", "Ussel", "Nicolas Peyrat"),
        c("g", "Peyrat Traiteur", "Ussel", "Julien Morel"),
        c("h", "Le Comptoir de la Viande", "Limoges", "Anne Roux"),
        c("i", "Centre hospitalier de Saint-Junien (cuisine)", "Saint-Junien", "Bilal Julien"),
        c("j", "Boucherie Lacour de Tulle", "Tulle", "Gérard Lacour"),
        c("k", "La Boucherie de Couzeix", "Couzeix", "Paul Faure"),
        c("l", "Maison Hubert", "Couzeix", "Bastien Hubert"),
    ]
    products = [{"name": "Viande hachée fraîche", "aliases": ["haché"]}, {"name": "Quartier avant bœuf limousin", "aliases": ["avant"]}]
    return desk.build_directory(rows, products)


def test_matcher_never_guesses_between_lookalikes():
    rows, stats = clients()

    def who(said):
        best, candidates = desk.match_clients(said, rows, stats)
        return best["id"] if best else None

    assert who("Hyper Frais Limoges") is None  # two plausible → ask
    assert {c["id"] for c in desk.match_clients("Hyper Frais Limoges", rows, stats)[1]} >= {"a", "b"}
    assert who("hyper frais corgnac") == "b"
    assert who("Hyper Frais Limoges, place Denis-Dussoubs") == "a"  # the street settles it
    assert who("c'est Christian de la boucherie peyronet") == "c"  # one missing letter
    assert who("C'est Julien, Hyper Frais") == "a"  # his first name settles which Hyper Frais
    assert who("le boeuf limousin") is None
    assert who("le boeuf limousin à Ambazac") == "d"
    assert desk.match_clients("bonjour je voudrais commander", rows, stats) == (None, [])


def test_matcher_needs_more_than_a_first_name_or_an_everyday_word():
    rows, stats = clients()

    def who(said):
        best, _ = desk.match_clients(said, rows, stats)
        return best["id"] if best else None

    assert who("c'est Julien") is None  # a first name alone names nobody (and "julien" is not "junien")
    assert who("Peyrat à l'appareil") is None  # the chef at Leroy, or Peyrat Traiteur?
    assert who("Bonjour, Peyrat, restaurant Leroy à Ussel") == "f"
    assert who("vous avez de la viande hachée ?") is None  # a product word is not a client
    assert who("boucherie Martin à Tulle") is None  # an unknown shop is not the known one in the same town
    assert who("c'est Gérard, Lacour à Tulle") == "j"
    assert who("c'est Bastien, la boucherie à Couzeix") is None  # Bastien belongs to another client there


def test_piece_weights_from_the_catalogue_packaging():
    assert desk.piece_kg("quartier 90-110 kg") == (90, 110)
    assert desk.piece_kg("pièce 300-350 g") == (0.3, 0.35)
    assert desk.piece_kg("carton 50 x 100 g") == (5, 5)
    assert desk.piece_kg("sachet 2,5 kg") == (2.5, 2.5)
    assert desk.piece_kg("carré 6 côtes") is None  # no weight: the agent asks for kilos
    assert desk.piece_kg(None) is None


def test_one_dropped_letter_is_the_same_word_one_changed_letter_is_not():
    assert desk.same_word("peyronet", "peyronnet")
    assert desk.same_word("bistro", "bistrot")
    assert not desk.same_word("julien", "junien")
    assert not desk.same_word("leroy", "leroux")
    assert not desk.same_word("rocher", "roger")
