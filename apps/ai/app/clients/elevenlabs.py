"""ElevenLabs TTS, streaming endpoint: POST /v1/text-to-speech/{voice}/stream → mp3 chunks (audio/mpeg)."""

import httpx

from .base import TTSClient, TTSResult
from .http import body_chunks, http_client, post_stream


class ElevenLabsTTS(TTSClient):
    name = "elevenlabs"

    def __init__(
        self,
        api_key: str,
        # Mesuré le 23/11 sur ce compte, 3 tirages, même phrase française (voir DECISIONS.md § 2.9) :
        # v4_turbo 137 ms jusqu'au 1er octet et 7,89 s d'audio ; flash_v2_5 163 ms et 8,18 s ; turbo_v2_5 198 ms ;
        # multilingual_v2 520 ms (écarté). v4_turbo gagne sur les deux axes : plus tôt, et moins de blancs.
        model: str = "eleven_v4_turbo",
        # Voix « premade » multilingue, pas native française : l'accent reste anglais sur « kilos ».
        # Échantillons comparatifs et procédure : DECISIONS.md § 2.9. Il faut un id de voix FR (clé sans `voices_read`).
        voice: str = "JBFqnCBsd6RMkjVDRZzb",
        language: str = "fr",
        http: httpx.AsyncClient | None = None,
    ):
        self.api_key, self.model, self.voice, self.language, self.http = api_key, model, voice, language, http

    def build_body(self, text: str) -> dict:
        body = {"text": text, "model_id": self.model}
        if "multilingual_v2" not in self.model:  # language_code is refused by eleven_multilingual_v2
            body["language_code"] = self.language
        return body

    async def synthesize(self, text: str, voice: str | None = None) -> TTSResult:
        res = await post_stream(
            self.http or http_client(),
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice or self.voice}/stream?output_format=mp3_44100_128",
            who="elevenlabs tts",
            headers={"xi-api-key": self.api_key},
            json=self.build_body(text),
        )
        return TTSResult("audio/mpeg", body_chunks(res))
