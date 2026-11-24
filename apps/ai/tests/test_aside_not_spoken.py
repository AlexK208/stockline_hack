"""The model's notes to itself are never spoken (services/call_prep.is_aside, voice_session.Speaker.speak)."""

import asyncio

from app.services.call_prep import is_aside
from app.services.voice_session import Speaker

ASIDES = [
    "Il pose la question lui-même, je peux donc proposer.",  # heard live, Restaurant Leroy, 24/11
    "Le client refuse les substitutions.",
    "L'appelant veut huit kilos.",
    "Il demande de la bavette à la place.",
    "Elle a confirmé la commande.",
    "Selon mes règles, je ne propose rien.",
    "Donc je peux créer la commande.",
]
SAID = [
    "Je regarde.",
    "Bonjour Céline.",
    "Il reste douze kilos de bavette pour jeudi.",
    "Il part à cinq heures, vous êtes le premier de sa tournée.",
    "Elle se commande deux jours avant, donc samedi au plus tôt.",
    "Les alternatives dispo pour jeudi sont la bavette d'aloyau, le rumsteck et l'entrecôte.",
    "La bavette est le remplacement habituel de l'onglet.",
    "Laquelle vous irait, et pour quelle quantité ?",
    "Très bien, c'est validé pour jeudi.",
    "Je ne peux pas prendre cette commande, votre compte est bloqué.",
]


def test_asides_are_caught():
    assert [s for s in ASIDES if not is_aside(s)] == []


def test_real_answers_are_not():
    assert [s for s in SAID if is_aside(s)] == []


def test_speaker_drops_the_aside_and_keeps_the_answer():
    shown: list[str] = []

    async def run():
        sp = Speaker(tts=None, send=None, send_bytes=None, on_sentence=shown.append)  # type: ignore[arg-type]
        sp.worker = asyncio.create_task(asyncio.sleep(0))  # no TTS in this test: only what would be spoken
        sp.push("Je regarde. Il pose la question lui-même, je peux donc proposer. La bavette est le remplacement habituel. ")
        await sp.worker

    asyncio.run(run())
    assert shown == ["Je regarde.", "La bavette est le remplacement habituel."]
