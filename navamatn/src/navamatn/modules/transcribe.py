from typing import Protocol

from openai import OpenAI

from navamatn.core.models import AudioInput, Transcript


class Transcriber(Protocol):
    def transcribe(self, audio: AudioInput) -> Transcript:
        ...


class OpenAITranscriber:
    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    def transcribe(self, audio: AudioInput) -> Transcript:
        with audio.path.open("rb") as file_obj:
            result = self._client.audio.transcriptions.create(
                model=self._model,
                file=file_obj,
                language=audio.language_hint,
            )
        return Transcript(text=result.text.strip())
